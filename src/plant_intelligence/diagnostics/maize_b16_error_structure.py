"""B16: retrospective error-structure diagnostic for the frozen G+E_T1 predictor.

This module does not fit or modify a predictor. It decomposes already-revealed
B14C residual error into an environment-wide mean-bias component and a
within-environment centered component, and summarizes within-environment
ordering. The oracle environment intercept is diagnostic only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

PRIMARY_REL = Path("reports/results/case_study_b14c_2024_primary_cohort.csv")
B12_REL = Path("reports/results/case_study_b12_2022_available_case_by_environment.csv")
LOCK_REL = Path("reports/results/case_study_b16_error_structure_lock.json")


@dataclass(frozen=True)
class DecompositionSummary:
    n_cells: int
    n_environments: int
    raw_sse: float
    environment_mean_bias_sse: float
    within_environment_centered_sse: float
    sse_identity_residual: float
    environment_bias_sse_fraction: float
    within_environment_sse_fraction: float
    raw_rmse: float
    raw_mae: float
    oracle_environment_intercept_corrected_rmse: float
    oracle_rmse_reduction_fraction: float
    mean_environment_pearson: float
    median_environment_pearson: float
    mean_environment_spearman: float
    median_environment_spearman: float
    median_predicted_to_observed_sd_ratio: float


def _safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) <= 0.0 or np.std(y) <= 0.0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _safe_spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) <= 0.0 or np.std(y) <= 0.0:
        return float("nan")
    return float(spearmanr(x, y).statistic)


def validate_primary(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "genotype",
        "environment",
        "predicted",
        "observed",
        "official_answer_key_present",
        "model",
        "horizon",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"B16 primary cohort missing columns: {missing}")
    out = frame.copy()
    if len(out) != 779:
        raise ValueError(f"B16 expects the frozen B14C primary cohort of 779 rows, found {len(out)}")
    if out.duplicated(["genotype", "environment"]).any():
        raise ValueError("B16 refuses duplicate B14C primary keys.")
    present = out["official_answer_key_present"].astype(str).str.lower().map({"true": True, "false": False})
    if present.isna().any() or not bool(present.all()):
        raise ValueError("B16 primary cohort must contain only officially observable sealed keys.")
    out["predicted"] = pd.to_numeric(out["predicted"], errors="coerce")
    out["observed"] = pd.to_numeric(out["observed"], errors="coerce")
    if out[["predicted", "observed"]].isna().any().any():
        raise ValueError("B16 refuses missing/non-numeric prediction or observed values.")
    if not out["model"].eq("G+E_T1").all() or not out["horizon"].eq("T1_30DAP").all():
        raise ValueError("B16 primary cohort is not the frozen G+E_T1/T1_30DAP object.")
    return out


def decompose(frame: pd.DataFrame) -> tuple[pd.DataFrame, DecompositionSummary]:
    data = frame.copy()
    data["residual"] = data["observed"] - data["predicted"]
    rows: list[dict[str, float | int | str]] = []
    for environment, part in data.groupby("environment", sort=True):
        y = part["observed"].to_numpy(float)
        p = part["predicted"].to_numpy(float)
        r = y - p
        mean_residual = float(np.mean(r))
        centered = r - mean_residual
        obs_sd = float(np.std(y, ddof=1)) if len(y) > 1 else float("nan")
        pred_sd = float(np.std(p, ddof=1)) if len(p) > 1 else float("nan")
        sd_ratio = pred_sd / obs_sd if np.isfinite(obs_sd) and obs_sd > 0.0 else float("nan")
        rows.append(
            {
                "environment": str(environment),
                "n": int(len(part)),
                "raw_rmse": float(np.sqrt(np.mean(np.square(r)))),
                "raw_mae": float(np.mean(np.abs(r))),
                "mean_residual_observed_minus_predicted": mean_residual,
                "environment_mean_bias_sse": float(len(part) * mean_residual**2),
                "within_environment_centered_sse": float(np.sum(np.square(centered))),
                "centered_rmse_after_oracle_intercept": float(np.sqrt(np.mean(np.square(centered)))),
                "pearson": _safe_corr(p, y),
                "spearman": _safe_spearman(p, y),
                "observed_sd": obs_sd,
                "predicted_sd": pred_sd,
                "predicted_to_observed_sd_ratio": float(sd_ratio),
                "oracle_intercept_uses_target_outcome": True,
                "diagnostic_only": True,
            }
        )
    env = pd.DataFrame(rows)
    residual = data["residual"].to_numpy(float)
    raw_sse = float(np.sum(np.square(residual)))
    between = float(env["environment_mean_bias_sse"].sum())
    within = float(env["within_environment_centered_sse"].sum())
    identity = float(raw_sse - between - within)
    if abs(identity) > max(1e-8, 1e-10 * max(raw_sse, 1.0)):
        raise AssertionError(f"B16 SSE identity failed: residual={identity}")
    n = len(data)
    raw_rmse = float(np.sqrt(raw_sse / n))
    oracle_rmse = float(np.sqrt(within / n))
    if oracle_rmse > raw_rmse + 1e-12:
        raise AssertionError("Removing retrospective environment means cannot increase SSE.")
    pearson = env["pearson"].dropna()
    spearman = env["spearman"].dropna()
    ratios = env["predicted_to_observed_sd_ratio"].replace([np.inf, -np.inf], np.nan).dropna()
    summary = DecompositionSummary(
        n_cells=int(n),
        n_environments=int(env["environment"].nunique()),
        raw_sse=raw_sse,
        environment_mean_bias_sse=between,
        within_environment_centered_sse=within,
        sse_identity_residual=identity,
        environment_bias_sse_fraction=float(between / raw_sse),
        within_environment_sse_fraction=float(within / raw_sse),
        raw_rmse=raw_rmse,
        raw_mae=float(np.mean(np.abs(residual))),
        oracle_environment_intercept_corrected_rmse=oracle_rmse,
        oracle_rmse_reduction_fraction=float(1.0 - oracle_rmse / raw_rmse),
        mean_environment_pearson=float(pearson.mean()),
        median_environment_pearson=float(pearson.median()),
        mean_environment_spearman=float(spearman.mean()),
        median_environment_spearman=float(spearman.median()),
        median_predicted_to_observed_sd_ratio=float(ratios.median()),
    )
    return env, summary


def b12_reference(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"environment", "rmse", "r2", "correlation", "diagnostic_only", "selection_uses_outcome_value"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"B12 reference missing columns: {missing}")
    corr = pd.to_numeric(frame["correlation"], errors="coerce")
    r2 = pd.to_numeric(frame["r2"], errors="coerce")
    rmse = pd.to_numeric(frame["rmse"], errors="coerce")
    return pd.DataFrame(
        [
            {
                "source_stage": "B12_2022_AVAILABLE_CASE_DIAGNOSTIC",
                "n_environments": int(len(frame)),
                "median_within_environment_pearson": float(corr.median()),
                "mean_within_environment_pearson": float(corr.mean()),
                "fraction_environments_negative_r2": float((r2 < 0.0).mean()),
                "median_environment_rmse": float(rmse.median()),
                "confirmatory": False,
                "used_to_fit_or_tune_b16": False,
            }
        ]
    )


def run(output_root: Path) -> dict[str, Path]:
    root = Path(output_root)
    lock_path = root / LOCK_REL
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock["status"] != "LOCKED_BEFORE_DECOMPOSITION_EXECUTION":
        raise ValueError("B16 protocol lock is missing or altered.")
    if lock["new_outcome_season_access_permitted"] or lock["new_external_outcome_acquisition_permitted"]:
        raise ValueError("B16 refuses a lock that permits new outcome access.")
    primary = validate_primary(pd.read_csv(root / PRIMARY_REL))
    env, summary = decompose(primary)
    historical = b12_reference(pd.read_csv(root / B12_REL))

    results = root / "reports" / "results"
    env_path = results / "case_study_b16_2024_environment_error_structure.csv"
    summary_path = results / "case_study_b16_2024_error_structure_summary.csv"
    historical_path = results / "case_study_b16_2022_reference_summary.csv"
    decision_path = results / "case_study_b16_decision.csv"
    env.to_csv(env_path, index=False)
    pd.DataFrame([asdict(summary)]).to_csv(summary_path, index=False)
    historical.to_csv(historical_path, index=False)
    pd.DataFrame(
        [
            {
                "stage": "B16_ERROR_STRUCTURE_DIAGNOSTIC",
                "decision": "B16_DIAGNOSTIC_COMPLETE_NO_MODEL_CHANGE",
                "n_2024_cells": summary.n_cells,
                "n_2024_environments": summary.n_environments,
                "new_outcome_access": False,
                "new_prediction_generation": False,
                "point_predictor_changed": False,
                "oracle_intercept_promoted": False,
                "posthoc_dominance_threshold_used": False,
                "method_novelty_claim": False,
                "t2_reopened": False,
                "post_result_tuning_permitted": False,
            }
        ]
    ).to_csv(decision_path, index=False)
    return {
        "environment": env_path,
        "summary": summary_path,
        "historical": historical_path,
        "decision": decision_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    for name, path in paths.items():
        print(f"{name}: {path}")
    print(pd.read_csv(paths["summary"]).to_string(index=False))
    print(pd.read_csv(paths["historical"]).to_string(index=False))


if __name__ == "__main__":
    main()
