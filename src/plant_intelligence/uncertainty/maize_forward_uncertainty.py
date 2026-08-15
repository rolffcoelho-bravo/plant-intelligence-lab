"""Case Study B11: forward-time uncertainty calibration and selective prediction.

B11 freezes the supported B10 T1 predictor and adds a strictly chronological
reliability layer. No predictive-model hyperparameter is changed and the closed
T2 adaptive-geometry branch is not reopened.

For a forecast year t, interval calibration may use only residuals from locked
forward-year predictions with year < t. At least two prior forward validation
years are required. Earlier years are emitted as
INSUFFICIENT_CALIBRATION_HISTORY rather than receiving manufactured intervals.

Two interval constructions are audited:

1. GLOBAL_FORWARD: finite-sample absolute-residual quantiles from all prior
   forward years.
2. SUPPORT_ADAPTIVE: the same chronological residual quantile, stratified by a
   predeclared outcome-free environmental-support boundary when the historical
   stratum has enough environments/cells; otherwise it falls back to the global
   chronological quantile.

The hard reliability state is outcome-free. A test environment is marked
ABSTAIN_LOW_ENVIRONMENT_SUPPORT when its nearest training-environment distance
is at or beyond the maximum internal nearest-neighbour spacing of the current
training set (``full_nearest_percentile == 1``). This boundary is computed from
T1 information available at forecast time and never from yield.

Selective-risk curves are retrospective diagnostics only; they do not tune a
new abstention threshold.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from plant_intelligence.models.maize_environment_transfer import prepare_cells
from plant_intelligence.models.maize_environment_transfer_robustness import (
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
    WEATHER_COLUMNS,
    build_environment_state_matrices,
    validate_b9_inputs,
)
from plant_intelligence.models.maize_forward_support_diagnostics import (
    _forward_partitions,
    context_support,
    support_geometry,
)

SEED = 20260815
MODEL = "G+E_T1"
HORIZON = STATE_BY_MODEL[MODEL]
NOMINAL_LEVELS = (0.80, 0.90, 0.95)
MIN_CALIBRATION_YEARS = 2
MIN_SUPPORT_GROUP_ENVIRONMENTS = 5
MIN_SUPPORT_GROUP_CELLS = 200
SUPPORT_WITHIN = "WITHIN_TRAINING_NN_ENVELOPE"
SUPPORT_EDGE = "AT_OR_BEYOND_TRAINING_NN_ENVELOPE"
RETAIN = "RETAIN_SUPPORTED"
ABSTAIN = "ABSTAIN_LOW_ENVIRONMENT_SUPPORT"
INSUFFICIENT = "INSUFFICIENT_CALIBRATION_HISTORY"
BOOTSTRAP_REPS = 2000
SELECTIVE_RETENTION = (1.00, 0.95, 0.90, 0.80, 0.70)


@dataclass(frozen=True)
class CalibrationQuantile:
    value: float
    source: str
    n_cells: int
    n_environments: int


def finite_sample_quantile(scores: np.ndarray | pd.Series, level: float) -> float:
    """Finite-sample conformal-style quantile of non-negative residual scores."""

    values = np.asarray(scores, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        raise ValueError("Cannot calibrate an interval from zero residual scores.")
    if not 0.0 < float(level) < 1.0:
        raise ValueError("Nominal level must lie strictly between zero and one.")
    rank = int(np.ceil((len(values) + 1) * float(level)))
    rank = min(max(rank, 1), len(values))
    return float(np.partition(values, rank - 1)[rank - 1])


def support_group(percentile: float) -> str:
    """Outcome-free support state from the training nearest-neighbour envelope."""

    value = float(percentile)
    if not np.isfinite(value):
        raise ValueError("Support percentile must be finite.")
    return SUPPORT_EDGE if value >= 1.0 - 1e-12 else SUPPORT_WITHIN


def reliability_state(calibration_years: int, group: str) -> str:
    if int(calibration_years) < MIN_CALIBRATION_YEARS:
        return INSUFFICIENT
    return ABSTAIN if str(group) == SUPPORT_EDGE else RETAIN


def _year_from_environment(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values.astype(str).str.slice(0, 4), errors="raise").astype(int)


def _predict_t1(train: pd.DataFrame, test: pd.DataFrame, geno: pd.DataFrame, geno_id_col: str, matrix: pd.DataFrame) -> np.ndarray:
    train_genotypes = set(train["genotype"].astype(str))
    train_environments = set(train["environment"].astype(str))
    gmap = genomic_map(geno, geno_id_col, train_genotypes, rank=FROZEN_CONFIG.g_rank)
    erank = min(int(FROZEN_CONFIG.e_rank), max(1, len(train_environments) - 1))
    emap = environment_map(
        matrix,
        train_environments,
        erank,
        FROZEN_CONFIG.gamma_multiplier,
    )
    tg, te = cell_features(train, gmap, emap)
    vg, ve = cell_features(test, gmap, emap)
    return predict(
        "G+E",
        tg,
        te,
        train["observed"].to_numpy(float),
        vg,
        ve,
        FROZEN_CONFIG.alpha,
    )


def build_forward_t1_predictions(
    root: Path,
    states: pd.DataFrame,
    env_manifest: pd.DataFrame,
    forward: pd.DataFrame,
) -> pd.DataFrame:
    """Reproduce only the frozen B10 T1 forward-year predictions."""

    pheno, geno, ecov = load_materialized(root)
    cells, geno, _, cols = prepare_cells(pheno, geno, ecov)
    matrices, _ = build_environment_state_matrices(states, env_manifest)
    matrix = matrices[HORIZON]
    env = env_manifest[["environment", "year"]].copy()
    env["environment"] = env["environment"].astype(str)
    env["year"] = env["year"].astype(int)

    rows: list[pd.DataFrame] = []
    for test_year, train_year_max, train_envs, test_envs in _forward_partitions(env_manifest, forward):
        train = cells[cells["environment"].astype(str).isin(train_envs)].copy()
        test = cells[cells["environment"].astype(str).isin(test_envs)].copy()
        if train.empty or test.empty:
            raise ValueError(f"B11 encountered an empty forward partition for {test_year}.")
        if int(_year_from_environment(train["environment"]).max()) >= int(test_year):
            raise ValueError("B11 forward prediction chronology violated.")
        pred = _predict_t1(train, test, geno, cols["geno_id"], matrix)
        out = test[["genotype", "environment", "observed"]].copy()
        out["test_year"] = int(test_year)
        out["train_year_max"] = int(train_year_max)
        out["predicted"] = np.asarray(pred, float)
        out["absolute_error"] = np.abs(out["observed"].to_numpy(float) - out["predicted"].to_numpy(float))
        rows.append(out)
    result = pd.concat(rows, ignore_index=True)
    if result["predicted"].isna().any():
        raise ValueError("B11 T1 prediction reproduction contains missing predictions.")
    return result


def build_t1_support_table(
    states: pd.DataFrame,
    env_manifest: pd.DataFrame,
    forward: pd.DataFrame,
) -> pd.DataFrame:
    """Compute T1 support using only each outer training environment set."""

    matrices, _ = build_environment_state_matrices(states, env_manifest)
    matrix = matrices[HORIZON]
    rows: list[pd.DataFrame] = []
    for test_year, train_year_max, train_ids, test_ids in _forward_partitions(env_manifest, forward):
        full, geometry = support_geometry(
            matrix,
            train_ids,
            test_ids,
            gamma_multiplier=FROZEN_CONFIG.gamma_multiplier,
            retained_rank=FROZEN_CONFIG.e_rank,
            prefix="full",
        )
        weather, _ = support_geometry(
            matrix.loc[:, list(WEATHER_COLUMNS)],
            train_ids,
            test_ids,
            gamma_multiplier=FROZEN_CONFIG.gamma_multiplier,
            retained_rank=min(FROZEN_CONFIG.e_rank, len(WEATHER_COLUMNS)),
            prefix="weather",
        )
        context = context_support(env_manifest, states, train_ids, test_ids)
        part = full.merge(weather, on="environment", validate="one_to_one").merge(
            context,
            on="environment",
            validate="one_to_one",
        )
        part["test_year"] = int(test_year)
        part["train_year_max"] = int(train_year_max)
        part["n_train_environments"] = int(len(train_ids))
        part["full_training_kernel_effective_rank"] = float(geometry.effective_rank)
        part["support_group"] = part["full_nearest_percentile"].map(support_group)
        part["support_boundary_uses_outcome"] = False
        rows.append(part)
    out = pd.concat(rows, ignore_index=True)
    if out.duplicated(["environment", "test_year"]).any():
        raise ValueError("B11 T1 support table is not unique by environment/year.")
    return out


def _adaptive_quantile(
    calibration: pd.DataFrame,
    group: str,
    level: float,
    global_q: float,
) -> CalibrationQuantile:
    part = calibration[calibration["support_group"].astype(str).eq(str(group))]
    n_env = int(part["environment"].nunique())
    n_cells = int(len(part))
    if n_env >= MIN_SUPPORT_GROUP_ENVIRONMENTS and n_cells >= MIN_SUPPORT_GROUP_CELLS:
        return CalibrationQuantile(
            finite_sample_quantile(part["absolute_error"], level),
            "SUPPORT_GROUP_CHRONOLOGICAL",
            n_cells,
            n_env,
        )
    return CalibrationQuantile(float(global_q), "GLOBAL_CHRONOLOGICAL_FALLBACK", n_cells, n_env)


def calibrate_forward_intervals(
    cell_table: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply strictly prior-year calibration to each frozen forward test year."""

    years = sorted(cell_table["test_year"].astype(int).unique().tolist())
    audit_rows: list[dict[str, object]] = []
    coverage_rows: list[dict[str, object]] = []
    evaluated_frames: list[pd.DataFrame] = []

    for test_year in years:
        prior = cell_table[cell_table["test_year"].astype(int) < int(test_year)].copy()
        calibration_years = sorted(prior["test_year"].astype(int).unique().tolist())
        current = cell_table[cell_table["test_year"].astype(int).eq(int(test_year))].copy()
        status = "CALIBRATION_AVAILABLE" if len(calibration_years) >= MIN_CALIBRATION_YEARS else INSUFFICIENT
        audit_rows.append(
            {
                "test_year": int(test_year),
                "status": status,
                "n_calibration_years": int(len(calibration_years)),
                "calibration_year_min": min(calibration_years) if calibration_years else np.nan,
                "calibration_year_max": max(calibration_years) if calibration_years else np.nan,
                "n_calibration_cells": int(len(prior)),
                "n_calibration_environments": int(prior["environment"].nunique()) if len(prior) else 0,
                "test_year_used_for_calibration": False,
                "future_year_used_for_calibration": False,
                "min_calibration_years": MIN_CALIBRATION_YEARS,
                "support_boundary_uses_outcome": False,
                "post_result_tuning_permitted": False,
            }
        )
        if status == INSUFFICIENT:
            for level in NOMINAL_LEVELS:
                coverage_rows.append(
                    {
                        "test_year": int(test_year),
                        "nominal": float(level),
                        "status": status,
                        "n": int(len(current)),
                        "n_environments": int(current["environment"].nunique()),
                        "global_half_width": np.nan,
                        "global_coverage": np.nan,
                        "adaptive_mean_half_width": np.nan,
                        "adaptive_coverage": np.nan,
                        "adaptive_environment_balanced_coverage": np.nan,
                    }
                )
            continue

        eval_current = current.copy()
        eval_current["reliability_state"] = eval_current["support_group"].map(
            lambda g: reliability_state(len(calibration_years), str(g))
        )
        for level in NOMINAL_LEVELS:
            global_q = finite_sample_quantile(prior["absolute_error"], level)
            q_by_group = {
                group: _adaptive_quantile(prior, group, level, global_q)
                for group in (SUPPORT_WITHIN, SUPPORT_EDGE)
            }
            adaptive_q = eval_current["support_group"].map(lambda g: q_by_group[str(g)].value).astype(float)
            global_covered = eval_current["absolute_error"].to_numpy(float) <= global_q
            adaptive_covered = eval_current["absolute_error"].to_numpy(float) <= adaptive_q.to_numpy(float)
            key = int(round(level * 100))
            eval_current[f"global_half_width_{key}"] = float(global_q)
            eval_current[f"adaptive_half_width_{key}"] = adaptive_q
            eval_current[f"global_covered_{key}"] = global_covered
            eval_current[f"adaptive_covered_{key}"] = adaptive_covered
            env_cov = (
                pd.DataFrame(
                    {
                        "environment": eval_current["environment"].astype(str),
                        "covered": adaptive_covered.astype(float),
                    }
                )
                .groupby("environment")["covered"]
                .mean()
            )
            coverage_rows.append(
                {
                    "test_year": int(test_year),
                    "nominal": float(level),
                    "status": status,
                    "n": int(len(eval_current)),
                    "n_environments": int(eval_current["environment"].nunique()),
                    "global_half_width": float(global_q),
                    "global_coverage": float(np.mean(global_covered)),
                    "adaptive_mean_half_width": float(adaptive_q.mean()),
                    "adaptive_coverage": float(np.mean(adaptive_covered)),
                    "adaptive_environment_balanced_coverage": float(env_cov.mean()),
                    "within_group_quantile_source": q_by_group[SUPPORT_WITHIN].source,
                    "edge_group_quantile_source": q_by_group[SUPPORT_EDGE].source,
                    "within_group_calibration_environments": q_by_group[SUPPORT_WITHIN].n_environments,
                    "edge_group_calibration_environments": q_by_group[SUPPORT_EDGE].n_environments,
                }
            )
        evaluated_frames.append(eval_current)

    evaluated = pd.concat(evaluated_frames, ignore_index=True) if evaluated_frames else pd.DataFrame()
    return pd.DataFrame(audit_rows), pd.DataFrame(coverage_rows), evaluated


