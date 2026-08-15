"""Case Study B10-U: geometry-agnostic robust T2 aggregation.

B10-U is a finite stopping experiment after B10-R/B10-S/B10-T showed that
selecting one T2 spectral geometry is brittle across forward years. It does not
select, rank, tune, or learn weights over geometries. It symmetrically aggregates
exactly the 12 B10-R T2 predictions using two predeclared rules:

    mean12   = arithmetic mean of the 12 predictions
    median12 = coordinate-wise median of the 12 predictions

The B9 issuance-safe T2 state, six forward years, genomic rank, ridge alpha, and
12-member rank/bandwidth family remain unchanged. Frozen B10 T1 and T2 are
reproduced in the same outer partitions for paired comparison.

Stopping rule
-------------
An aggregate can keep the T2 adaptive branch open only if it simultaneously:
1. beats frozen T1 in pooled RMSE;
2. has both environment-cluster and year-cluster paired 95% RMSE-difference
   intervals entirely below zero; and
3. reduces both the worst-year RMSE and across-year RMSE range relative to
   frozen T2.

Otherwise B10-U closes the T2 adaptive branch for this dataset. The criterion is
predeclared in code and contains no learned ensemble weights or post-result
threshold tuning.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_transfer import BOOTSTRAP_REPS, prepare_cells
from plant_intelligence.models.maize_environment_transfer_robustness import (
    environment_map,
    genomic_map,
    load_materialized,
    metrics,
)
from plant_intelligence.models.maize_forecast_time_prediction import (
    FROZEN_CONFIG,
    STATE_BY_MODEL,
    build_environment_state_matrices,
    validate_b9_inputs,
)
from plant_intelligence.models.maize_forward_support_diagnostics import (
    DIAGNOSTIC_GRID,
    _forward_partitions,
)
from plant_intelligence.models.maize_training_only_geometry_selection import _predict_ge

SEED = 20260813
T1_HORIZON = STATE_BY_MODEL["G+E_T1"]
T2_HORIZON = STATE_BY_MODEL["G+E_T2"]
EXPECTED_YEARS = (2016, 2017, 2018, 2019, 2020, 2021)
AGGREGATE_MODELS = ("T2-Mean12", "T2-Median12")
MODEL_ORDER = ("Frozen-T1", "Frozen-T2", *AGGREGATE_MODELS)
PAIR_SPECS = (
    ("T2-Mean12", "Frozen-T1", "mean12_vs_frozen_T1"),
    ("T2-Median12", "Frozen-T1", "median12_vs_frozen_T1"),
    ("T2-Mean12", "Frozen-T2", "mean12_vs_frozen_T2"),
    ("T2-Median12", "Frozen-T2", "median12_vs_frozen_T2"),
)


def validate_geometry_family() -> None:
    """Refuse any silent change to the frozen 3x4 B10-R geometry family."""
    if len(DIAGNOSTIC_GRID) != 12:
        raise ValueError("B10-U requires exactly the 12 frozen B10-R geometries.")
    ranks = sorted({int(cfg.e_rank) for cfg in DIAGNOSTIC_GRID})
    gammas = sorted({float(cfg.gamma_multiplier) for cfg in DIAGNOSTIC_GRID})
    if ranks != [8, 16, 32] or gammas != [0.5, 1.0, 2.0, 4.0]:
        raise ValueError("B10-U geometry family differs from the frozen B10-R 3x4 grid.")
    if any(int(cfg.g_rank) != int(FROZEN_CONFIG.g_rank) for cfg in DIAGNOSTIC_GRID):
        raise ValueError("B10-U requires the frozen genomic rank for every geometry.")
    if any(not np.isclose(float(cfg.alpha), float(FROZEN_CONFIG.alpha)) for cfg in DIAGNOSTIC_GRID):
        raise ValueError("B10-U requires the frozen ridge alpha for every geometry.")


def aggregate_geometry_predictions(prediction_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return symmetric mean and median across the frozen geometry dimension."""
    values = np.asarray(prediction_matrix, dtype=float)
    if values.ndim != 2 or values.shape[1] != 12:
        raise ValueError("B10-U aggregation requires an n x 12 prediction matrix.")
    if not np.isfinite(values).all():
        raise ValueError("B10-U refuses non-finite geometry predictions.")
    return values.mean(axis=1), np.median(values, axis=1)


