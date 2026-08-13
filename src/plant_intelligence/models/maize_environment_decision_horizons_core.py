"""Case Study B8: decision-horizon environmental forecasting.

B8 keeps the B5 environment/genotype folds and the B6-R outer-fold
representation choices frozen. It asks how much predictive information is
available at progressively later decision horizons without allowing later-stage
ECOV columns into earlier horizons.

A source-level caveat is explicit: the published G2F ECOV matrix was generated
with APSIM phenology calibrated to average observed silking within each
historical year-location. Therefore current-year in-season ECOV horizons are
retrospective horizon proxies, not prospective live-deployment validation.
The pre-season location-history representation is stricter: it uses only
outer-training-year environmental histories and never the held-out current-year
ECOV row.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_process_kernels import (
    STAGES,
    build_ec_audit,
)
from plant_intelligence.models.maize_environment_transfer import (
    BOOTSTRAP_REPS,
    _attach_folds,
    _load_manifests,
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

SEED = 20260813


@dataclass(frozen=True)
class HorizonSpec:
    name: str
    stages: tuple[str, ...]
    uses_current_year_ecov: bool
    availability_state: str
    description: str


PRE_FLOWERING_STAGES = ("GerEme", "EmeEnJ")
AT_FLOWERING_STAGES = ("GerEme", "EmeEnJ", "EnJFlo")
REPRODUCTIVE_STAGES = (
    "GerEme", "EmeEnJ", "EnJFlo", "FloFla", "FlaFlw", "FlwStG"
)
FULL_STAGES = tuple(STAGES)

HORIZONS = (
    HorizonSpec(
        "Pre-season-G-only",
        (),
        False,
        "PROSPECTIVE_SUPPORTED_G_ONLY",
        "No current-year ECOV information is admitted.",
    ),
    HorizonSpec(
        "Pre-season-location-history",
        (),
        False,
        "PROSPECTIVE_PROXY_TRAINING_HISTORY_ONLY",
        "Environmental representation is a training-only historical location climatology; held-out current-year ECOV is never used.",
    ),
    HorizonSpec(
        "Pre-flowering-observed",
        PRE_FLOWERING_STAGES,
        True,
        "RETROSPECTIVE_HORIZON_PROXY",
        "Uses only completed GerEme and EmeEnJ current-year ECOV intervals; later stages are excluded.",
    ),
    HorizonSpec(
        "At-flowering-observed",
        AT_FLOWERING_STAGES,
        True,
        "RETROSPECTIVE_HORIZON_PROXY",
        "Adds EnJFlo, so information is accumulated through the flowering boundary.",
    ),
    HorizonSpec(
        "Reproductive-stage-observed",
        REPRODUCTIVE_STAGES,
        True,
        "RETROSPECTIVE_HORIZON_PROXY",
        "Accumulates non-target-proximal ECOV information through FlwStG.",
    ),
    HorizonSpec(
        "Full-season-nonleaky",
        FULL_STAGES,
        True,
        "RETROSPECTIVE_REFERENCE_ONLY",
        "Uses all non-target-proximal stage ECOVs and is not an early-decision representation.",
    ),
)

HORIZON_ORDER = tuple(h.name for h in HORIZONS)


def location_code(environment: str) -> str:
    text = str(environment)
    return text.split("-", 1)[1] if "-" in text else text


def horizon_columns(audit: pd.DataFrame, spec: HorizonSpec) -> list[str]:
    if not spec.stages:
        return []
    mask = (~audit["target_proximal"].astype(bool)) & audit["phenology_stage"].isin(spec.stages)
    return audit.loc[mask, "covariate"].astype(str).tolist()


def load_selected_configs(results: Path) -> dict[int, TransferConfig]:
    path = results / "case_study_b6r_selected_configs.csv"
    if not path.exists():
        raise FileNotFoundError("B8 requires the frozen B6-R selected-config evidence.")
    frame = pd.read_csv(path)
    required = {"outer_environment_fold", "config", "g_rank", "e_rank", "gamma_multiplier", "alpha"}
    if not required.issubset(frame.columns):
        raise ValueError("B6-R selected-config table is missing required fields.")
    out: dict[int, TransferConfig] = {}
    for row in frame.itertuples(index=False):
        out[int(row.outer_environment_fold)] = TransferConfig(
            str(row.config), int(row.g_rank), int(row.e_rank), float(row.gamma_multiplier), float(row.alpha)
        )
    if len(out) != 5:
        raise ValueError("B8 expects five frozen B6-R outer-fold configurations.")
    return out


def historical_location_proxy(
    ecov_nonleaky: pd.DataFrame,
    train_envs: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build pre-season proxies without using held-out current-year ECOV rows.

    For a held-out environment, the proxy is the mean of outer-training
    environments at the same location. If the location has no outer-training
    history, the outer-training global mean is used. For an outer-training
    environment, its own ECOV row is excluded from the history pool so train and
    test representations obey the same decision-time rule.
    """

    all_envs = [str(v) for v in ecov_nonleaky.index]
    train = {str(v) for v in train_envs}
    if not train:
        raise ValueError("Training environment set cannot be empty.")
    missing = train.difference(all_envs)
    if missing:
        raise ValueError(f"Training environments absent from ECOV: {sorted(missing)[:3]}")

    source = ecov_nonleaky.copy()
    source.index = source.index.astype(str)
    global_train = source.loc[sorted(train)].mean(axis=0)
    train_by_location: dict[str, list[str]] = {}
    for env in sorted(train):
        train_by_location.setdefault(location_code(env), []).append(env)

    rows = []
    audit_rows = []
    for env in all_envs:
        loc = location_code(env)
        candidates = list(train_by_location.get(loc, []))
        if env in train:
            candidates = [e for e in candidates if e != env]
        if candidates:
            proxy = source.loc[candidates].mean(axis=0)
            source_type = "same_location_training_history"
        else:
            proxy = global_train
            source_type = "global_training_history_fallback"
        rows.append(proxy.to_numpy(float))
        audit_rows.append({
            "environment": env,
            "location": loc,
            "is_outer_training_environment": env in train,
            "history_source": source_type,
            "n_same_location_history_environments": int(len(candidates)),
            "uses_own_current_year_ecov": False,
            "uses_outer_test_ecov": False,
        })

    proxy_frame = pd.DataFrame(rows, index=all_envs, columns=source.columns, dtype=float)
    return proxy_frame, pd.DataFrame(audit_rows)


