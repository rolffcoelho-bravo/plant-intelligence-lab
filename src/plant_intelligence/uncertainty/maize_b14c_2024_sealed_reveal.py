"""Case Study B14C: seal-first 2024 external reveal and drift-guard test.

This module may read the official 2024 observed-values object only after the
B14C pre-reveal protocol has been committed. It verifies the immutable B14B
prediction seal before opening outcomes, evaluates the prospectively declared
OFFICIALLY_OBSERVABLE_SEALED_KEYS cohort, compares the two locked 90% interval
rules, and forbids post-result tuning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from plant_intelligence.uncertainty import maize_b13_forward_drift_calibration as b13
from plant_intelligence.uncertainty import maize_b14b_2024_sealed_prediction as b14b
from plant_intelligence.uncertainty import maize_forward_uncertainty as b11

TARGET_YEAR = 2024
EXPECTED_PREDICTION_SHA256 = "91c765ea994f557db1911865309bca94ebc2110b87a5fea483a03c879d1fb19d"
EXPECTED_CANDIDATE_SHA256 = "32e4f308522ee849e498d2bf0614f3ec349574a27bb327fefeb80e0f4e05bf7f"
EXPECTED_N_PREDICTIONS = 798
EXPECTED_N_GENOTYPES = 92
EXPECTED_N_ENVIRONMENTS = 19
EXPECTED_ADAPTIVE_LEVEL = 0.9512813317177465
# B14B wrote floating columns with 12 decimal places.  The JSON seal is the
# exact semantic authority; this tolerance verifies the immutable CSV's
# redundant level column at half a unit in its recorded serialization precision.
SEALED_CSV_ADAPTIVE_LEVEL_ATOL = 5e-13
CONTROL_LEVEL = 0.90
TARGET_COVERAGE = 0.90
MAX_COVERAGE_GAP = 0.03
PRIMARY_ESTIMAND = "OFFICIALLY_OBSERVABLE_SEALED_KEYS"
EXPECTED_OFFICIAL_COLUMNS = ("Env", "Hybrid", "Yield_Mg_ha")
CONTROL = b13.CONTROL
ADAPTIVE = b13.ADAPTIVE
NO_2023_FEEDBACK = "NO_2023_FEEDBACK_AVAILABLE_CARRY_FORWARD_2022_DRIFT_STATE"

DECISION_ADAPTIVE_PROMOTED = "B14C_ADAPTIVE_DRIFT_GUARD_PROMOTED"
DECISION_ADAPTIVE_INEFFICIENT = "B14C_ADAPTIVE_CALIBRATION_PASS_BUT_INEFFICIENT"
DECISION_KEEP_CONTROL = "B14C_BOTH_INTERVAL_RULES_PASS_KEEP_FROZEN_B11"
DECISION_BOTH_FAIL = "B14C_BOTH_INTERVAL_RULES_FAIL"
DECISION_DATA_ABORT = "B14C_PRIMARY_EVALUATION_ABORTED_DATA_INTEGRITY"
DECISION_SEAL_ABORT = "B14C_PRE_REVEAL_SEAL_MISMATCH"


class B14CIntegrityError(RuntimeError):
    """Raised when a predeclared B14C integrity gate fails."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _false(value: object) -> bool:
    return str(value).strip().lower() == "false"


def sealed_csv_adaptive_level_matches(values: object) -> bool:
    """Check the redundant B14B CSV level at its frozen 12-decimal precision."""

    array = np.asarray(values, dtype=float)
    return bool(
        np.all(np.isfinite(array))
        and np.allclose(
            array,
            EXPECTED_ADAPTIVE_LEVEL,
            rtol=0,
            atol=SEALED_CSV_ADAPTIVE_LEVEL_ATOL,
        )
    )