def _add_prediction(
    store: list[pd.DataFrame],
    test: pd.DataFrame,
    test_year: int,
    model: str,
    predicted: np.ndarray,
) -> None:
    out = test[["genotype", "environment", "observed"]].copy()
    out["test_year"] = int(test_year)
    out["model"] = model
    out["predicted"] = np.asarray(predicted, dtype=float)
    out["geometry_count"] = 12 if model in AGGREGATE_MODELS else 1
    out["weighting"] = "equal_mean" if model == "T2-Mean12" else (
        "coordinate_median" if model == "T2-Median12" else "single_frozen_geometry"
    )
    out["outer_outcome_used_for_aggregation"] = False
    store.append(out)


def _predict_geometry_grid(
    train: pd.DataFrame,
    test: pd.DataFrame,
    gmap,
    t2_matrix: pd.DataFrame,
    train_envs: set[str],
) -> np.ndarray:
    """Reproduce all 12 B10-R T2 predictions without using test outcomes."""
    columns: list[np.ndarray] = []
    for cfg in DIAGNOSTIC_GRID:
        rank = min(int(cfg.e_rank), max(1, len(train_envs) - 1))
        emap = environment_map(t2_matrix, train_envs, rank, cfg.gamma_multiplier)
        columns.append(_predict_ge(train, test, gmap, emap, cfg.alpha))
    return np.column_stack(columns)


