"""Case Study B10-S: training-only forward selection of T2 environment geometry.

B10-S converts the B10-R oracle geometry diagnosis into a valid historical
selection problem. The B9 issuance horizons and B10 outer forward-year splits
remain frozen. Candidate T2 geometries are exactly the 12 rank/bandwidth cells
already diagnosed in B10-R; genomic rank and ridge alpha remain fixed.

For outer deployment year t, a candidate may be selected only from chronological
inner validation years y < t, where each inner fit itself uses years < y. The
outer-year yield is never used for geometry selection.

At least two inner chronological validation years are required. Therefore 2016
has an explicit INSUFFICIENT_HISTORY_FALLBACK state and uses the frozen B10
geometry (rank 16, gamma multiplier 2) without inspecting 2016 outcomes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_transfer import BOOTSTRAP_REPS, prepare_cells
from plant_intelligence.models.maize_environment_transfer_robustness import (
    TransferConfig,
    cell_features,
    environment_map,
    genomic_map,
    load_materialized,
    metrics,
    predict,
)
from plant_intelligence.models.maize_forecast_time_prediction import (
    FROZEN_CONFIG,
    STATE_BY_MODEL,
    build_environment_state_matrices,
    validate_b9_inputs,
)
from plant_intelligence.models.maize_forward_support_diagnostics import DIAGNOSTIC_GRID

SEED = 20260813
MIN_INNER_YEARS = 2
T1_HORIZON = STATE_BY_MODEL["G+E_T1"]
T2_HORIZON = STATE_BY_MODEL["G+E_T2"]

# Candidate order is frozen by B10-R. It is used only as the final deterministic
# tie-break after equal-weight mean inner-year RMSE and pooled inner RMSE.
CANDIDATES = tuple(DIAGNOSTIC_GRID)
CANDIDATE_ORDER = {cfg.name: i for i, cfg in enumerate(CANDIDATES)}

PAIR_SPECS = (
    ("Selected-T2", "Frozen-T2", "selected_T2_vs_frozen_T2"),
    ("Selected-T2", "Frozen-T1", "selected_T2_vs_frozen_T1"),
    ("Frozen-T2", "Frozen-T1", "frozen_T2_vs_frozen_T1_reproduction"),
)


def _year_from_environment(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values.astype(str).str.slice(0, 4), errors="raise").astype(int)


def inner_years_for_outer(available_years: list[int] | tuple[int, ...], outer_year: int) -> list[int]:
    years = sorted({int(v) for v in available_years if int(v) < int(outer_year)})
    if len(years) < 2:
        return []
    # The first historical year cannot be an inner validation year because it
    # has no earlier training year. Every returned year is strictly pre-outer.
    return years[1:]


def _candidate_name(rank: int, gamma: float) -> str:
    return f"diagnostic_rank{int(rank)}_gamma{float(gamma):g}"


def select_candidate(inner_evidence: pd.DataFrame, outer_year: int) -> dict[str, object]:
    """Select geometry using only chronological inner evidence before outer_year."""

    eligible = inner_evidence[inner_evidence["inner_test_year"].astype(int) < int(outer_year)].copy()
    inner_years = sorted(eligible["inner_test_year"].astype(int).unique().tolist())
    if len(inner_years) < MIN_INNER_YEARS:
        return {
            "outer_test_year": int(outer_year),
            "selection_status": "INSUFFICIENT_HISTORY_FALLBACK",
            "n_inner_years": int(len(inner_years)),
            "inner_years": ";".join(map(str, inner_years)),
            "selected_config": FROZEN_CONFIG.name,
            "selected_e_rank": int(FROZEN_CONFIG.e_rank),
            "selected_gamma_multiplier": float(FROZEN_CONFIG.gamma_multiplier),
            "selected_alpha": float(FROZEN_CONFIG.alpha),
            "mean_inner_year_rmse": np.nan,
            "pooled_inner_rmse": np.nan,
            "mean_inner_year_mae": np.nan,
            "outer_outcome_used_for_selection": False,
        }

    expected = set(CANDIDATE_ORDER)
    observed = set(eligible["config"].astype(str))
    if observed != expected:
        raise ValueError(f"B10-S inner evidence candidate mismatch: expected {len(expected)}, found {len(observed)}")

    scored_rows: list[dict[str, object]] = []
    for config_name, part in eligible.groupby("config"):
        # Every candidate must have exactly the same chronological validation years.
        candidate_years = sorted(part["inner_test_year"].astype(int).unique().tolist())
        if candidate_years != inner_years:
            raise ValueError(f"Candidate {config_name} has inconsistent inner years.")
        n = float(part["n"].sum())
        scored_rows.append(
            {
                "config": str(config_name),
                "mean_inner_year_rmse": float(part["rmse"].mean()),
                "pooled_inner_rmse": float(np.sqrt(part["sse"].sum() / n)),
                "mean_inner_year_mae": float(part["mae"].mean()),
                "order": CANDIDATE_ORDER[str(config_name)],
            }
        )
    scores = pd.DataFrame(scored_rows).sort_values(
        ["mean_inner_year_rmse", "pooled_inner_rmse", "order"],
        kind="mergesort",
    )
    winner = scores.iloc[0]
    cfg = next(c for c in CANDIDATES if c.name == winner["config"])
    return {
        "outer_test_year": int(outer_year),
        "selection_status": "TRAINING_ONLY_SELECTED",
        "n_inner_years": int(len(inner_years)),
        "inner_years": ";".join(map(str, inner_years)),
        "selected_config": cfg.name,
        "selected_e_rank": int(cfg.e_rank),
        "selected_gamma_multiplier": float(cfg.gamma_multiplier),
        "selected_alpha": float(cfg.alpha),
        "mean_inner_year_rmse": float(winner["mean_inner_year_rmse"]),
        "pooled_inner_rmse": float(winner["pooled_inner_rmse"]),
        "mean_inner_year_mae": float(winner["mean_inner_year_mae"]),
        "outer_outcome_used_for_selection": False,
    }


def _config_from_selection(row: pd.Series) -> TransferConfig:
    if str(row["selection_status"]) == "INSUFFICIENT_HISTORY_FALLBACK":
        return FROZEN_CONFIG
    name = str(row["selected_config"])
    return next(c for c in CANDIDATES if c.name == name)


def _cells_with_year(cells: pd.DataFrame) -> pd.DataFrame:
    out = cells.copy()
    out["year"] = _year_from_environment(out["environment"])
    return out


def _gmap(geno: pd.DataFrame, geno_id_col: str, train: pd.DataFrame):
    return genomic_map(geno, geno_id_col, set(train["genotype"].astype(str)), rank=FROZEN_CONFIG.g_rank)


def _predict_ge(train: pd.DataFrame, test: pd.DataFrame, gmap, emap, alpha: float) -> np.ndarray:
    tg, te = cell_features(train, gmap, emap)
    vg, ve = cell_features(test, gmap, emap)
    return predict(
        "G+E",
        tg,
        te,
        train["observed"].to_numpy(float),
        vg,
        ve,
        alpha,
    )


def build_inner_evidence(
    cells: pd.DataFrame,
    geno: pd.DataFrame,
    geno_id_col: str,
    t2_matrix: pd.DataFrame,
    available_years: list[int],
) -> pd.DataFrame:
    """Evaluate every candidate once per historical chronological inner year."""

    rows: list[dict[str, object]] = []
    years = sorted(int(v) for v in available_years)
    # 2021 is the final outer test year, so the latest usable inner year is 2020.
    for inner_year in years[1:-1]:
        train = cells[cells["year"] < inner_year].copy()
        valid = cells[cells["year"] == inner_year].copy()
        if train.empty or valid.empty:
            raise ValueError(f"Inner chronological split {inner_year} is empty.")
        if int(train["year"].max()) >= int(inner_year):
            raise ValueError("B10-S inner chronology violated.")
        train_envs = set(train["environment"].astype(str))
        gmap = _gmap(geno, geno_id_col, train)
        for cfg in CANDIDATES:
            rank = min(int(cfg.e_rank), max(1, len(train_envs) - 1))
            emap = environment_map(t2_matrix, train_envs, rank, cfg.gamma_multiplier)
            pred = _predict_ge(train, valid, gmap, emap, cfg.alpha)
            y = valid["observed"].to_numpy(float)
            err = y - pred
            row = {
                "inner_test_year": int(inner_year),
                "inner_train_year_max": int(train["year"].max()),
                "n_train_environments": int(train["environment"].nunique()),
                "n_valid_environments": int(valid["environment"].nunique()),
                "n": int(len(valid)),
                "config": cfg.name,
                "e_rank_requested": int(cfg.e_rank),
                "e_rank_effective": int(emap.metadata.get("feature_dim", rank)),
                "gamma_multiplier": float(cfg.gamma_multiplier),
                "rbf_gamma": float(emap.metadata.get("rbf_gamma", np.nan)),
                "alpha": float(cfg.alpha),
                "sse": float(np.sum(err * err)),
                "sae": float(np.sum(np.abs(err))),
                "rmse": float(np.sqrt(np.mean(err * err))),
                "mae": float(np.mean(np.abs(err))),
                "outer_outcome_used": False,
            }
            rows.append(row)
    return pd.DataFrame(rows)


def _add_prediction(
    store: list[pd.DataFrame],
    test: pd.DataFrame,
    model: str,
    pred: np.ndarray,
    outer_year: int,
    selection: pd.Series,
) -> None:
    out = test[["genotype", "environment", "observed"]].copy()
    out["test_year"] = int(outer_year)
    out["model"] = model
    out["predicted"] = np.asarray(pred, float)
    out["selection_status"] = str(selection["selection_status"])
    out["selected_config"] = str(selection["selected_config"])
    out["outer_outcome_used_for_selection"] = False
    store.append(out)


def run_outer_predictions(
    cells: pd.DataFrame,
    geno: pd.DataFrame,
    geno_id_col: str,
    matrices: dict[str, pd.DataFrame],
    forward_manifest: pd.DataFrame,
    selections: pd.DataFrame,
) -> pd.DataFrame:
    predictions: list[pd.DataFrame] = []
    for outer_year in sorted(forward_manifest["test_year"].astype(int).unique()):
        part = forward_manifest[forward_manifest["test_year"].astype(int).eq(outer_year)]
        train_year_max_values = part["train_year_max"].astype(int).unique()
        if len(train_year_max_values) != 1:
            raise ValueError(f"Outer year {outer_year} has inconsistent B9 train-year lock.")
        train_year_max = int(train_year_max_values[0])
        train = cells[cells["year"] <= train_year_max].copy()
        test_envs = set(part["environment"].astype(str))
        test = cells[cells["environment"].astype(str).isin(test_envs)].copy()
        if train.empty or test.empty or int(train["year"].max()) >= outer_year:
            raise ValueError(f"Invalid outer partition for {outer_year}.")
        selection = selections[selections["outer_test_year"].astype(int).eq(outer_year)].iloc[0]
        selected_cfg = _config_from_selection(selection)
        train_envs = set(train["environment"].astype(str))
        gmap = _gmap(geno, geno_id_col, train)

        frozen_t1 = environment_map(
            matrices[T1_HORIZON],
            train_envs,
            min(FROZEN_CONFIG.e_rank, max(1, len(train_envs) - 1)),
            FROZEN_CONFIG.gamma_multiplier,
        )
        frozen_t2 = environment_map(
            matrices[T2_HORIZON],
            train_envs,
            min(FROZEN_CONFIG.e_rank, max(1, len(train_envs) - 1)),
            FROZEN_CONFIG.gamma_multiplier,
        )
        selected_t2 = environment_map(
            matrices[T2_HORIZON],
            train_envs,
            min(selected_cfg.e_rank, max(1, len(train_envs) - 1)),
            selected_cfg.gamma_multiplier,
        )

        _add_prediction(
            predictions,
            test,
            "Frozen-T1",
            _predict_ge(train, test, gmap, frozen_t1, FROZEN_CONFIG.alpha),
            outer_year,
            selection,
        )
        _add_prediction(
            predictions,
            test,
            "Frozen-T2",
            _predict_ge(train, test, gmap, frozen_t2, FROZEN_CONFIG.alpha),
            outer_year,
            selection,
        )
        _add_prediction(
            predictions,
            test,
            "Selected-T2",
            _predict_ge(train, test, gmap, selected_t2, selected_cfg.alpha),
            outer_year,
            selection,
        )
    return pd.concat(predictions, ignore_index=True)


def summarize_predictions(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pooled_rows: list[dict[str, object]] = []
    year_rows: list[dict[str, object]] = []
    env_rows: list[dict[str, object]] = []
    for model, part in predictions.groupby("model"):
        pooled_rows.append(
            {
                "model": model,
                "n": int(len(part)),
                "n_environments": int(part["environment"].nunique()),
                "n_test_years": int(part["test_year"].nunique()),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    for (year, model), part in predictions.groupby(["test_year", "model"]):
        year_rows.append(
            {
                "test_year": int(year),
                "model": model,
                "n": int(len(part)),
                "n_environments": int(part["environment"].nunique()),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    for (env, year, model), part in predictions.groupby(["environment", "test_year", "model"]):
        env_rows.append(
            {
                "environment": str(env),
                "test_year": int(year),
                "model": model,
                "n": int(len(part)),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    return pd.DataFrame(pooled_rows), pd.DataFrame(year_rows), pd.DataFrame(env_rows)


def _paired_frame(predictions: pd.DataFrame) -> pd.DataFrame:
    pivot = predictions.pivot_table(
        index=["genotype", "environment", "observed", "test_year"],
        columns="model",
        values="predicted",
        aggfunc="first",
    ).reset_index()
    expected = {"Frozen-T1", "Frozen-T2", "Selected-T2"}
    if not expected.issubset(pivot.columns):
        raise ValueError("B10-S paired predictions are incomplete.")
    return pivot


def paired_cluster_bootstrap(predictions: pd.DataFrame, reps: int = BOOTSTRAP_REPS) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    pivot = _paired_frame(predictions)
    rows: list[dict[str, object]] = []
    y = pivot["observed"].to_numpy(float)
    for challenger, reference, comparison in PAIR_SPECS:
        sq_ch = (y - pivot[challenger].to_numpy(float)) ** 2
        sq_ref = (y - pivot[reference].to_numpy(float)) ** 2
        point = float(np.sqrt(np.mean(sq_ch)) - np.sqrt(np.mean(sq_ref)))
        for cluster in ("environment", "test_year"):
            clustered = (
                pd.DataFrame(
                    {
                        "cluster": pivot[cluster].astype(str),
                        "sq_ch": sq_ch,
                        "sq_ref": sq_ref,
                    }
                )
                .groupby("cluster")
                .agg(s_ch=("sq_ch", "sum"), s_ref=("sq_ref", "sum"), n=("sq_ch", "size"))
            )
            labels = np.asarray(clustered.index.astype(str))
            boots = np.empty(reps, dtype=float)
            for i in range(reps):
                sample = rng.choice(labels, size=len(labels), replace=True)
                picked = clustered.loc[sample]
                n = float(picked["n"].sum())
                boots[i] = np.sqrt(float(picked["s_ch"].sum()) / n) - np.sqrt(float(picked["s_ref"].sum()) / n)
            rows.append(
                {
                    "comparison": comparison,
                    "challenger": challenger,
                    "reference": reference,
                    "bootstrap_cluster": cluster,
                    "n_clusters": int(len(labels)),
                    "bootstrap_reps": int(reps),
                    "delta_rmse_challenger_minus_reference": point,
                    "ci95_low": float(np.quantile(boots, 0.025)),
                    "ci95_high": float(np.quantile(boots, 0.975)),
                    "improvement_frequency": float(np.mean(boots < 0.0)),
                }
            )
    return pd.DataFrame(rows)


def verify_b10_reproduction(root: Path, year_metrics: pd.DataFrame, tolerance: float = 1e-8) -> pd.DataFrame:
    path = root / "reports" / "results" / "case_study_b10_forward_year_metrics.csv"
    reference = pd.read_csv(path)
    reference = reference[reference["model"].isin(["G+E_T1", "G+E_T2"])].copy()
    mapping = {"G+E_T1": "Frozen-T1", "G+E_T2": "Frozen-T2"}
    reference["model"] = reference["model"].map(mapping)
    merged = year_metrics.merge(
        reference[["test_year", "model", "rmse"]].rename(columns={"rmse": "b10_reference_rmse"}),
        on=["test_year", "model"],
        how="inner",
        validate="one_to_one",
    )
    merged = merged[merged["model"].isin(["Frozen-T1", "Frozen-T2"])].copy()
    merged["absolute_rmse_difference"] = np.abs(merged["rmse"] - merged["b10_reference_rmse"])
    merged["within_tolerance"] = merged["absolute_rmse_difference"] <= tolerance
    if len(merged) != 12 or not merged["within_tolerance"].all():
        raise ValueError("B10-S failed to reproduce frozen B10 forward-year T1/T2 metrics.")
    return merged[["test_year", "model", "rmse", "b10_reference_rmse", "absolute_rmse_difference", "within_tolerance"]]


def oracle_regret(root: Path, selections: pd.DataFrame, year_metrics: pd.DataFrame) -> pd.DataFrame:
    path = root / "reports" / "results" / "case_study_b10r_geometry_sensitivity_by_year.csv"
    grid = pd.read_csv(path)
    selected = year_metrics[year_metrics["model"].eq("Selected-T2")][["test_year", "rmse"]].rename(
        columns={"rmse": "selected_t2_rmse"}
    )
    rows: list[dict[str, object]] = []
    for year, part in grid.groupby("test_year"):
        best = part.sort_values("rmse").iloc[0]
        sel = selections[selections["outer_test_year"].astype(int).eq(int(year))].iloc[0]
        rmse = float(selected.loc[selected["test_year"].astype(int).eq(int(year)), "selected_t2_rmse"].iloc[0])
        rows.append(
            {
                "test_year": int(year),
                "selection_status": str(sel["selection_status"]),
                "training_only_selected_config": str(sel["selected_config"]),
                "training_only_selected_rmse": rmse,
                "oracle_diagnostic_config": str(best["config"]),
                "oracle_diagnostic_rmse": float(best["rmse"]),
                "training_only_rmse_minus_oracle": rmse - float(best["rmse"]),
                "oracle_uses_outer_outcome": True,
                "oracle_admitted_for_deployment": False,
            }
        )
    return pd.DataFrame(rows)


def make_figure(year_metrics: pd.DataFrame, selections: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.8, 7.6))
    years = sorted(year_metrics["test_year"].astype(int).unique())
    for model in ("Frozen-T1", "Frozen-T2", "Selected-T2"):
        part = year_metrics[year_metrics["model"].eq(model)].set_index("test_year").loc[years]
        ax.plot(years, part["rmse"].to_numpy(float), marker="o", linewidth=2.2, label=model)
    for _, row in selections.iterrows():
        year = int(row["outer_test_year"])
        selected_rmse = float(
            year_metrics[(year_metrics["test_year"].eq(year)) & (year_metrics["model"].eq("Selected-T2"))]["rmse"].iloc[0]
        )
        label = "fallback" if row["selection_status"] == "INSUFFICIENT_HISTORY_FALLBACK" else str(row["selected_config"]).replace("diagnostic_", "")
        ax.annotate(label, (year, selected_rmse), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8)
    ax.set_xlabel("Forward test year")
    ax.set_ylabel("Out-of-sample RMSE")
    ax.set_title("Case Study B10-S — training-only selection of T2 spectral geometry")
    ax.grid(axis="y", alpha=0.25)
    # Repository figure convention: horizontal legend outside and below plot.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
    fig.subplots_adjust(bottom=0.27)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(root: Path) -> dict[str, Path]:
    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    states = pd.read_csv(results / "case_study_b9_safe_environment_states.csv")
    env_manifest = pd.read_csv(results / "case_study_b9_environment_manifest.csv")
    forward = pd.read_csv(results / "case_study_b9_forward_year_folds.csv")
    validate_b9_inputs(states, env_manifest, forward)

    pheno, geno, ecov = load_materialized(root)
    cells, geno, _, cols = prepare_cells(pheno, geno, ecov)
    cells = _cells_with_year(cells)
    matrices, _ = build_environment_state_matrices(states, env_manifest)
    available_years = sorted(env_manifest["year"].astype(int).unique().tolist())

    inner = build_inner_evidence(cells, geno, cols["geno_id"], matrices[T2_HORIZON], available_years)
    selection_rows = [select_candidate(inner, int(year)) for year in sorted(forward["test_year"].astype(int).unique())]
    selections = pd.DataFrame(selection_rows)
    if selections.loc[selections["outer_test_year"].eq(2016), "selection_status"].iloc[0] != "INSUFFICIENT_HISTORY_FALLBACK":
        raise ValueError("B10-S must encode 2016 as insufficient-history fallback.")
    if selections["outer_outcome_used_for_selection"].astype(bool).any():
        raise ValueError("B10-S selection audit detected outer-outcome use.")

    predictions = run_outer_predictions(cells, geno, cols["geno_id"], matrices, forward, selections)
    pooled, year_metrics, env_metrics = summarize_predictions(predictions)
    reproduction = verify_b10_reproduction(root, year_metrics)
    bootstrap = paired_cluster_bootstrap(predictions)
    regret = oracle_regret(root, selections, year_metrics)

    paths = {
        "inner_evidence": results / "case_study_b10s_inner_chronological_evidence.csv",
        "selection": results / "case_study_b10s_selection_audit.csv",
        "summary": results / "case_study_b10s_forward_summary.csv",
        "year_metrics": results / "case_study_b10s_forward_year_metrics.csv",
        "environment_metrics": results / "case_study_b10s_environment_metrics.csv",
        "bootstrap": results / "case_study_b10s_paired_bootstrap.csv",
        "reproduction": results / "case_study_b10s_b10_reproduction_audit.csv",
        "oracle_regret": results / "case_study_b10s_oracle_regret.csv",
        "figure": figures / "case_study_b10s_training_only_geometry.png",
    }
    results.mkdir(parents=True, exist_ok=True)
    inner.to_csv(paths["inner_evidence"], index=False)
    selections.to_csv(paths["selection"], index=False)
    pooled.to_csv(paths["summary"], index=False)
    year_metrics.to_csv(paths["year_metrics"], index=False)
    env_metrics.to_csv(paths["environment_metrics"], index=False)
    bootstrap.to_csv(paths["bootstrap"], index=False)
    reproduction.to_csv(paths["reproduction"], index=False)
    regret.to_csv(paths["oracle_regret"], index=False)
    make_figure(year_metrics, selections, paths["figure"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Case Study B10-S training-only T2 geometry selection.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B10-S training-only geometry selection complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
