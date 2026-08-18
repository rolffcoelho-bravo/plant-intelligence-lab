"""B17: forecast-time GxE response-amplitude transport audit.

B17 is outcome-closed. It uses only the already-revealed B14C primary cohort
and the already-published B16 summary. It does not fit, rescale, recalibrate or
change the frozen predictor. The module places the B16 under-dispersion result
into established within-environment difference/dispersion quantities and
encodes a simple non-identification witness for forecast-time target amplitude.
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
B16_SUMMARY_REL = Path("reports/results/case_study_b16_2024_error_structure_summary.csv")
LOCK_REL = Path("reports/results/case_study_b17_response_amplitude_transport_lock.json")
DECISION = "B17_BROAD_RESPONSE_AMPLITUDE_NOVELTY_REJECTED_OPEN_ARCHITECTURE_CONTRACTION_TEST"


@dataclass(frozen=True)
class ResponseAmplitudeSummary:
    n_cells: int
    n_environments: int
    mean_environment_pearson: float
    median_environment_pearson: float
    mean_environment_spearman: float
    median_environment_spearman: float
    mean_predicted_to_observed_sd_ratio: float
    median_predicted_to_observed_sd_ratio: float
    mean_observed_on_predicted_slope: float
    median_observed_on_predicted_slope: float
    mean_root_pairwise_msed: float
    median_root_pairwise_msed: float
    median_slope_identity_residual: float


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
        raise KeyError(f"B17 primary cohort missing columns: {missing}")
    out = frame.copy()
    if len(out) != 779:
        raise ValueError(f"B17 expects the frozen B14C primary cohort of 779 rows, found {len(out)}")
    if out.duplicated(["genotype", "environment"]).any():
        raise ValueError("B17 refuses duplicate B14C primary keys.")
    present = out["official_answer_key_present"].astype(str).str.lower().map({"true": True, "false": False})
    if present.isna().any() or not bool(present.all()):
        raise ValueError("B17 primary cohort must contain only officially observable sealed keys.")
    out["predicted"] = pd.to_numeric(out["predicted"], errors="coerce")
    out["observed"] = pd.to_numeric(out["observed"], errors="coerce")
    if out[["predicted", "observed"]].isna().any().any():
        raise ValueError("B17 refuses missing/non-numeric prediction or observed values.")
    if not out["model"].eq("G+E_T1").all() or not out["horizon"].eq("T1_30DAP").all():
        raise ValueError("B17 primary cohort is not the frozen G+E_T1/T1_30DAP object.")
    return out


def pairwise_msed_from_residuals(residual: np.ndarray) -> float:
    """Average ordered-pair squared error of within-environment differences.

    If f_i = y_i - z_i, then
    mean_{i != j}(f_i-f_j)^2 = 2/(n-1) * sum_i(f_i-f_bar)^2.
    """
    residual = np.asarray(residual, dtype=float)
    n = len(residual)
    if n < 2:
        return float("nan")
    centered = residual - float(np.mean(residual))
    return float(2.0 * np.sum(np.square(centered)) / (n - 1))


def direct_pairwise_msed(residual: np.ndarray) -> float:
    """Small-sample reference implementation used by tests."""
    residual = np.asarray(residual, dtype=float)
    n = len(residual)
    if n < 2:
        return float("nan")
    diffs = residual[:, None] - residual[None, :]
    mask = ~np.eye(n, dtype=bool)
    return float(np.mean(np.square(diffs[mask])))


def environment_response_amplitude(frame: pd.DataFrame) -> tuple[pd.DataFrame, ResponseAmplitudeSummary]:
    rows: list[dict[str, float | int | str | bool]] = []
    for environment, part in frame.groupby("environment", sort=True):
        y = part["observed"].to_numpy(float)
        p = part["predicted"].to_numpy(float)
        n = len(part)
        yc = y - float(np.mean(y))
        pc = p - float(np.mean(p))
        residual = y - p
        obs_sd = float(np.std(y, ddof=1)) if n > 1 else float("nan")
        pred_sd = float(np.std(p, ddof=1)) if n > 1 else float("nan")
        pearson = _safe_corr(p, y)
        spearman = _safe_spearman(p, y)
        sd_ratio = pred_sd / obs_sd if np.isfinite(obs_sd) and obs_sd > 0.0 else float("nan")
        denom = float(np.dot(pc, pc))
        slope = float(np.dot(pc, yc) / denom) if denom > 0.0 else float("nan")
        slope_from_corr_scale = (
            float(pearson * obs_sd / pred_sd)
            if np.isfinite(pearson) and np.isfinite(pred_sd) and pred_sd > 0.0
            else float("nan")
        )
        slope_residual = slope - slope_from_corr_scale if np.isfinite(slope_from_corr_scale) else float("nan")
        msed = pairwise_msed_from_residuals(residual)
        rows.append(
            {
                "environment": str(environment),
                "n": int(n),
                "pearson": pearson,
                "spearman": spearman,
                "observed_sd": obs_sd,
                "predicted_sd": pred_sd,
                "predicted_to_observed_sd_ratio": float(sd_ratio),
                "observed_on_predicted_slope": slope,
                "slope_from_correlation_and_scale": slope_from_corr_scale,
                "slope_identity_residual": slope_residual,
                "pairwise_msed": msed,
                "root_pairwise_msed": float(np.sqrt(msed)) if np.isfinite(msed) and msed >= 0.0 else float("nan"),
                "uses_already_revealed_target_outcome": True,
                "diagnostic_only": True,
            }
        )
    env = pd.DataFrame(rows)
    summary = ResponseAmplitudeSummary(
        n_cells=int(len(frame)),
        n_environments=int(env["environment"].nunique()),
        mean_environment_pearson=float(env["pearson"].mean()),
        median_environment_pearson=float(env["pearson"].median()),
        mean_environment_spearman=float(env["spearman"].mean()),
        median_environment_spearman=float(env["spearman"].median()),
        mean_predicted_to_observed_sd_ratio=float(env["predicted_to_observed_sd_ratio"].mean()),
        median_predicted_to_observed_sd_ratio=float(env["predicted_to_observed_sd_ratio"].median()),
        mean_observed_on_predicted_slope=float(env["observed_on_predicted_slope"].mean()),
        median_observed_on_predicted_slope=float(env["observed_on_predicted_slope"].median()),
        mean_root_pairwise_msed=float(env["root_pairwise_msed"].mean()),
        median_root_pairwise_msed=float(env["root_pairwise_msed"].median()),
        median_slope_identity_residual=float(env["slope_identity_residual"].abs().median()),
    )
    return env, summary


def amplitude_nonidentification_witness(predicted: np.ndarray) -> pd.DataFrame:
    """Two outcome worlds with identical forecast information and predictions.

    The witness is deliberately elementary: before target outcomes are observed,
    the same prediction vector is compatible with distinct centered target
    amplitudes. Therefore target response amplitude is not distribution-free
    point identified from the prediction/pre-outcome state alone.
    """
    p = np.asarray(predicted, dtype=float)
    pc = p - float(np.mean(p))
    if len(p) < 3 or np.std(pc) <= 0.0:
        raise ValueError("B17 witness requires a nonconstant prediction vector with at least three values.")
    rows = []
    for world, target_scale in (("WORLD_A", 0.5), ("WORLD_B", 2.0)):
        y = 10.0 + target_scale * pc
        pred_sd = float(np.std(p, ddof=1))
        obs_sd = float(np.std(y, ddof=1))
        rows.append(
            {
                "world": world,
                "same_preoutcome_information": True,
                "same_prediction_vector": True,
                "target_scale_relative_to_centered_prediction": target_scale,
                "predicted_to_observed_sd_ratio": pred_sd / obs_sd,
                "forecast_time_target_amplitude_point_identified": False,
            }
        )
    return pd.DataFrame(rows)


def run(output_root: Path) -> dict[str, Path]:
    root = Path(output_root)
    lock = json.loads((root / LOCK_REL).read_text(encoding="utf-8"))
    if lock["status"] != "LOCKED_BEFORE_RETROSPECTIVE_DECOMPOSITION_EXECUTION":
        raise ValueError("B17 protocol lock is missing or altered.")
    forbidden_true = [
        "new_outcome_season_access_permitted",
        "new_external_outcome_acquisition_permitted",
        "new_prediction_generation_permitted",
        "point_predictor_refit_permitted",
        "response_amplitude_rescaling_promotion_permitted",
        "interval_or_support_tuning_permitted",
        "b5_genomic_change_permitted",
        "t1_clock_change_permitted",
        "t2_reopen_permitted",
        "reseal_permitted",
        "post_result_tuning_permitted",
        "method_novelty_claim_permitted",
    ]
    if any(bool(lock[name]) for name in forbidden_true):
        raise ValueError("B17 lock permits a forbidden operation.")
    if lock["predeclared_broad_novelty_decision"] != DECISION:
        raise ValueError("B17 broad novelty decision was altered after lock.")

    primary = validate_primary(pd.read_csv(root / PRIMARY_REL))
    env, summary = environment_response_amplitude(primary)
    b16 = pd.read_csv(root / B16_SUMMARY_REL).iloc[0]
    if not np.isclose(
        summary.median_predicted_to_observed_sd_ratio,
        float(b16["median_predicted_to_observed_sd_ratio"]),
        atol=1e-12,
        rtol=0.0,
    ):
        raise AssertionError("B17 response-amplitude ratio does not reproduce B16.")
    if not np.isclose(summary.median_environment_pearson, float(b16["median_environment_pearson"]), atol=1e-12, rtol=0.0):
        raise AssertionError("B17 median environment Pearson does not reproduce B16.")

    first_env = env.iloc[0]["environment"]
    witness_prediction = primary.loc[primary["environment"].eq(first_env), "predicted"].to_numpy(float)
    witness = amplitude_nonidentification_witness(witness_prediction)

    results = root / "reports" / "results"
    env_path = results / "case_study_b17_2024_response_amplitude_by_environment.csv"
    summary_path = results / "case_study_b17_2024_response_amplitude_summary.csv"
    witness_path = results / "case_study_b17_nonidentification_witness.csv"
    decision_path = results / "case_study_b17_decision.csv"
    env.to_csv(env_path, index=False)
    pd.DataFrame([asdict(summary)]).to_csv(summary_path, index=False)
    witness.to_csv(witness_path, index=False)
    pd.DataFrame(
        [
            {
                "stage": "B17_RESPONSE_AMPLITUDE_TRANSPORT_AUDIT",
                "decision": DECISION,
                "broad_response_amplitude_method_novelty": False,
                "pairwise_difference_shrinkage_is_prior_art": True,
                "genomic_prediction_dispersion_is_prior_art": True,
                "reaction_norm_slope_transport_is_prior_art": True,
                "forecast_time_target_amplitude_distribution_free_point_identified": False,
                "new_outcome_access": False,
                "new_prediction_generation": False,
                "point_predictor_changed": False,
                "response_rescaling_promoted": False,
                "interval_or_support_tuning": False,
                "t2_reopened": False,
                "post_result_tuning_permitted": False,
                "next_stage": "B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_TEST",
            }
        ]
    ).to_csv(decision_path, index=False)
    return {
        "environment": env_path,
        "summary": summary_path,
        "witness": witness_path,
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
    print(pd.read_csv(paths["decision"]).to_string(index=False))


if __name__ == "__main__":
    main()