def run_forward_predictions(
    root: Path,
    states: pd.DataFrame,
    env_manifest: pd.DataFrame,
    forward: pd.DataFrame,
) -> pd.DataFrame:
    validate_geometry_family()
    pheno, geno, ecov = load_materialized(root)
    cells, geno, _, cols = prepare_cells(pheno, geno, ecov)
    matrices, _ = build_environment_state_matrices(states, env_manifest)
    predictions: list[pd.DataFrame] = []

    partitions = _forward_partitions(env_manifest, forward)
    if tuple(int(v[0]) for v in partitions) != EXPECTED_YEARS:
        raise ValueError("B10-U must retain the exact six locked B9 forward test years.")

    for test_year, train_year_max, train_envs, test_envs in partitions:
        train = cells[cells["environment"].astype(str).isin(train_envs)].copy()
        test = cells[cells["environment"].astype(str).isin(test_envs)].copy()
        if train.empty or test.empty:
            raise ValueError(f"B10-U produced an empty partition for {test_year}.")
        train_years = pd.to_numeric(train["environment"].astype(str).str[:4], errors="raise").astype(int)
        if int(train_years.max()) != int(train_year_max) or int(train_year_max) >= int(test_year):
            raise ValueError("B10-U chronology does not match the B9 forward-year lock.")

        train_env_ids = set(train["environment"].astype(str))
        gmap = genomic_map(
            geno,
            cols["geno_id"],
            set(train["genotype"].astype(str)),
            rank=FROZEN_CONFIG.g_rank,
        )

        frozen_t1_map = environment_map(
            matrices[T1_HORIZON],
            train_env_ids,
            min(FROZEN_CONFIG.e_rank, max(1, len(train_env_ids) - 1)),
            FROZEN_CONFIG.gamma_multiplier,
        )
        frozen_t2_map = environment_map(
            matrices[T2_HORIZON],
            train_env_ids,
            min(FROZEN_CONFIG.e_rank, max(1, len(train_env_ids) - 1)),
            FROZEN_CONFIG.gamma_multiplier,
        )
        frozen_t1 = _predict_ge(train, test, gmap, frozen_t1_map, FROZEN_CONFIG.alpha)
        frozen_t2 = _predict_ge(train, test, gmap, frozen_t2_map, FROZEN_CONFIG.alpha)

        grid = _predict_geometry_grid(train, test, gmap, matrices[T2_HORIZON], train_env_ids)
        mean12, median12 = aggregate_geometry_predictions(grid)

        _add_prediction(predictions, test, test_year, "Frozen-T1", frozen_t1)
        _add_prediction(predictions, test, test_year, "Frozen-T2", frozen_t2)
        _add_prediction(predictions, test, test_year, "T2-Mean12", mean12)
        _add_prediction(predictions, test, test_year, "T2-Median12", median12)

    out = pd.concat(predictions, ignore_index=True)
    if set(out["model"].astype(str)) != set(MODEL_ORDER):
        raise ValueError("B10-U prediction output is missing a predeclared model.")
    return out


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
    for (environment, year, model), part in predictions.groupby(["environment", "test_year", "model"]):
        env_rows.append(
            {
                "environment": str(environment),
                "test_year": int(year),
                "model": model,
                "n": int(len(part)),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    pooled = pd.DataFrame(pooled_rows)
    pooled["model_order"] = pooled["model"].map({m: i for i, m in enumerate(MODEL_ORDER)})
    pooled = pooled.sort_values("model_order").drop(columns="model_order").reset_index(drop=True)
    years = pd.DataFrame(year_rows)
    years["model_order"] = years["model"].map({m: i for i, m in enumerate(MODEL_ORDER)})
    years = years.sort_values(["test_year", "model_order"]).drop(columns="model_order").reset_index(drop=True)
    return pooled, years, pd.DataFrame(env_rows)


def _paired_frame(predictions: pd.DataFrame) -> pd.DataFrame:
    pivot = predictions.pivot_table(
        index=["genotype", "environment", "observed", "test_year"],
        columns="model",
        values="predicted",
        aggfunc="first",
    ).reset_index()
    if not set(MODEL_ORDER).issubset(pivot.columns):
        raise ValueError("B10-U paired prediction matrix is incomplete.")
    return pivot


def paired_cluster_bootstrap(predictions: pd.DataFrame, reps: int = BOOTSTRAP_REPS) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    pivot = _paired_frame(predictions)
    y = pivot["observed"].to_numpy(float)
    rows: list[dict[str, object]] = []
    for challenger, reference, comparison in PAIR_SPECS:
        sq_ch = np.square(y - pivot[challenger].to_numpy(float))
        sq_ref = np.square(y - pivot[reference].to_numpy(float))
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
            if len(labels) < 2:
                raise ValueError("B10-U cluster bootstrap requires at least two clusters.")
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
    reference = pd.read_csv(root / "reports" / "results" / "case_study_b10_forward_year_metrics.csv")
    reference = reference[reference["model"].isin(["G+E_T1", "G+E_T2"])].copy()
    reference["model"] = reference["model"].map({"G+E_T1": "Frozen-T1", "G+E_T2": "Frozen-T2"})
    reproduced = year_metrics[year_metrics["model"].isin(["Frozen-T1", "Frozen-T2"])].copy()
    merged = reproduced.merge(
        reference[["test_year", "model", "rmse"]].rename(columns={"rmse": "b10_reference_rmse"}),
        on=["test_year", "model"],
        validate="one_to_one",
    )
    merged["absolute_rmse_difference"] = np.abs(merged["rmse"] - merged["b10_reference_rmse"])
    merged["within_tolerance"] = merged["absolute_rmse_difference"] <= tolerance
    if len(merged) != 12 or not merged["within_tolerance"].all():
        raise ValueError("B10-U failed to reproduce frozen B10 T1/T2 year metrics.")
    return merged[["test_year", "model", "rmse", "b10_reference_rmse", "absolute_rmse_difference", "within_tolerance"]]


def instability_audit(year_metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model, part in year_metrics.groupby("model"):
        rmse = part.sort_values("test_year")["rmse"].to_numpy(float)
        rows.append(
            {
                "model": model,
                "worst_year_rmse": float(np.max(rmse)),
                "best_year_rmse": float(np.min(rmse)),
                "year_rmse_range": float(np.max(rmse) - np.min(rmse)),
                "year_rmse_sd": float(np.std(rmse, ddof=1)),
                "worst_year": int(part.iloc[int(np.argmax(rmse))]["test_year"]),
            }
        )
    audit = pd.DataFrame(rows)
    t1 = year_metrics[year_metrics["model"].eq("Frozen-T1")].set_index("test_year")["rmse"]
    for model in AGGREGATE_MODELS:
        mask = audit["model"].eq(model)
        values = year_metrics[year_metrics["model"].eq(model)].set_index("test_year")["rmse"].reindex(t1.index)
        audit.loc[mask, "years_beating_frozen_t1"] = int((values < t1).sum())
        audit.loc[mask, "max_year_deterioration_vs_frozen_t1"] = float((values - t1).max())
    return audit


def stopping_decision(
    pooled: pd.DataFrame,
    year_metrics: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> pd.DataFrame:
    """Apply the predeclared finite B10-U stop rule without tuning thresholds."""
    instability = instability_audit(year_metrics).set_index("model")
    t1_rmse = float(pooled.loc[pooled["model"].eq("Frozen-T1"), "rmse"].iloc[0])
    frozen_t2 = instability.loc["Frozen-T2"]
    rows: list[dict[str, object]] = []
    for model in AGGREGATE_MODELS:
        rmse = float(pooled.loc[pooled["model"].eq(model), "rmse"].iloc[0])
        comp = bootstrap[
            bootstrap["challenger"].eq(model) & bootstrap["reference"].eq("Frozen-T1")
        ].set_index("bootstrap_cluster")
        if not {"environment", "test_year"}.issubset(comp.index):
            raise ValueError("B10-U stopping rule requires both environment and year bootstrap views.")
        env_upper = float(comp.loc["environment", "ci95_high"])
        year_upper = float(comp.loc["test_year", "ci95_high"])
        robust_t1 = bool(rmse < t1_rmse and env_upper < 0.0 and year_upper < 0.0)
        stable_vs_t2 = bool(
            float(instability.loc[model, "worst_year_rmse"]) < float(frozen_t2["worst_year_rmse"])
            and float(instability.loc[model, "year_rmse_range"]) < float(frozen_t2["year_rmse_range"])
        )
        rows.append(
            {
                "aggregate": model,
                "pooled_rmse": rmse,
                "frozen_t1_pooled_rmse": t1_rmse,
                "delta_rmse_vs_frozen_t1": rmse - t1_rmse,
                "environment_ci95_high_vs_t1": env_upper,
                "year_ci95_high_vs_t1": year_upper,
                "robust_pooled_improvement_over_t1": robust_t1,
                "worst_year_rmse": float(instability.loc[model, "worst_year_rmse"]),
                "frozen_t2_worst_year_rmse": float(frozen_t2["worst_year_rmse"]),
                "year_rmse_range": float(instability.loc[model, "year_rmse_range"]),
                "frozen_t2_year_rmse_range": float(frozen_t2["year_rmse_range"]),
                "reduced_catastrophic_instability_vs_frozen_t2": stable_vs_t2,
                "years_beating_frozen_t1": int(instability.loc[model, "years_beating_frozen_t1"]),
                "max_year_deterioration_vs_frozen_t1": float(instability.loc[model, "max_year_deterioration_vs_frozen_t1"]),
                "aggregate_admitted": bool(robust_t1 and stable_vs_t2),
            }
        )
    out = pd.DataFrame(rows)
    branch = "KEEP_T2_AGGREGATION_BRANCH_OPEN" if out["aggregate_admitted"].any() else "CLOSE_T2_ADAPTIVE_BRANCH_USE_SUPPORTED_T1"
    out["branch_decision"] = branch
    out["post_result_tuning_permitted"] = False
    return out


def make_figure(year_metrics: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.8, 7.6))
    for model in MODEL_ORDER:
        part = year_metrics[year_metrics["model"].eq(model)].sort_values("test_year")
        ax.plot(part["test_year"], part["rmse"], marker="o", linewidth=2.1, label=model)
    ax.set_xlabel("Forward test year")
    ax.set_ylabel("Out-of-sample RMSE")
    ax.set_title("Case Study B10-U — geometry-agnostic T2 aggregation")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, frameon=False)
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

    predictions = run_forward_predictions(root, states, env_manifest, forward)
    pooled, years, environments = summarize_predictions(predictions)
    reproduction = verify_b10_reproduction(root, years)
    bootstrap = paired_cluster_bootstrap(predictions)
    instability = instability_audit(years)
    decision = stopping_decision(pooled, years, bootstrap)

    paths = {
        "predictions": results / "case_study_b10u_predictions.csv",
        "summary": results / "case_study_b10u_summary.csv",
        "year_metrics": results / "case_study_b10u_forward_year_metrics.csv",
        "environment_metrics": results / "case_study_b10u_environment_metrics.csv",
        "bootstrap": results / "case_study_b10u_paired_bootstrap.csv",
        "instability": results / "case_study_b10u_instability_audit.csv",
        "reproduction": results / "case_study_b10u_b10_reproduction_audit.csv",
        "decision": results / "case_study_b10u_branch_decision.csv",
        "figure": figures / "case_study_b10u_robust_aggregation.png",
    }
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(paths["predictions"], index=False)
    pooled.to_csv(paths["summary"], index=False)
    years.to_csv(paths["year_metrics"], index=False)
    environments.to_csv(paths["environment_metrics"], index=False)
    bootstrap.to_csv(paths["bootstrap"], index=False)
    instability.to_csv(paths["instability"], index=False)
    reproduction.to_csv(paths["reproduction"], index=False)
    decision.to_csv(paths["decision"], index=False)
    make_figure(years, paths["figure"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Case Study B10-U robust T2 geometry aggregation.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B10-U geometry-agnostic aggregation complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