def verify_pre_reveal_lock(root: Path) -> dict[str, object]:
    results = root / "reports" / "results"
    marker = (results / ".b14c_protocol_locked").read_text(encoding="utf-8")
    required = (
        "B14C_2024_SEAL_FIRST_REVEAL_PROTOCOL_LOCKED",
        f"EXPECTED_B14B_PREDICTION_SHA256={EXPECTED_PREDICTION_SHA256}",
        f"EXPECTED_CANDIDATE_UNIVERSE_SHA256={EXPECTED_CANDIDATE_SHA256}",
        "PRIMARY_ESTIMAND=OFFICIALLY_OBSERVABLE_SEALED_KEYS",
        "COHORT_SELECTION=EXACT_OFFICIAL_KEY_PRESENCE_ONLY",
        "OUTCOME_VALUE_USED_FOR_SELECTION=false",
        "DUPLICATE_OFFICIAL_KEYS=ABORT",
        "PRESENT_KEY_MISSING_OR_NONNUMERIC_OUTCOME=ABORT",
        "POST_RESULT_TUNING=FORBIDDEN",
        "RESEAL=FORBIDDEN",
    )
    for token in required:
        if token not in marker:
            raise B14CIntegrityError(f"B14C protocol marker is missing {token!r}.")

    lock = json.loads((results / "case_study_b14c_pre_reveal_lock.json").read_text(encoding="utf-8"))
    checks = (
        lock.get("schema") == "plant-intelligence-lab/b14c-2024-pre-reveal-lock/v1",
        int(lock.get("target_year", -1)) == TARGET_YEAR,
        lock.get("primary_estimand") == PRIMARY_ESTIMAND,
        lock.get("cohort_selection") == "EXACT_OFFICIAL_KEY_PRESENCE_ONLY",
        lock.get("expected_prediction_sha256") == EXPECTED_PREDICTION_SHA256,
        lock.get("candidate_universe_sha256") == EXPECTED_CANDIDATE_SHA256,
        int(lock.get("expected_n_predictions", -1)) == EXPECTED_N_PREDICTIONS,
        bool(lock.get("outcome_value_used_for_selection", True)) is False,
        bool(lock.get("post_result_tuning_permitted", True)) is False,
        bool(lock.get("reseal_permitted", True)) is False,
        np.isclose(float(lock.get("adaptive_quantile_level")), EXPECTED_ADAPTIVE_LEVEL, rtol=0, atol=1e-15),
    )
    if not all(checks):
        raise B14CIntegrityError("Machine-readable B14C pre-reveal lock changed.")
    return lock


def verify_b14b_before_outcome(root: Path) -> pd.DataFrame:
    """Verify the immutable B14B artifact before the outcome file is opened."""

    results = root / "reports" / "results"
    pred_path = results / "case_study_b14b_2024_sealed_predictions.csv"
    seal_path = results / "case_study_b14b_2024_prediction_seal.json"
    decision_path = results / "case_study_b14b_2024_seal_decision.csv"

    seal = b14b.verify_seal(pred_path, seal_path)
    decision = pd.read_csv(decision_path)
    if len(decision) != 1:
        raise B14CIntegrityError("B14C requires exactly one B14B decision row.")
    row = decision.iloc[0]
    checks = (
        str(row["decision"]) == b14b.SEALED_DECISION,
        str(row["prediction_sha256"]) == EXPECTED_PREDICTION_SHA256,
        str(row["candidate_universe_sha256"]) == EXPECTED_CANDIDATE_SHA256,
        int(row["n_predictions"]) == EXPECTED_N_PREDICTIONS,
        int(row["n_genotypes"]) == EXPECTED_N_GENOTYPES,
        int(row["n_environments"]) == EXPECTED_N_ENVIRONMENTS,
        _false(row["observed_values_accessed"]),
        _false(row["point_predictor_changed"]),
        _false(row["b5_genotype_representation_changed"]),
        _false(row["t1_clock_changed"]),
        _false(row["t2_branch_reopened"]),
        _false(row["post_result_tuning_permitted"]),
        seal.get("prediction_sha256") == EXPECTED_PREDICTION_SHA256,
        seal.get("candidate_universe_sha256") == EXPECTED_CANDIDATE_SHA256,
        seal.get("calibration_feedback_state") == NO_2023_FEEDBACK,
        np.isclose(float(seal.get("adaptive_quantile_level")), EXPECTED_ADAPTIVE_LEVEL, rtol=0, atol=1e-15),
        bool(seal.get("prediction_generated_pre_outcome")) is True,
        bool(seal.get("observed_values_accessed")) is False,
    )
    if not all(checks):
        raise B14CIntegrityError("B14C pre-reveal B14B seal verification failed.")
    if sha256_file(pred_path) != EXPECTED_PREDICTION_SHA256:
        raise B14CIntegrityError("B14B prediction bytes differ from the frozen B14C SHA-256.")

    sealed = pd.read_csv(pred_path, low_memory=False)
    required = {
        "genotype", "environment", "predicted",
        "control_lower_90", "control_upper_90",
        "adaptive_lower_90", "adaptive_upper_90",
        "control_rule", "adaptive_rule",
        "adaptive_quantile_level", "calibration_feedback_state",
        "support_group", "reliability_state",
    }
    missing = required - set(sealed.columns)
    if missing:
        raise B14CIntegrityError(f"Sealed B14B artifact is missing columns: {sorted(missing)}")
    if sealed.duplicated(["genotype", "environment"]).any():
        raise B14CIntegrityError("Sealed B14B prediction keys are not unique.")
    if len(sealed) != EXPECTED_N_PREDICTIONS:
        raise B14CIntegrityError("Sealed B14B prediction count changed.")
    if sealed["genotype"].nunique() != EXPECTED_N_GENOTYPES or sealed["environment"].nunique() != EXPECTED_N_ENVIRONMENTS:
        raise B14CIntegrityError("Sealed B14B genotype/environment counts changed.")
    if not sealed["control_rule"].astype(str).eq(CONTROL).all():
        raise B14CIntegrityError("B14B control identity changed.")
    if not sealed["adaptive_rule"].astype(str).eq(ADAPTIVE).all():
        raise B14CIntegrityError("B14B adaptive identity changed.")
    if not sealed_csv_adaptive_level_matches(sealed["adaptive_quantile_level"].astype(float)):
        raise B14CIntegrityError("B14B adaptive level changed beyond sealed CSV precision.")
    if not sealed["calibration_feedback_state"].astype(str).eq(NO_2023_FEEDBACK).all():
        raise B14CIntegrityError("B14B calibration feedback state changed.")
    return sealed


