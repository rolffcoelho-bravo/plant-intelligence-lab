"""Case Study B7: biologically structured environmental representation.

B7 preserves the B5 outer environment/genotype folds and freezes the B6-R
outer-fold representation choices. It does not retune those choices. Instead,
it asks whether biologically structured environmental blocks carry more
transferable information than treating every environmental covariate as one
undifferentiated vector.

The source ECOV matrix contains APSIM crop-model outputs named ``yield_*``.
These are explicitly marked target-proximal and excluded from every B7
candidate model. The published B6-R all-EC model is retained only as a frozen
sensitivity/reference benchmark.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_transfer import (
    BOOTSTRAP_REPS,
    FeatureMap,
    _attach_folds,
    _load_manifests,
    prepare_cells,
)
from plant_intelligence.models.maize_environment_transfer_robustness import (
    TransferConfig,
    cell_features,
    environment_map,
    genomic_map,
    load_materialized,
    metrics,
    predict,
    sliced,
)

STAGES = (
    "GerEme", "EmeEnJ", "EnJFlo", "FloFla", "FlaFlw",
    "FlwStG", "StGEnG", "EnGMat", "MatHar",
)
STAGE_GROUPS = {
    "vegetative": {"GerEme", "EmeEnJ", "EnJFlo"},
    "reproductive_transition": {"FloFla", "FlaFlw", "FlwStG"},
    "grain_fill_maturity": {"StGEnG", "EnGMat", "MatHar"},
}
THERMAL_PREFIXES = {"HI30", "CumHI30", "TT", "CumTT"}
WATER_PREFIXES = {
    "Eo", "Eos", "Es", "ESW", "SW", "Flow", "FlowNO3", "Flux",
    "Infiltration", "PotInf", "PotInfiltr", "PotRunoff", "Runoff",
    "WaterTable", "TimeEvap2", "SDR", "T",
}
CANOPY_PREFIXES = {"biomass", "CoverGreen", "CoverTotal", "LAI"}
TARGET_PREFIXES = {"yield"}

MODEL_ORDER = (
    "B6R-all-EC-reference",
    "All-nonleaky",
    "Thermal",
    "Water-soil",
    "Canopy-growth",
    "Thermal+water-MK",
    "Vegetative",
    "Reproductive-transition",
    "Grain-fill-maturity",
    "Process-MK",
    "Stage-MK",
)


@dataclass(frozen=True)
class EnvironmentalSpec:
    name: str
    groups: tuple[str, ...]
    multiple_kernel: bool = False


SPECS = (
    EnvironmentalSpec("B6R-all-EC-reference", ("all",)),
    EnvironmentalSpec("All-nonleaky", ("nonleaky",)),
    EnvironmentalSpec("Thermal", ("thermal",)),
    EnvironmentalSpec("Water-soil", ("water_soil",)),
    EnvironmentalSpec("Canopy-growth", ("canopy_growth",)),
    EnvironmentalSpec("Thermal+water-MK", ("thermal", "water_soil"), True),
    EnvironmentalSpec("Vegetative", ("vegetative",)),
    EnvironmentalSpec("Reproductive-transition", ("reproductive_transition",)),
    EnvironmentalSpec("Grain-fill-maturity", ("grain_fill_maturity",)),
    EnvironmentalSpec("Process-MK", ("thermal", "water_soil", "canopy_growth", "other"), True),
    EnvironmentalSpec("Stage-MK", ("vegetative", "reproductive_transition", "grain_fill_maturity"), True),
)


def split_ec_name(name: str) -> tuple[str, str | None]:
    text = str(name)
    for stage in STAGES:
        suffix = "_" + stage
        if text.endswith(suffix):
            return text[: -len(suffix)], stage
    return text, None


def process_block(prefix: str) -> str:
    if prefix in TARGET_PREFIXES:
        return "target_proximal"
    if prefix in THERMAL_PREFIXES:
        return "thermal"
    if prefix in WATER_PREFIXES:
        return "water_soil"
    if prefix in CANOPY_PREFIXES:
        return "canopy_growth"
    return "other"


def build_ec_audit(ecov: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in ecov.columns:
        prefix, stage = split_ec_name(str(col))
        block = process_block(prefix)
        target = block == "target_proximal"
        stage_group = None
        if stage is not None:
            for group, members in STAGE_GROUPS.items():
                if stage in members:
                    stage_group = group
                    break
        rows.append({
            "covariate": str(col),
            "prefix": prefix,
            "phenology_stage": stage,
            "stage_group": stage_group,
            "process_block": block,
            "target_proximal": bool(target),
            "included_in_b7_candidates": bool(not target),
            "exclusion_reason": "APSIM predicted-yield output; excluded conservatively from B7 candidates" if target else "",
        })
    return pd.DataFrame(rows)


def group_columns(audit: pd.DataFrame) -> dict[str, list[str]]:
    nonleaky = audit.loc[~audit.target_proximal, "covariate"].tolist()
    out: dict[str, list[str]] = {
        "all": audit["covariate"].tolist(),
        "nonleaky": nonleaky,
    }
    for block in ("thermal", "water_soil", "canopy_growth", "other"):
        out[block] = audit.loc[(audit.process_block == block) & (~audit.target_proximal), "covariate"].tolist()
    for stage_group in STAGE_GROUPS:
        out[stage_group] = audit.loc[(audit.stage_group == stage_group) & (~audit.target_proximal), "covariate"].tolist()
    return out


def combine_maps(maps: list[FeatureMap], name: str) -> FeatureMap:
    active = [m for m in maps if m.values.shape[1] > 0]
    if not active:
        raise ValueError(f"No environmental maps available for {name}.")
    ids = active[0].ids
    if any(m.ids != ids for m in active[1:]):
        raise ValueError("Environmental map identifiers do not align.")
    # Each component map is already dimension-normalized by environment_map.
    # Dividing the concatenation by sqrt(B) makes the induced kernel the equal
    # average of B component kernels rather than allowing a block-count scale
    # advantage.
    values = np.hstack([m.values for m in active]).astype(np.float32) / np.sqrt(len(active))
    return FeatureMap(ids, values, {"kind": "equal_weight_multiple_kernel", "components": len(active), "name": name})


def build_environment_representation(
    ecov: pd.DataFrame,
    audit: pd.DataFrame,
    train_envs: set[str],
    cfg: TransferConfig,
    spec: EnvironmentalSpec,
) -> FeatureMap:
    groups = group_columns(audit)
    maps: list[FeatureMap] = []
    for group in spec.groups:
        cols = groups[group]
        if not cols:
            continue
        rank = min(int(cfg.e_rank), len(train_envs) - 1)
        maps.append(environment_map(ecov[cols], train_envs, rank, float(cfg.gamma_multiplier)))
    if not maps:
        raise ValueError(f"Environmental specification {spec.name} has no usable columns.")
    if spec.multiple_kernel:
        return combine_maps(maps, spec.name)
    return maps[0]


def load_selected_configs(results: Path) -> dict[int, TransferConfig]:
    path = results / "case_study_b6r_selected_configs.csv"
    if not path.exists():
        raise FileNotFoundError("B6-R selected configuration evidence is required before B7.")
    frame = pd.read_csv(path)
    required = {"outer_environment_fold", "config", "g_rank", "e_rank", "gamma_multiplier", "alpha"}
    if not required.issubset(frame.columns):
        raise ValueError("B6-R selected-config table is missing required fields.")
    out = {}
    for row in frame.itertuples(index=False):
        out[int(row.outer_environment_fold)] = TransferConfig(
            str(row.config), int(row.g_rank), int(row.e_rank), float(row.gamma_multiplier), float(row.alpha)
        )
    if len(out) != 5:
        raise ValueError("B7 expects five frozen B6-R outer-fold configurations.")
    return out


def _append_prediction(store: list[pd.DataFrame], test: pd.DataFrame, regime: str, scenario: str, model: str, pred: np.ndarray) -> None:
    f = test[["environment", "observed"]].copy()
    f["regime"] = regime
    f["scenario"] = scenario
    f["model"] = model
    f["predicted"] = pred
    store.append(f)


def run_predictions(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pheno, geno, ecov = load_materialized(root)
    cells, geno, ecov, cols = prepare_cells(pheno, geno, ecov)
    results = root / "reports" / "results"
    envm, genom = _load_manifests(results)
    cells = _attach_folds(cells, envm, genom)
    selected = load_selected_configs(results)
    audit = build_ec_audit(ecov)
    groups = group_columns(audit)
    if not groups["nonleaky"]:
        raise ValueError("No non-target-proximal environmental covariates remain.")

    predictions: list[pd.DataFrame] = []
    design_rows: list[dict[str, object]] = []

    # Primary unseen-environment transfer. Genomic representation and B6-R
    # selected hyperparameters are frozen; only the environmental information
    # block is changed.
    for outer in sorted(envm.environment_fold.unique()):
        outer = int(outer)
        cfg = selected[outer]
        train = cells[cells.environment_fold != outer]
        test = cells[cells.environment_fold == outer]
        train_envs = set(train.environment.astype(str))
        gmax = genomic_map(geno, cols["geno_id"], set(train.genotype.astype(str)))
        gm = sliced(gmax, cfg.g_rank)
        for spec in SPECS:
            em = build_environment_representation(ecov, audit, train_envs, cfg, spec)
            tg, te = cell_features(train, gm, em)
            vg, ve = cell_features(test, gm, em)
            pred = predict("G+E", tg, te, train.observed.to_numpy(float), vg, ve, cfg.alpha)
            _append_prediction(predictions, test, "CV-E-B7", f"efold_{outer}", spec.name, pred)
            design_rows.append({
                "regime": "CV-E-B7", "scenario": f"efold_{outer}", "model": spec.name,
                "selected_b6r_config": cfg.name, "g_rank": cfg.g_rank, "base_e_rank": cfg.e_rank,
                "gamma_multiplier": cfg.gamma_multiplier, "alpha": cfg.alpha,
                "environment_feature_dim": int(em.values.shape[1]),
                "n_source_covariates": int(sum(len(groups[g]) for g in spec.groups)),
                "multiple_kernel": bool(spec.multiple_kernel),
            })

    # Strict unseen-genotype + unseen-environment transfer. The environment map
    # depends only on the held-out environment fold and can be reused across the
    # five genotype folds. The genomic map is rebuilt without the held-out
    # genotype fold.
    strict_g = {}
    for gf in sorted(genom.genotype_fold.unique()):
        gf = int(gf)
        ids = set(genom.loc[genom.genotype_fold != gf, "genotype"].astype(str))
        strict_g[gf] = genomic_map(geno, cols["geno_id"], ids)

    for outer in sorted(envm.environment_fold.unique()):
        outer = int(outer)
        cfg = selected[outer]
        train_envs = set(envm.loc[envm.environment_fold != outer, "environment"].astype(str))
        emaps = {spec.name: build_environment_representation(ecov, audit, train_envs, cfg, spec) for spec in SPECS}
        for gf, gmax in strict_g.items():
            train = cells[(cells.environment_fold != outer) & (cells.genotype_fold != gf)]
            test = cells[(cells.environment_fold == outer) & (cells.genotype_fold == gf)]
            if test.empty:
                continue
            gm = sliced(gmax, cfg.g_rank)
            for spec in SPECS:
                em = emaps[spec.name]
                tg, te = cell_features(train, gm, em)
                vg, ve = cell_features(test, gm, em)
                pred = predict("G+E", tg, te, train.observed.to_numpy(float), vg, ve, cfg.alpha)
                scenario = f"efold_{outer}__gfold_{gf}"
                _append_prediction(predictions, test, "CV-GE-B7", scenario, spec.name, pred)

    return pd.concat(predictions, ignore_index=True), audit, pd.DataFrame(design_rows)


def summarize(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pooled = []
    env_rows = []
    for (regime, model), part in predictions.groupby(["regime", "model"]):
        pooled.append({"regime": regime, "model": model, "n": len(part), **metrics(part.observed, part.predicted)})
    for (regime, environment, model), part in predictions.groupby(["regime", "environment", "model"]):
        env_rows.append({"regime": regime, "environment": environment, "model": model, "n": len(part), **metrics(part.observed, part.predicted)})
    p = pd.DataFrame(pooled)
    p["model_order"] = p.model.map({m: i for i, m in enumerate(MODEL_ORDER)})
    p = p.sort_values(["regime", "model_order"]).drop(columns="model_order").reset_index(drop=True)
    return p, pd.DataFrame(env_rows)


def paired_environment_bootstrap(predictions: pd.DataFrame, reps: int = BOOTSTRAP_REPS) -> pd.DataFrame:
    rng = np.random.default_rng(20260813)
    comparisons = []
    for model in MODEL_ORDER[1:]:
        comparisons.append((model, "B6R-all-EC-reference"))
    comparisons += [
        ("Process-MK", "All-nonleaky"),
        ("Stage-MK", "All-nonleaky"),
        ("Thermal+water-MK", "All-nonleaky"),
    ]
    rows = []
    for regime, part in predictions.groupby("regime"):
        pivot = part.pivot_table(index=["environment", "observed"], columns="model", values="predicted", aggfunc="first").reset_index()
        envs = np.asarray(sorted(pivot.environment.unique()))
        for challenger, reference in comparisons:
            a = (pivot.observed - pivot[challenger]) ** 2
            b = (pivot.observed - pivot[reference]) ** 2
            stats = pd.DataFrame({"environment": pivot.environment, "a": a, "b": b}).groupby("environment").agg(sa=("a", "sum"), sb=("b", "sum"), n=("a", "size"))
            delta = float(np.sqrt(a.mean()) - np.sqrt(b.mean()))
            boots = np.empty(reps, dtype=float)
            for i in range(reps):
                sample = rng.choice(envs, len(envs), replace=True)
                s = stats.loc[sample]
                n = s.n.sum()
                boots[i] = np.sqrt(s.sa.sum() / n) - np.sqrt(s.sb.sum() / n)
            rows.append({
                "regime": regime, "challenger": challenger, "reference": reference,
                "metric": "RMSE", "delta_challenger_minus_reference": delta,
                "ci95_low": float(np.quantile(boots, 0.025)),
                "ci95_high": float(np.quantile(boots, 0.975)),
                "improvement_frequency": float(np.mean(boots < 0.0)),
                "bootstrap_clusters": "environment", "bootstrap_reps": int(reps),
            })
    return pd.DataFrame(rows)


def block_summary(audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for block, part in audit.groupby("process_block", dropna=False):
        rows.append({"dimension": "process", "block": block, "n_covariates": len(part), "n_target_proximal": int(part.target_proximal.sum())})
    for stage, part in audit.groupby("stage_group", dropna=False):
        rows.append({"dimension": "phenology", "block": str(stage), "n_covariates": len(part), "n_target_proximal": int(part.target_proximal.sum())})
    return pd.DataFrame(rows)


def make_figure(summary: pd.DataFrame, path: Path) -> None:
    focus = ["B6R-all-EC-reference", "All-nonleaky", "Thermal", "Water-soil", "Canopy-growth", "Process-MK", "Stage-MK"]
    regimes = ["CV-E-B7", "CV-GE-B7"]
    x = np.arange(len(regimes), dtype=float)
    width = 0.105
    fig, ax = plt.subplots(figsize=(13.5, 6.8))
    for j, model in enumerate(focus):
        vals = []
        for regime in regimes:
            row = summary[(summary.regime == regime) & (summary.model == model)]
            vals.append(float(row.iloc[0].rmse))
        bars = ax.bar(x + (j - (len(focus)-1)/2) * width, vals, width, label=model)
        ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=7.5, rotation=90)
    ax.set_xticks(x, ["Unseen environment", "Unseen genotype + environment"])
    ax.set_ylabel("RMSE")
    ax.set_title("Case Study B7 — biologically structured environmental representation")
    ax.grid(axis="y", alpha=0.22)
    fig.legend(loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.01))
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def run(output_root: Path) -> dict[str, Path]:
    root = output_root.resolve()
    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    results.mkdir(parents=True, exist_ok=True)
    predictions, audit, design = run_predictions(root)
    summary, env_metrics = summarize(predictions)
    bootstrap = paired_environment_bootstrap(predictions)
    blocks = block_summary(audit)
    outputs = {
        "summary": results / "case_study_b7_process_kernel_summary.csv",
        "bootstrap": results / "case_study_b7_process_kernel_bootstrap.csv",
        "environment_metrics": results / "case_study_b7_environment_metrics.csv",
        "ecov_audit": results / "case_study_b7_ecov_leakage_audit.csv",
        "block_summary": results / "case_study_b7_environment_block_summary.csv",
        "design": results / "case_study_b7_design_audit.csv",
        "figure": figures / "case_study_b7_process_kernel_ablation.png",
    }
    summary.to_csv(outputs["summary"], index=False)
    bootstrap.to_csv(outputs["bootstrap"], index=False)
    env_metrics.to_csv(outputs["environment_metrics"], index=False)
    audit.to_csv(outputs["ecov_audit"], index=False)
    blocks.to_csv(outputs["block_summary"], index=False)
    design.to_csv(outputs["design"], index=False)
    make_figure(summary, outputs["figure"])
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Case Study B7 biological environmental representation")
    parser.add_argument("--output-root", default=".")
    args = parser.parse_args()
    outputs = run(Path(args.output_root))
    print("Case Study B7 complete")
    for key, value in outputs.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
