"""Post-reveal available-case diagnostic for Case Study B12.

This module does not replace the original B12 confirmatory reveal rule.  The
420-row Stage-A prediction artifact remains immutable.  The strict primary B12
protocol requires an official outcome for every sealed key and therefore remains
incomplete when the public answer key omits sealed genotype-environment cells.

After that incompleteness was discovered, this module was added as an explicitly
post-reveal diagnostic.  It evaluates only sealed keys that are present in the
official answer key.  Cohort membership is determined by exact key presence,
never by the numerical outcome value.  No prediction, interval, support rule,
hyperparameter, or T2 decision is changed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_transfer_robustness import metrics
from plant_intelligence.uncertainty.maize_external_temporal_validation import (
    FORBIDDEN_ANSWER_BASENAME,
    TARGET_YEAR,
    _answer_columns,
    _normalized,
    acquire_stage_b_answer,
    sha256_file,
    verify_prediction_seal,
)
from plant_intelligence.uncertainty.maize_forward_uncertainty import (
    ABSTAIN,
    NOMINAL_LEVELS,
    RETAIN,
    _cluster_coverage_ci,
)

PRIMARY_INCOMPLETE = "B12_PRIMARY_INCOMPLETE_OFFICIAL_OUTCOME_MATCH"
DIAGNOSTIC_LABEL = "POST_REVEAL_AVAILABLE_CASE_DIAGNOSTIC"
SELECTION_RULE = "SEALED_KEY_PRESENT_IN_OFFICIAL_ANSWER_KEY"


def _load_official_answer(answer_path: Path) -> pd.DataFrame:
    """Load the official answer while preserving key-presence as the selector."""

    if _normalized(answer_path.name) != _normalized(FORBIDDEN_ANSWER_BASENAME):
        raise ValueError("B12 diagnostic requires the official observed-answer basename.")
    answer = pd.read_csv(answer_path, low_memory=False)
    g_col, e_col, y_col = _answer_columns(answer)
    observed = answer[[g_col, e_col, y_col]].copy()
    observed.columns = ["genotype", "environment", "observed"]
    observed["genotype"] = observed["genotype"].astype(str)
    observed["environment"] = observed["environment"].astype(str)

    duplicate = observed.duplicated(["genotype", "environment"], keep=False)
    if duplicate.any():
        conflicting = (
            observed.loc[duplicate]
            .assign(_numeric=pd.to_numeric(observed.loc[duplicate, "observed"], errors="coerce"))
            .groupby(["genotype", "environment"])["_numeric"]
            .nunique(dropna=False)
        )
        if (conflicting > 1).any():
            raise ValueError("Official B12 answer contains conflicting duplicate key outcomes.")
        observed = observed.drop_duplicates(["genotype", "environment"])

    observed["observed"] = pd.to_numeric(observed["observed"], errors="coerce")
    return observed


def _environment_diagnostics(cohort: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for environment, part in cohort.groupby("environment", sort=True):
        available = part[part["official_answer_key_present"]].copy()
        row: dict[str, object] = {
            "environment": str(environment),
            "n_sealed": int(len(part)),
            "n_officially_observable": int(len(available)),
            "observable_fraction": float(len(available) / len(part)),
            "selection_rule": SELECTION_RULE,
            "selection_uses_outcome_value": False,
            "diagnostic_only": True,
        }
        if len(available):
            row.update(metrics(available["observed"], available["predicted"]))
            row["coverage_90"] = float(
                (
                    (available["observed"] >= available["lower_90"])
                    & (available["observed"] <= available["upper_90"])
                ).mean()
            )
        else:
            row.update({"rmse": np.nan, "mae": np.nan, "r2": np.nan, "correlation": np.nan})
            row["coverage_90"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_available_case_diagnostic(
    prediction_path: Path,
    seal_path: Path,
    answer_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate the externally observable subset without altering B12 primary status."""

    seal = verify_prediction_seal(prediction_path, seal_path)
    predictions = pd.read_csv(prediction_path)
    if predictions.duplicated(["genotype", "environment"]).any():
        raise ValueError("Sealed B12 predictions are not unique by genotype/environment.")
    predictions["genotype"] = predictions["genotype"].astype(str)
    predictions["environment"] = predictions["environment"].astype(str)

    observed = _load_official_answer(answer_path)
    answer_keys = observed[["genotype", "environment"]].drop_duplicates().copy()
    answer_keys["official_answer_key_present"] = True

    # The selector is constructed from exact key membership before outcome values
    # are merged.  Numerical yield never participates in cohort selection.
    cohort = predictions.merge(
        answer_keys,
        on=["genotype", "environment"],
        how="left",
        validate="one_to_one",
    )
    cohort["official_answer_key_present"] = cohort["official_answer_key_present"].fillna(False).astype(bool)
    cohort = cohort.merge(
        observed,
        on=["genotype", "environment"],
        how="left",
        validate="one_to_one",
    )

    present = cohort["official_answer_key_present"]
    if cohort.loc[present, "observed"].isna().any():
        raise ValueError(
            "Official answer contains a sealed key with a missing/non-numeric outcome; "
            "B12 diagnostic refuses outcome-value-based row deletion."
        )
    if cohort.loc[~present, "observed"].notna().any():
        raise AssertionError("Outcome attached to a key not present in the official answer-key set.")

    available = cohort.loc[present].copy()
    if available.empty:
        raise ValueError("No sealed B12 prediction has an official observable outcome.")

    n_sealed = int(len(cohort))
    n_available = int(len(available))
    n_missing = int(n_sealed - n_available)
    if int(seal["n_predictions"]) != n_sealed:
        raise ValueError("Seal count and committed prediction count disagree.")

    primary_status = pd.DataFrame(
        [
            {
                "target_year": TARGET_YEAR,
                "prediction_sha256": seal["prediction_sha256"],
                "answer_sha256": sha256_file(answer_path),
                "n_sealed_predictions": n_sealed,
                "n_officially_observable": n_available,
                "n_missing_official_answer_keys": n_missing,
                "officially_observable_fraction": float(n_available / n_sealed),
                "primary_confirmatory_evaluable": bool(n_missing == 0),
                "primary_status": (
                    "B12_PRIMARY_COMPLETE_OFFICIAL_OUTCOME_MATCH"
                    if n_missing == 0
                    else PRIMARY_INCOMPLETE
                ),
                "sealed_artifact_replaced_or_resealed": False,
                "post_reveal_protocol_amendment": True,
                "available_case_diagnostic_confirmatory": False,
                "selection_rule": SELECTION_RULE,
                "selection_uses_outcome_value": False,
                "predictive_model_refit_after_reveal": False,
                "interval_retuned_after_reveal": False,
                "support_threshold_retuned_after_reveal": False,
                "t2_branch_reopened": False,
                "post_result_tuning_permitted": False,
            }
        ]
    )

    coverage_rows: list[dict[str, object]] = []
    for level in NOMINAL_LEVELS:
        key = int(round(100 * level))
        covered_col = f"_diagnostic_covered_{key}"
        available[covered_col] = (
            (available["observed"] >= available[f"lower_{key}"])
            & (available["observed"] <= available[f"upper_{key}"])
        )
        low, high = _cluster_coverage_ci(available, covered_col)
        env_cov = available.groupby("environment")[covered_col].mean()
        coverage_rows.append(
            {
                "diagnostic": DIAGNOSTIC_LABEL,
                "confirmatory": False,
                "nominal": float(level),
                "n": n_available,
                "n_environments": int(available["environment"].nunique()),
                "empirical_coverage": float(available[covered_col].mean()),
                "environment_balanced_coverage": float(env_cov.mean()),
                "environment_cluster_ci95_low": float(low),
                "environment_cluster_ci95_high": float(high),
                "mean_interval_width": float(
                    (available[f"upper_{key}"] - available[f"lower_{key}"]).mean()
                ),
                "absolute_coverage_gap": abs(float(available[covered_col].mean()) - float(level)),
                "selection_rule": SELECTION_RULE,
                "selection_uses_outcome_value": False,
                "post_reveal_protocol_amendment": True,
            }
        )
    coverage = pd.DataFrame(coverage_rows)

    reliability_rows: list[dict[str, object]] = []
    for state in ("ALL_AVAILABLE_CASES", RETAIN, ABSTAIN):
        part = (
            available
            if state == "ALL_AVAILABLE_CASES"
            else available[available["reliability_state"].astype(str).eq(state)]
        )
        if part.empty:
            continue
        reliability_rows.append(
            {
                "diagnostic": DIAGNOSTIC_LABEL,
                "confirmatory": False,
                "state": state,
                "n": int(len(part)),
                "n_environments": int(part["environment"].nunique()),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    reliability = pd.DataFrame(reliability_rows)

    c90 = coverage[np.isclose(coverage["nominal"], 0.90)].iloc[0]
    diagnostic_criterion_met = bool(
        abs(float(c90["empirical_coverage"]) - 0.90) <= 0.03
        and float(c90["environment_cluster_ci95_low"])
        <= 0.90
        <= float(c90["environment_cluster_ci95_high"])
    )
    overall = metrics(available["observed"], available["predicted"])
    summary = pd.DataFrame(
        [
            {
                "target_year": TARGET_YEAR,
                "diagnostic": DIAGNOSTIC_LABEL,
                "confirmatory": False,
                "post_reveal_protocol_amendment": True,
                "prediction_sha256": seal["prediction_sha256"],
                "answer_sha256": sha256_file(answer_path),
                "n_sealed_predictions": n_sealed,
                "n_evaluated_available_cases": n_available,
                "n_excluded_missing_official_keys": n_missing,
                "n_environments": int(available["environment"].nunique()),
                "n_genotypes": int(available["genotype"].nunique()),
                **overall,
                "coverage_90": float(c90["empirical_coverage"]),
                "coverage_90_env_ci_low": float(c90["environment_cluster_ci95_low"]),
                "coverage_90_env_ci_high": float(c90["environment_cluster_ci95_high"]),
                "diagnostic_90_criterion_met": diagnostic_criterion_met,
                "primary_confirmatory_evaluable": bool(n_missing == 0),
                "selection_rule": SELECTION_RULE,
                "selection_uses_outcome_value": False,
                "sealed_artifact_replaced_or_resealed": False,
                "predictive_model_refit_after_reveal": False,
                "interval_retuned_after_reveal": False,
                "support_threshold_retuned_after_reveal": False,
                "t2_branch_reopened": False,
                "post_result_tuning_permitted": False,
                "decision": (
                    "B12_AVAILABLE_CASE_DIAGNOSTIC_90_CRITERION_MET"
                    if diagnostic_criterion_met
                    else "B12_AVAILABLE_CASE_DIAGNOSTIC_90_CRITERION_NOT_MET"
                ),
            }
        ]
    )

    environment = _environment_diagnostics(cohort)
    cohort_audit = cohort[
        ["genotype", "environment", "official_answer_key_present"]
    ].copy()
    cohort_audit["selection_rule"] = SELECTION_RULE
    cohort_audit["selection_uses_outcome_value"] = False
    cohort_audit["diagnostic_only"] = True
    return primary_status, summary, coverage, reliability, environment, cohort_audit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the post-reveal B12 available-case diagnostic without changing the seal."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--download-answer", action="store_true")
    args = parser.parse_args()

    root = args.output_root.resolve()
    results = root / "reports" / "results"
    answer = args.answer_file
    if answer is None and args.download_answer:
        answer = acquire_stage_b_answer(root)
    if answer is None:
        raise SystemExit("B12 diagnostic requires --answer-file or --download-answer.")

    outputs = evaluate_available_case_diagnostic(
        results / "case_study_b12_2022_sealed_predictions.csv",
        results / "case_study_b12_2022_prediction_seal.json",
        answer,
    )
    primary, summary, coverage, reliability, environment, cohort_audit = outputs
    results.mkdir(parents=True, exist_ok=True)
    primary.to_csv(results / "case_study_b12_2022_primary_status.csv", index=False)
    summary.to_csv(results / "case_study_b12_2022_available_case_summary.csv", index=False)
    coverage.to_csv(results / "case_study_b12_2022_available_case_coverage.csv", index=False)
    reliability.to_csv(results / "case_study_b12_2022_available_case_reliability.csv", index=False)
    environment.to_csv(results / "case_study_b12_2022_available_case_by_environment.csv", index=False)
    cohort_audit.to_csv(results / "case_study_b12_2022_available_case_cohort_audit.csv", index=False)

    print(primary.to_string(index=False))
    print("\nAvailable-case diagnostic")
    print(summary.to_string(index=False))
    print("\nCoverage")
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