def normalize_official_outcomes(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize only the prospectively declared official 2024 schema."""

    missing = [col for col in EXPECTED_OFFICIAL_COLUMNS if col not in frame.columns]
    if missing:
        raise B14CIntegrityError(f"Official outcome object lacks locked columns: {missing}")
    out = frame[["Hybrid", "Env", "Yield_Mg_ha"]].copy()
    out = out.rename(columns={"Hybrid": "genotype", "Env": "environment", "Yield_Mg_ha": "observed"})
    if out[["genotype", "environment"]].isna().any().any():
        raise B14CIntegrityError("Official outcome object contains missing key values.")
    out["genotype"] = out["genotype"].astype(str)
    out["environment"] = out["environment"].astype(str)
    if out.duplicated(["genotype", "environment"]).any():
        raise B14CIntegrityError("Official outcome object contains duplicate genotype-environment keys.")
    out["observed"] = pd.to_numeric(out["observed"], errors="coerce")
    return out


def build_primary_cohort(sealed: pd.DataFrame, official: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select by exact official key presence only; never by observed value."""

    try:
        cohort, audit = b13.officially_observable_sealed_cohort(
            sealed,
            official,
            genotype_col="genotype",
            environment_col="environment",
            observed_col="observed",
        )
    except (KeyError, ValueError, AssertionError) as exc:
        raise B14CIntegrityError(str(exc)) from exc
    audit = audit.copy()
    audit["stage"] = "B14C"
    audit["target_year"] = TARGET_YEAR
    return cohort, audit


def point_metrics(cohort: pd.DataFrame) -> dict[str, float]:
    y = cohort["observed"].to_numpy(float)
    pred = cohort["predicted"].to_numpy(float)
    if len(y) == 0 or np.any(~np.isfinite(y)) or np.any(~np.isfinite(pred)):
        raise B14CIntegrityError("Point metrics require finite non-empty observed/predicted values.")
    residual = y - pred
    rmse = float(np.sqrt(np.mean(residual**2)))
    mae = float(np.mean(np.abs(residual)))
    denom = float(np.sum((y - np.mean(y)) ** 2))
    r2 = float(1.0 - np.sum(residual**2) / denom) if denom > 0 else float("nan")
    corr = float(np.corrcoef(y, pred)[0, 1]) if len(y) > 1 and np.std(y) > 0 and np.std(pred) > 0 else float("nan")
    return {"rmse": rmse, "mae": mae, "r2": r2, "correlation": corr}


def interval_evaluation(cohort: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    detail = cohort.copy()
    specs = (
        (CONTROL, "control_lower_90", "control_upper_90", "control_covered_90", "control_interval_score_90"),
        (ADAPTIVE, "adaptive_lower_90", "adaptive_upper_90", "adaptive_covered_90", "adaptive_interval_score_90"),
    )
    for rule, lower_col, upper_col, covered_col, score_col in specs:
        lo = detail[lower_col].to_numpy(float)
        hi = detail[upper_col].to_numpy(float)
        y = detail["observed"].to_numpy(float)
        if np.any(~np.isfinite(lo)) or np.any(~np.isfinite(hi)) or np.any(lo > hi):
            raise B14CIntegrityError(f"Locked interval bounds invalid for {rule}.")
        covered = (y >= lo) & (y <= hi)
        detail[covered_col] = covered
        detail[score_col] = b13.interval_score_90(y, lo, hi)
        empirical = float(np.mean(covered))
        env_balanced = b13.environment_balanced_coverage(detail, covered_col)
        ci_low, ci_high = b11._cluster_coverage_ci(detail, covered_col)
        passed = b13.calibration_pass(empirical, ci_low, ci_high, TARGET_COVERAGE, MAX_COVERAGE_GAP)
        rows.append(
            {
                "rule": rule,
                "nominal": TARGET_COVERAGE,
                "n": int(len(detail)),
                "n_environments": int(detail["environment"].nunique()),
                "empirical_coverage": empirical,
                "environment_balanced_coverage": float(env_balanced),
                "cluster_ci_low": float(ci_low),
                "cluster_ci_high": float(ci_high),
                "absolute_coverage_gap": float(abs(empirical - TARGET_COVERAGE)),
                "mean_half_width": float(np.mean((hi - lo) / 2.0)),
                "mean_interval_score": float(np.mean(detail[score_col].to_numpy(float))),
                "calibration_pass": bool(passed),
            }
        )
    return pd.DataFrame(rows), detail


def environment_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for environment, part in detail.groupby("environment", sort=True):
        rows.append(
            {
                "environment": str(environment),
                "n": int(len(part)),
                "rmse": float(np.sqrt(np.mean((part["observed"].to_numpy(float) - part["predicted"].to_numpy(float)) ** 2))),
                "mae": float(np.mean(np.abs(part["observed"].to_numpy(float) - part["predicted"].to_numpy(float)))),
                "control_coverage_90": float(part["control_covered_90"].astype(float).mean()),
                "adaptive_coverage_90": float(part["adaptive_covered_90"].astype(float).mean()),
                "control_mean_interval_score_90": float(part["control_interval_score_90"].mean()),
                "adaptive_mean_interval_score_90": float(part["adaptive_interval_score_90"].mean()),
            }
        )
    return pd.DataFrame(rows)


def support_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (support_group, reliability_state), part in detail.groupby(["support_group", "reliability_state"], dropna=False, sort=True):
        rows.append(
            {
                "support_group": str(support_group),
                "reliability_state": str(reliability_state),
                "n": int(len(part)),
                "n_environments": int(part["environment"].nunique()),
                "rmse": float(np.sqrt(np.mean((part["observed"].to_numpy(float) - part["predicted"].to_numpy(float)) ** 2))),
                "mae": float(np.mean(np.abs(part["observed"].to_numpy(float) - part["predicted"].to_numpy(float)))),
                "control_coverage_90": float(part["control_covered_90"].astype(float).mean()),
                "adaptive_coverage_90": float(part["adaptive_covered_90"].astype(float).mean()),
                "support_used_for_primary_selection": False,
                "support_threshold_tuned_on_2024": False,
            }
        )
    return pd.DataFrame(rows)


def branch_decision(interval_summary: pd.DataFrame) -> str:
    indexed = interval_summary.set_index("rule")
    c_pass = bool(indexed.loc[CONTROL, "calibration_pass"])
    a_pass = bool(indexed.loc[ADAPTIVE, "calibration_pass"])
    c_score = float(indexed.loc[CONTROL, "mean_interval_score"])
    a_score = float(indexed.loc[ADAPTIVE, "mean_interval_score"])
    if a_pass:
        if a_score < c_score - 1e-12:
            return DECISION_ADAPTIVE_PROMOTED
        if c_pass:
            return DECISION_KEEP_CONTROL
        return DECISION_ADAPTIVE_INEFFICIENT
    if c_pass:
        return DECISION_KEEP_CONTROL
    return DECISION_BOTH_FAIL


def run(root: Path, outcome_path: Path) -> dict[str, Path]:
    root = root.resolve()
    outcome_path = outcome_path.resolve()
    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)

    lock = verify_pre_reveal_lock(root)
    sealed = verify_b14b_before_outcome(root)

    # The first operation on the official outcome object is hashing it.
    if not outcome_path.is_file():
        raise B14CIntegrityError("Official B14C outcome object is missing.")
    outcome_sha = sha256_file(outcome_path)
    outcome_size = int(outcome_path.stat().st_size)

    raw = pd.read_csv(outcome_path, low_memory=False)
    official = normalize_official_outcomes(raw)
    cohort, key_audit = build_primary_cohort(sealed, official)

    metrics = point_metrics(cohort)
    interval_summary, detail = interval_evaluation(cohort)
    decision = branch_decision(interval_summary)
    env = environment_summary(detail)
    support = support_summary(detail)

    # Re-verify that outcome evaluation did not mutate or replace the seal.
    if sha256_file(results / "case_study_b14b_2024_sealed_predictions.csv") != EXPECTED_PREDICTION_SHA256:
        raise B14CIntegrityError("B14B prediction artifact changed during B14C reveal.")

    primary_path = results / "case_study_b14c_2024_primary_cohort.csv"
    audit_path = results / "case_study_b14c_2024_key_audit.csv"
    interval_path = results / "case_study_b14c_2024_interval_summary.csv"
    env_path = results / "case_study_b14c_2024_environment_summary.csv"
    support_path = results / "case_study_b14c_2024_support_diagnostic.csv"
    summary_path = results / "case_study_b14c_2024_primary_summary.csv"
    decision_path = results / "case_study_b14c_2024_decision.csv"
    source_path = results / "case_study_b14c_2024_outcome_source_seal.json"

    detail.sort_values(["environment", "genotype"], kind="mergesort").to_csv(primary_path, index=False)
    key_audit.sort_values(["environment", "genotype"], kind="mergesort").to_csv(audit_path, index=False)
    interval_summary.to_csv(interval_path, index=False)
    env.to_csv(env_path, index=False)
    support.to_csv(support_path, index=False)

    pd.DataFrame([
        {
            "stage": "B14C",
            "target_year": TARGET_YEAR,
            "primary_estimand": PRIMARY_ESTIMAND,
            "n_sealed": int(len(sealed)),
            "n_officially_observable": int(len(cohort)),
            "n_sealed_keys_absent_from_official": int((~key_audit["official_answer_key_present"].astype(bool)).sum()),
            "n_genotypes": int(cohort["genotype"].nunique()),
            "n_environments": int(cohort["environment"].nunique()),
            **metrics,
            "selection_uses_outcome_value": False,
            "post_reveal_protocol_amendment": False,
            "point_predictor_changed": False,
            "b5_genotype_representation_changed": False,
            "t1_clock_changed": False,
            "t2_branch_reopened": False,
            "post_result_tuning_permitted": False,
        }
    ]).to_csv(summary_path, index=False)

    pd.DataFrame([
        {
            "stage": "B14C",
            "decision": decision,
            "prediction_sha256": EXPECTED_PREDICTION_SHA256,
            "outcome_sha256": outcome_sha,
            "primary_estimand": PRIMARY_ESTIMAND,
            "n_primary": int(len(cohort)),
            "control_calibration_pass": bool(interval_summary.set_index("rule").loc[CONTROL, "calibration_pass"]),
            "adaptive_calibration_pass": bool(interval_summary.set_index("rule").loc[ADAPTIVE, "calibration_pass"]),
            "control_mean_interval_score": float(interval_summary.set_index("rule").loc[CONTROL, "mean_interval_score"]),
            "adaptive_mean_interval_score": float(interval_summary.set_index("rule").loc[ADAPTIVE, "mean_interval_score"]),
            "adaptive_quantile_level": EXPECTED_ADAPTIVE_LEVEL,
            "selection_uses_outcome_value": False,
            "post_result_tuning_permitted": False,
        }
    ]).to_csv(decision_path, index=False)

    source_path.write_text(
        json.dumps(
            {
                "schema": "plant-intelligence-lab/b14c-2024-outcome-source-seal/v1",
                "stage": "B14C_2024_EXTERNAL_REVEAL",
                "target_year": TARGET_YEAR,
                "official_release_doi": lock["official_release_doi"],
                "official_object": lock["official_outcome_object"],
                "sha256": outcome_sha,
                "size_bytes": outcome_size,
                "prediction_sha256_verified_before_outcome_read": EXPECTED_PREDICTION_SHA256,
                "outcome_accessed": True,
                "cohort_selection_uses_outcome_value": False,
                "post_result_tuning_permitted": False,
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return {
        "primary_cohort": primary_path,
        "key_audit": audit_path,
        "interval_summary": interval_path,
        "environment_summary": env_path,
        "support_diagnostic": support_path,
        "primary_summary": summary_path,
        "decision": decision_path,
        "outcome_source_seal": source_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--outcome-file", type=Path, required=True)
    args = parser.parse_args()
    outputs = run(args.output_root, args.outcome_file)
    for key, path in outputs.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()