def _cluster_coverage_ci(frame: pd.DataFrame, covered_col: str, reps: int = BOOTSTRAP_REPS) -> tuple[float, float]:
    stats = (
        frame.assign(_covered=frame[covered_col].astype(float))
        .groupby("environment")
        .agg(covered=("_covered", "sum"), n=("_covered", "size"))
    )
    labels = np.asarray(stats.index.astype(str))
    if len(labels) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(SEED + sum(ord(c) for c in covered_col))
    boots = np.empty(reps, dtype=float)
    for i in range(reps):
        sample = rng.choice(labels, size=len(labels), replace=True)
        chosen = stats.loc[sample]
        boots[i] = float(chosen["covered"].sum() / chosen["n"].sum())
    return float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


def pooled_coverage_summary(evaluated: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for level in NOMINAL_LEVELS:
        key = int(round(level * 100))
        for method, covered_col, width_col in (
            ("GLOBAL_FORWARD", f"global_covered_{key}", f"global_half_width_{key}"),
            ("SUPPORT_ADAPTIVE", f"adaptive_covered_{key}", f"adaptive_half_width_{key}"),
        ):
            coverage = float(evaluated[covered_col].astype(float).mean())
            ci_low, ci_high = _cluster_coverage_ci(evaluated, covered_col)
            env_cov = evaluated.groupby("environment")[covered_col].mean()
            rows.append(
                {
                    "method": method,
                    "nominal": float(level),
                    "n": int(len(evaluated)),
                    "n_environments": int(evaluated["environment"].nunique()),
                    "n_test_years": int(evaluated["test_year"].nunique()),
                    "empirical_coverage": coverage,
                    "environment_balanced_coverage": float(env_cov.mean()),
                    "environment_cluster_ci95_low": ci_low,
                    "environment_cluster_ci95_high": ci_high,
                    "mean_interval_width": float(2.0 * evaluated[width_col].astype(float).mean()),
                    "absolute_coverage_gap": abs(coverage - float(level)),
                }
            )
    return pd.DataFrame(rows)


def support_conditioned_coverage(evaluated: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (group, state), part in evaluated.groupby(["support_group", "reliability_state"]):
        for level in NOMINAL_LEVELS:
            key = int(round(level * 100))
            rows.append(
                {
                    "support_group": str(group),
                    "reliability_state": str(state),
                    "nominal": float(level),
                    "n": int(len(part)),
                    "n_environments": int(part["environment"].nunique()),
                    "adaptive_coverage": float(part[f"adaptive_covered_{key}"].astype(float).mean()),
                    "adaptive_mean_interval_width": float(2.0 * part[f"adaptive_half_width_{key}"].astype(float).mean()),
                    "rmse": metrics(part["observed"], part["predicted"])["rmse"],
                    "mae": metrics(part["observed"], part["predicted"])["mae"],
                }
            )
    return pd.DataFrame(rows)


def reliability_summary(evaluated: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    groups: list[tuple[str, pd.DataFrame]] = [("ALL_EVALUATED", evaluated)]
    groups.extend((str(name), part) for name, part in evaluated.groupby("reliability_state"))
    for name, part in groups:
        m = metrics(part["observed"], part["predicted"])
        rows.append(
            {
                "state": name,
                "n": int(len(part)),
                "n_environments": int(part["environment"].nunique()),
                "n_test_years": int(part["test_year"].nunique()),
                "rmse": m["rmse"],
                "mae": m["mae"],
                "r2": m["r2"],
                "correlation": m["correlation"],
                "adaptive_90_coverage": float(part["adaptive_covered_90"].astype(float).mean()),
                "adaptive_90_mean_width": float(2.0 * part["adaptive_half_width_90"].astype(float).mean()),
            }
        )
    return pd.DataFrame(rows)


def selective_risk(evaluated: pd.DataFrame) -> pd.DataFrame:
    """Outcome-free support ranking; diagnostic only, no threshold promotion."""

    env = (
        evaluated[["test_year", "environment", "full_nearest_percentile"]]
        .drop_duplicates(["test_year", "environment"])
        .copy()
    )
    rows: list[dict[str, object]] = []
    for retention in SELECTIVE_RETENTION:
        kept_keys: set[tuple[int, str]] = set()
        for year, part in env.groupby("test_year"):
            part = part.sort_values(["full_nearest_percentile", "environment"], kind="mergesort")
            keep_n = max(1, int(np.ceil(float(retention) * len(part))))
            kept_keys.update((int(year), str(v)) for v in part.iloc[:keep_n]["environment"])
        mask = [
            (int(y), str(e)) in kept_keys
            for y, e in zip(evaluated["test_year"], evaluated["environment"])
        ]
        kept = evaluated.loc[mask].copy()
        m = metrics(kept["observed"], kept["predicted"])
        rows.append(
            {
                "target_environment_retention": float(retention),
                "realized_cell_retention": float(len(kept) / len(evaluated)),
                "n": int(len(kept)),
                "n_environment_years": int(kept[["test_year", "environment"]].drop_duplicates().shape[0]),
                "rmse": m["rmse"],
                "mae": m["mae"],
                "adaptive_90_coverage": float(kept["adaptive_covered_90"].astype(float).mean()),
                "selection_uses_outcome": False,
                "diagnostic_only_no_threshold_selection": True,
            }
        )
    return pd.DataFrame(rows)


def support_error_association(evaluated: pd.DataFrame) -> pd.DataFrame:
    """Environment-level descriptive association of uncertainty/support with error."""

    agg = (
        evaluated.groupby(["test_year", "environment"], as_index=False)
        .agg(
            observed_n=("observed", "size"),
            mse=("absolute_error", lambda x: float(np.mean(np.square(x)))),
            mae=("absolute_error", "mean"),
            full_nearest_percentile=("full_nearest_percentile", "first"),
            full_max_training_kernel_similarity=("full_max_training_kernel_similarity", "first"),
            weather_nearest_percentile=("weather_nearest_percentile", "first"),
            nearest_training_location_km=("nearest_training_location_km", "first"),
            adaptive_half_width_90=("adaptive_half_width_90", "first"),
            global_half_width_90=("global_half_width_90", "first"),
        )
    )
    agg["rmse"] = np.sqrt(agg["mse"])
    rows: list[dict[str, object]] = []
    for signal in (
        "adaptive_half_width_90",
        "global_half_width_90",
        "full_nearest_percentile",
        "full_max_training_kernel_similarity",
        "weather_nearest_percentile",
        "nearest_training_location_km",
    ):
        x = agg[signal].to_numpy(float)
        y = agg["rmse"].to_numpy(float)
        if np.std(x) == 0.0 or np.std(y) == 0.0:
            rho, p = np.nan, np.nan
        else:
            result = spearmanr(x, y)
            rho, p = float(result.statistic), float(result.pvalue)
        rows.append(
            {
                "signal": signal,
                "n_environment_years": int(len(agg)),
                "spearman_rho_with_environment_rmse": rho,
                "descriptive_p_value": p,
                "outcome_free_at_issuance": signal not in {"adaptive_half_width_90", "global_half_width_90"},
                "interpretation": "descriptive_not_causal",
            }
        )
    return pd.DataFrame(rows)


def branch_decision(
    pooled: pd.DataFrame,
    reliability: pd.DataFrame,
) -> pd.DataFrame:
    adaptive90 = pooled[(pooled["method"].eq("SUPPORT_ADAPTIVE")) & np.isclose(pooled["nominal"], 0.90)].iloc[0]
    global90 = pooled[(pooled["method"].eq("GLOBAL_FORWARD")) & np.isclose(pooled["nominal"], 0.90)].iloc[0]
    all_row = reliability[reliability["state"].eq("ALL_EVALUATED")].iloc[0]
    retained = reliability[reliability["state"].eq(RETAIN)]
    abstained = reliability[reliability["state"].eq(ABSTAIN)]
    retained_rmse = float(retained["rmse"].iloc[0]) if len(retained) else np.nan
    abstained_rmse = float(abstained["rmse"].iloc[0]) if len(abstained) else np.nan
    abstained_envs = int(abstained["n_environments"].iloc[0]) if len(abstained) else 0
    interval_supported = bool(
        float(adaptive90["environment_cluster_ci95_low"]) <= 0.90 <= float(adaptive90["environment_cluster_ci95_high"])
        and abs(float(adaptive90["empirical_coverage"]) - 0.90) <= 0.03
    )
    support_abstention_supported = bool(
        abstained_envs >= MIN_SUPPORT_GROUP_ENVIRONMENTS
        and np.isfinite(retained_rmse)
        and np.isfinite(abstained_rmse)
        and retained_rmse < float(all_row["rmse"])
        and abstained_rmse > retained_rmse
    )
    if interval_supported and support_abstention_supported:
        decision = "ADMIT_FORWARD_INTERVALS_WITH_OUTCOME_FREE_SUPPORT_ABSTENTION"
    elif interval_supported:
        decision = "ADMIT_FORWARD_INTERVALS_KEEP_SUPPORT_ABSTENTION_DIAGNOSTIC"
    else:
        decision = "DO_NOT_ADMIT_FORWARD_UNCERTAINTY_LAYER"
    return pd.DataFrame(
        [
            {
                "supported_predictor": MODEL,
                "evaluated_horizon": HORIZON,
                "n_evaluated_years": int(adaptive90["n_test_years"]),
                "adaptive_90_coverage": float(adaptive90["empirical_coverage"]),
                "adaptive_90_env_ci_low": float(adaptive90["environment_cluster_ci95_low"]),
                "adaptive_90_env_ci_high": float(adaptive90["environment_cluster_ci95_high"]),
                "global_90_coverage": float(global90["empirical_coverage"]),
                "interval_calibration_supported": interval_supported,
                "all_rmse": float(all_row["rmse"]),
                "retained_rmse": retained_rmse,
                "abstained_rmse": abstained_rmse,
                "abstained_environments": abstained_envs,
                "support_abstention_supported": support_abstention_supported,
                "branch_decision": decision,
                "t2_branch_reopened": False,
                "predictive_model_refit_or_tuned_in_b11": False,
                "post_result_tuning_permitted": False,
            }
        ]
    )


def make_coverage_figure(pooled: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.8))
    for method in ("GLOBAL_FORWARD", "SUPPORT_ADAPTIVE"):
        part = pooled[pooled["method"].eq(method)].sort_values("nominal")
        ax.plot(part["nominal"], part["empirical_coverage"], marker="o", linewidth=2.2, label=method.replace("_", " ").title())
        ax.fill_between(
            part["nominal"].to_numpy(float),
            part["environment_cluster_ci95_low"].to_numpy(float),
            part["environment_cluster_ci95_high"].to_numpy(float),
            alpha=0.12,
        )
    x = np.asarray(NOMINAL_LEVELS, dtype=float)
    ax.plot(x, x, linestyle="--", linewidth=1.4, label="Nominal coverage")
    ax.set_xlabel("Nominal coverage")
    ax.set_ylabel("Forward empirical coverage")
    ax.set_title("Case Study B11 — strictly forward-time T1 interval calibration")
    ax.set_xticks(list(NOMINAL_LEVELS))
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
    fig.subplots_adjust(bottom=0.25)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_selective_figure(selective: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.8, 6.8))
    part = selective.sort_values("realized_cell_retention")
    ax.plot(part["realized_cell_retention"], part["rmse"], marker="o", linewidth=2.2, label="T1 RMSE")
    ax.set_xlabel("Realized cell retention")
    ax.set_ylabel("RMSE")
    ax.set_title("Case Study B11 — outcome-free environmental-support selective risk")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, frameon=False)
    fig.subplots_adjust(bottom=0.25)
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

    predictions = build_forward_t1_predictions(root, states, env_manifest, forward)
    support = build_t1_support_table(states, env_manifest, forward)
    cells = predictions.merge(
        support,
        on=["environment", "test_year", "train_year_max"],
        how="left",
        validate="many_to_one",
    )
    if cells["support_group"].isna().any():
        raise ValueError("B11 could not align T1 predictions with outcome-free support diagnostics.")

    audit, by_year, evaluated = calibrate_forward_intervals(cells)
    if evaluated.empty:
        raise ValueError("B11 produced no years with sufficient calibration history.")
    pooled = pooled_coverage_summary(evaluated)
    conditioned = support_conditioned_coverage(evaluated)
    reliability = reliability_summary(evaluated)
    selective = selective_risk(evaluated)
    association = support_error_association(evaluated)
    decision = branch_decision(pooled, reliability)

    # Frozen B10 T1 reproduction audit.
    b10 = pd.read_csv(results / "case_study_b10_forward_year_metrics.csv")
    b10 = b10[b10["model"].eq(MODEL)][["test_year", "rmse"]].rename(columns={"rmse": "b10_t1_rmse"})
    reproduced_rows = []
    for year, part in predictions.groupby("test_year"):
        rmse = metrics(part["observed"], part["predicted"])["rmse"]
        reference = float(b10.loc[b10["test_year"].astype(int).eq(int(year)), "b10_t1_rmse"].iloc[0])
        reproduced_rows.append(
            {
                "test_year": int(year),
                "b11_reproduced_t1_rmse": rmse,
                "b10_t1_rmse": reference,
                "absolute_difference": abs(rmse - reference),
                "within_tolerance_1e-8": abs(rmse - reference) <= 1e-8,
            }
        )
    reproduction = pd.DataFrame(reproduced_rows)
    if len(reproduction) != 6 or not reproduction["within_tolerance_1e-8"].all():
        raise ValueError("B11 failed to reproduce the frozen B10 T1 predictor.")

    paths = {
        "calibration_audit": results / "case_study_b11_calibration_audit.csv",
        "coverage_by_year": results / "case_study_b11_coverage_by_year.csv",
        "coverage_summary": results / "case_study_b11_coverage_summary.csv",
        "support_conditioned": results / "case_study_b11_support_conditioned_coverage.csv",
        "reliability": results / "case_study_b11_reliability_summary.csv",
        "selective_risk": results / "case_study_b11_selective_risk.csv",
        "support_association": results / "case_study_b11_support_error_association.csv",
        "decision": results / "case_study_b11_branch_decision.csv",
        "reproduction": results / "case_study_b11_b10_t1_reproduction_audit.csv",
        "coverage_figure": figures / "case_study_b11_forward_coverage.png",
        "selective_figure": figures / "case_study_b11_selective_risk.png",
    }
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    audit.to_csv(paths["calibration_audit"], index=False)
    by_year.to_csv(paths["coverage_by_year"], index=False)
    pooled.to_csv(paths["coverage_summary"], index=False)
    conditioned.to_csv(paths["support_conditioned"], index=False)
    reliability.to_csv(paths["reliability"], index=False)
    selective.to_csv(paths["selective_risk"], index=False)
    association.to_csv(paths["support_association"], index=False)
    decision.to_csv(paths["decision"], index=False)
    reproduction.to_csv(paths["reproduction"], index=False)
    make_coverage_figure(pooled, paths["coverage_figure"])
    make_selective_figure(selective, paths["selective_figure"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Case Study B11 forward-time T1 uncertainty calibration.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B11 forward-time uncertainty calibration complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