def _g_features(cells: pd.DataFrame, gmap) -> np.ndarray:
    lookup = gmap.lookup()
    return np.vstack([gmap.values[lookup[str(v)]] for v in cells["genotype"]]).astype(np.float32)


def _append_prediction(
    store: list[pd.DataFrame],
    test: pd.DataFrame,
    regime: str,
    scenario: str,
    horizon: str,
    pred: np.ndarray,
    cfg: TransferConfig,
) -> None:
    frame = test[["genotype", "environment", "observed", "environment_fold", "genotype_fold"]].copy()
    frame["regime"] = regime
    frame["scenario"] = scenario
    frame["horizon"] = horizon
    frame["predicted"] = np.asarray(pred, float)
    frame["selected_b6r_config"] = cfg.name
    store.append(frame)


def _fit_horizon(
    train: pd.DataFrame,
    test: pd.DataFrame,
    gm,
    em,
    alpha: float,
) -> np.ndarray:
    tg, te = cell_features(train, gm, em)
    vg, ve = cell_features(test, gm, em)
    return predict("G+E", tg, te, train.observed.to_numpy(float), vg, ve, alpha)


def run_predictions(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pheno, geno, ecov = load_materialized(root)
    from plant_intelligence.models.maize_environment_transfer import prepare_cells

    cells, geno, ecov, cols = prepare_cells(pheno, geno, ecov)
    results = root / "reports" / "results"
    envm, genom = _load_manifests(results)
    cells = _attach_folds(cells, envm, genom)
    selected = load_selected_configs(results)
    audit = build_ec_audit(ecov)
    nonleaky_cols = audit.loc[~audit.target_proximal.astype(bool), "covariate"].astype(str).tolist()
    if len(nonleaky_cols) != 197:
        raise ValueError(f"B8 expected 197 non-target-proximal ECOV columns, found {len(nonleaky_cols)}.")

    predictions: list[pd.DataFrame] = []
    history_audits: list[pd.DataFrame] = []
    design_rows: list[dict[str, object]] = []

    # Primary unseen-environment regime.
    for outer in sorted(envm.environment_fold.unique()):
        outer = int(outer)
        cfg = selected[outer]
        train = cells[cells.environment_fold != outer]
        test = cells[cells.environment_fold == outer]
        train_envs = set(train.environment.astype(str))

        gmax = genomic_map(geno, cols["geno_id"], set(train.genotype.astype(str)))
        gm = sliced(gmax, cfg.g_rank)

        # Strict pre-season genomic-only baseline.
        tg = _g_features(train, gm)
        vg = _g_features(test, gm)
        zeros_t = np.zeros((len(train), 1), dtype=np.float32)
        zeros_v = np.zeros((len(test), 1), dtype=np.float32)
        p = predict("G", tg, zeros_t, train.observed.to_numpy(float), vg, zeros_v, cfg.alpha)
        _append_prediction(predictions, test, "CV-E-B8", f"efold_{outer}", "Pre-season-G-only", p, cfg)

        # Strict-with-respect-to-current-year pre-season historical-location proxy.
        proxy, h_audit = historical_location_proxy(ecov[nonleaky_cols], train_envs)
        h_audit["outer_environment_fold"] = outer
        h_audit["regime"] = "CV-E-B8"
        history_audits.append(h_audit)
        rank = min(int(cfg.e_rank), len(train_envs) - 1)
        em_hist = environment_map(proxy, train_envs, rank, float(cfg.gamma_multiplier))
        p = _fit_horizon(train, test, gm, em_hist, cfg.alpha)
        _append_prediction(predictions, test, "CV-E-B8", f"efold_{outer}", "Pre-season-location-history", p, cfg)

        # Current-year information accumulation; no later-stage column may enter an earlier horizon.
        for spec in HORIZONS[2:]:
            cols_h = horizon_columns(audit, spec)
            if not cols_h:
                raise ValueError(f"No columns resolved for horizon {spec.name}.")
            em = environment_map(ecov[cols_h], train_envs, rank, float(cfg.gamma_multiplier))
            p = _fit_horizon(train, test, gm, em, cfg.alpha)
            _append_prediction(predictions, test, "CV-E-B8", f"efold_{outer}", spec.name, p, cfg)

        for spec in HORIZONS:
            design_rows.append({
                "regime": "CV-E-B8",
                "outer_environment_fold": outer,
                "horizon": spec.name,
                "selected_b6r_config": cfg.name,
                "g_rank": cfg.g_rank,
                "e_rank": cfg.e_rank,
                "gamma_multiplier": cfg.gamma_multiplier,
                "alpha": cfg.alpha,
                "n_current_year_ecov_columns": len(horizon_columns(audit, spec)),
                "uses_current_year_ecov": spec.uses_current_year_ecov,
                "availability_state": spec.availability_state,
            })

    # Strict unseen-genotype + unseen-environment regime.
    strict_g = {}
    for gf in sorted(genom.genotype_fold.unique()):
        gf = int(gf)
        ids = set(genom.loc[genom.genotype_fold != gf, "genotype"].astype(str))
        strict_g[gf] = genomic_map(geno, cols["geno_id"], ids)

    for outer in sorted(envm.environment_fold.unique()):
        outer = int(outer)
        cfg = selected[outer]
        train_envs = set(envm.loc[envm.environment_fold != outer, "environment"].astype(str))
        rank = min(int(cfg.e_rank), len(train_envs) - 1)
        proxy, _ = historical_location_proxy(ecov[nonleaky_cols], train_envs)
        emaps = {"Pre-season-location-history": environment_map(proxy, train_envs, rank, float(cfg.gamma_multiplier))}
        for spec in HORIZONS[2:]:
            emaps[spec.name] = environment_map(
                ecov[horizon_columns(audit, spec)], train_envs, rank, float(cfg.gamma_multiplier)
            )

        for gf, gmax in strict_g.items():
            train = cells[(cells.environment_fold != outer) & (cells.genotype_fold != gf)]
            test = cells[(cells.environment_fold == outer) & (cells.genotype_fold == gf)]
            if test.empty:
                continue
            gm = sliced(gmax, cfg.g_rank)
            tg = _g_features(train, gm)
            vg = _g_features(test, gm)
            zeros_t = np.zeros((len(train), 1), dtype=np.float32)
            zeros_v = np.zeros((len(test), 1), dtype=np.float32)
            p = predict("G", tg, zeros_t, train.observed.to_numpy(float), vg, zeros_v, cfg.alpha)
            scenario = f"efold_{outer}__gfold_{gf}"
            _append_prediction(predictions, test, "CV-GE-B8", scenario, "Pre-season-G-only", p, cfg)
            for name, em in emaps.items():
                p = _fit_horizon(train, test, gm, em, cfg.alpha)
                _append_prediction(predictions, test, "CV-GE-B8", scenario, name, p, cfg)

    return pd.concat(predictions, ignore_index=True), pd.concat(history_audits, ignore_index=True), pd.DataFrame(design_rows)


def availability_audit(ecov_audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, spec in enumerate(HORIZONS):
        cols_h = horizon_columns(ecov_audit, spec)
        rows.append({
            "horizon_order": i,
            "horizon": spec.name,
            "admitted_stages": "|".join(spec.stages),
            "n_current_year_ecov_columns": len(cols_h),
            "uses_current_year_ecov": spec.uses_current_year_ecov,
            "availability_state": spec.availability_state,
            "strict_no_post_horizon_columns": True,
            "source_phenology_calibrated_to_observed_silking": spec.uses_current_year_ecov,
            "description": spec.description,
        })
    return pd.DataFrame(rows)


def summarize(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pooled = []
    env_rows = []
    order = {name: i for i, name in enumerate(HORIZON_ORDER)}
    for (regime, horizon), part in predictions.groupby(["regime", "horizon"]):
        pooled.append({"regime": regime, "horizon": horizon, "n": len(part), **metrics(part.observed, part.predicted)})
    for (regime, environment, horizon), part in predictions.groupby(["regime", "environment", "horizon"]):
        env_rows.append({"regime": regime, "environment": environment, "horizon": horizon, "n": len(part), **metrics(part.observed, part.predicted)})
    summary = pd.DataFrame(pooled)
    summary["horizon_order"] = summary.horizon.map(order)
    summary = summary.sort_values(["regime", "horizon_order"]).reset_index(drop=True)
    summary["delta_rmse_vs_previous"] = np.nan
    summary["pct_rmse_change_vs_previous"] = np.nan
    for regime, idx in summary.groupby("regime").groups.items():
        inds = list(idx)
        for j in range(1, len(inds)):
            cur, prev = inds[j], inds[j - 1]
            delta = float(summary.loc[cur, "rmse"] - summary.loc[prev, "rmse"])
            summary.loc[cur, "delta_rmse_vs_previous"] = delta
            summary.loc[cur, "pct_rmse_change_vs_previous"] = 100.0 * delta / float(summary.loc[prev, "rmse"])
    return summary, pd.DataFrame(env_rows)


def paired_environment_bootstrap(predictions: pd.DataFrame, reps: int = BOOTSTRAP_REPS) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    pairs = list(zip(HORIZON_ORDER[1:], HORIZON_ORDER[:-1]))
    pairs += [
        ("Reproductive-stage-observed", "Pre-season-G-only"),
        ("Full-season-nonleaky", "Pre-season-G-only"),
        ("Full-season-nonleaky", "Reproductive-stage-observed"),
    ]
    rows = []
    for regime, part in predictions.groupby("regime"):
        pivot = part.pivot_table(
            index=["genotype", "environment", "observed"],
            columns="horizon",
            values="predicted",
            aggfunc="first",
        ).reset_index()
        envs = np.asarray(sorted(pivot.environment.astype(str).unique()))
        for challenger, reference in pairs:
            if challenger not in pivot.columns or reference not in pivot.columns:
                continue
            ae = (pivot.observed.to_numpy(float) - pivot[challenger].to_numpy(float)) ** 2
            be = (pivot.observed.to_numpy(float) - pivot[reference].to_numpy(float)) ** 2
            stats = pd.DataFrame({"environment": pivot.environment.astype(str), "a": ae, "b": be}).groupby("environment").agg(sa=("a", "sum"), sb=("b", "sum"), n=("a", "size"))
            delta = float(np.sqrt(np.mean(ae)) - np.sqrt(np.mean(be)))
            boots = np.empty(reps, dtype=float)
            for i in range(reps):
                sample = rng.choice(envs, len(envs), replace=True)
                s = stats.loc[sample]
                n = float(s.n.sum())
                boots[i] = np.sqrt(float(s.sa.sum()) / n) - np.sqrt(float(s.sb.sum()) / n)
            rows.append({
                "regime": regime,
                "challenger": challenger,
                "reference": reference,
                "metric": "RMSE",
                "delta_challenger_minus_reference": delta,
                "ci95_low": float(np.quantile(boots, 0.025)),
                "ci95_high": float(np.quantile(boots, 0.975)),
                "improvement_frequency": float(np.mean(boots < 0.0)),
                "bootstrap_clusters": "environment",
                "bootstrap_reps": reps,
            })
    return pd.DataFrame(rows)


def history_summary(history_audit: pd.DataFrame) -> pd.DataFrame:
    test = history_audit[~history_audit.is_outer_training_environment.astype(bool)].copy()
    rows = []
    for outer, part in test.groupby("outer_environment_fold"):
        same = part.history_source.eq("same_location_training_history")
        rows.append({
            "outer_environment_fold": int(outer),
            "n_held_out_environments": int(len(part)),
            "n_with_same_location_training_history": int(same.sum()),
            "same_location_history_fraction": float(same.mean()),
            "n_global_fallback": int((~same).sum()),
            "uses_outer_test_ecov": bool(part.uses_outer_test_ecov.any()),
        })
    return pd.DataFrame(rows)


def make_figure(summary: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.5, 7.2))
    x = np.arange(len(HORIZON_ORDER))
    labels = [
        "G only",
        "Location\nhistory",
        "Pre-\nflowering",
        "At\nflowering",
        "Reproductive\nstage",
        "Full\nseason",
    ]
    for regime, part in summary.groupby("regime"):
        part = part.set_index("horizon").loc[list(HORIZON_ORDER)]
        label = "Unseen environment" if regime == "CV-E-B8" else "Unseen genotype + environment"
        ax.plot(x, part.rmse.to_numpy(float), marker="o", linewidth=2.2, label=label)
    ax.set_xticks(x, labels)
    ax.set_ylabel("RMSE")
    ax.set_title("Case Study B8 — predictive value accumulated across decision horizons")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    fig.subplots_adjust(bottom=0.24)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(root: Path) -> dict[str, Path]:
    predictions, history_audit_frame, design = run_predictions(root)
    pheno, geno, ecov = load_materialized(root)
    audit = build_ec_audit(ecov)
    summary, env_metrics = summarize(predictions)
    bootstrap = paired_environment_bootstrap(predictions)
    availability = availability_audit(audit)
    history = history_summary(history_audit_frame)

    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    paths = {
        "summary": results / "case_study_b8_decision_horizon_summary.csv",
        "bootstrap": results / "case_study_b8_decision_horizon_bootstrap.csv",
        "environment_metrics": results / "case_study_b8_environment_metrics.csv",
        "availability": results / "case_study_b8_availability_audit.csv",
        "preseason_history": results / "case_study_b8_preseason_history_audit.csv",
        "design": results / "case_study_b8_design_audit.csv",
        "figure": figures / "case_study_b8_decision_horizon.png",
    }
    summary.to_csv(paths["summary"], index=False)
    bootstrap.to_csv(paths["bootstrap"], index=False)
    env_metrics.to_csv(paths["environment_metrics"], index=False)
    availability.to_csv(paths["availability"], index=False)
    history.to_csv(paths["preseason_history"], index=False)
    design.to_csv(paths["design"], index=False)
    make_figure(summary, paths["figure"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Case Study B8 decision-horizon forecasting.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B8 complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
