"""B17-T1: architecture-contraction novelty kill test.

This stage is outcome-closed. It reads only the immutable B14B pre-outcome
sealed predictions plus the already-merged B17 decision. It does not generate
predictions, fit/rescale a model, access B14C outcomes, or promote a correction.

The frozen G+E_T1 predictor is additive in genomic and environmental feature
blocks. In real arithmetic the environmental main-effect block therefore
cancels from every within-environment genotype contrast. The deployed feature
construction, however, uses float32 arrays. A first real-seal CI audit wrongly
used a 1e-8 CSV-only tolerance and failed. That failure is preserved in the
B17-T1 numerical amendment. The corrected empirical reproduction check uses a
fixed four-term float32 ULP budget derived from the contrast identity, while the
scientific novelty decision remains unchanged.
"""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SEALED_REL = Path("reports/results/case_study_b14b_2024_sealed_predictions.csv")
B17_DECISION_REL = Path("reports/results/case_study_b17_decision.csv")
LOCK_REL = Path("reports/results/case_study_b17_t1_architecture_contraction_lock.json")
AMENDMENT_REL = Path("reports/results/case_study_b17_t1_numerical_amendment.json")

EXPECTED_PARENT = "B17_BROAD_RESPONSE_AMPLITUDE_NOVELTY_REJECTED_OPEN_ARCHITECTURE_CONTRACTION_TEST"
DECISION = "B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_REJECTED_TERMINATE_B17"
CSV_ONLY_TOLERANCE = 1e-8
FLOAT32_FOUR_TERM_ULP_BUDGET = 4.0


@dataclass(frozen=True)
class InvarianceSummary:
    n_prediction_rows: int
    n_environments: int
    n_genotypes: int
    n_environment_pairs_with_two_or_more_common_genotypes: int
    min_common_genotypes: int
    max_common_genotypes: int
    total_environment_pair_common_genotype_pairs: int
    max_abs_pairwise_contrast_deviation: float
    max_abs_centered_prediction_deviation: float
    max_environment_offset_sd: float
    max_float32_ulp_across_sealed_predictions: float
    max_pairwise_deviation_in_local_float32_ulp: float
    max_float32_implementation_bound: float
    all_environment_pair_contrasts_invariant_within_csv_only_precision: bool
    all_environment_pair_contrasts_consistent_with_float32_implementation: bool
    csv_only_tolerance: float
    float32_four_term_ulp_budget: float


def validate_sealed_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "genotype",
        "environment",
        "predicted",
        "test_year",
        "model",
        "horizon",
        "genotype_support_state",
        "environment_input_state",
        "support_boundary_uses_outcome",
        "observed_values_accessed",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"B17-T1 sealed prediction artifact missing columns: {missing}")
    out = frame.copy()
    if len(out) != 798:
        raise ValueError(f"B17-T1 expects 798 sealed B14B rows, found {len(out)}")
    if out.duplicated(["genotype", "environment"]).any():
        raise ValueError("B17-T1 refuses duplicate sealed genotype-environment keys.")
    if out["environment"].nunique() != 19 or out["genotype"].nunique() != 92:
        raise ValueError("B17-T1 sealed cohort dimensions differ from B14B.")
    if not out["test_year"].astype(int).eq(2024).all():
        raise ValueError("B17-T1 sealed input is not the 2024 B14B object.")
    if not out["model"].astype(str).eq("G+E_T1").all():
        raise ValueError("B17-T1 sealed input is not the frozen G+E_T1 model.")
    if not out["horizon"].astype(str).eq("T1_30DAP").all():
        raise ValueError("B17-T1 sealed input is not the frozen T1_30DAP horizon.")
    if not out["genotype_support_state"].astype(str).eq("SUPPORTED_FROZEN_B5_GENOME").all():
        raise ValueError("B17-T1 detects a changed genomic-support state.")
    if not out["environment_input_state"].astype(str).eq("SUPPORTED_T1_CONTEXT").all():
        raise ValueError("B17-T1 detects a changed environmental-input state.")
    if not out["support_boundary_uses_outcome"].astype(str).str.lower().eq("false").all():
        raise ValueError("B17-T1 sealed support boundary reports outcome use.")
    if not out["observed_values_accessed"].astype(str).str.lower().eq("false").all():
        raise ValueError("B17-T1 sealed artifact reports outcome access.")
    out["predicted"] = pd.to_numeric(out["predicted"], errors="coerce")
    if out["predicted"].isna().any() or not np.isfinite(out["predicted"].to_numpy(float)).all():
        raise ValueError("B17-T1 requires finite sealed predictions.")
    return out


def additive_prediction(
    genomic: np.ndarray,
    environment: np.ndarray,
    beta_g: np.ndarray,
    beta_e: np.ndarray,
    intercept: float = 0.0,
) -> np.ndarray:
    """Synthetic reference for the frozen additive G+E functional form."""
    g = np.asarray(genomic, dtype=float)
    e = np.asarray(environment, dtype=float)
    bg = np.asarray(beta_g, dtype=float)
    be = np.asarray(beta_e, dtype=float)
    return np.asarray(intercept + g @ bg + e @ be, dtype=float)


def interaction_prediction(
    genomic_scalar: np.ndarray,
    environment_scalar: np.ndarray,
    beta_g: float,
    beta_e: float,
    beta_ge: float,
    intercept: float = 0.0,
) -> np.ndarray:
    """Minimal counterexample: a genuine GxE term breaks contrast invariance."""
    g = np.asarray(genomic_scalar, dtype=float)
    e = np.asarray(environment_scalar, dtype=float)
    return np.asarray(intercept + beta_g * g + beta_e * e + beta_ge * g * e, dtype=float)


def ridge_spectral_filters(singular_values: np.ndarray, alpha: float) -> pd.DataFrame:
    """Return standard ridge coefficient/fitted-value spectral filters."""
    s = np.asarray(singular_values, dtype=float)
    if alpha <= 0.0:
        raise ValueError("B17-T1 requires a positive ridge penalty.")
    if np.any(s < 0.0) or not np.isfinite(s).all():
        raise ValueError("Singular values must be finite and nonnegative.")
    denom = np.square(s) + float(alpha)
    return pd.DataFrame(
        {
            "singular_value": s,
            "ridge_alpha": float(alpha),
            "coefficient_filter_sigma_over_sigma2_plus_alpha": s / denom,
            "fitted_value_filter_sigma2_over_sigma2_plus_alpha": np.square(s) / denom,
            "standard_ridge_prior_art_object": True,
        }
    )


def _float32_ulp(values: np.ndarray) -> np.ndarray:
    v32 = np.asarray(values, dtype=np.float32)
    return np.abs(np.spacing(v32).astype(float))


def pairwise_invariance_audit(
    frame: pd.DataFrame,
    csv_tolerance: float = CSV_ONLY_TOLERANCE,
    ulp_budget: float = FLOAT32_FOUR_TERM_ULP_BUDGET,
) -> tuple[pd.DataFrame, InvarianceSummary]:
    """Audit the additive contrast identity using only sealed predictions.

    For environments a,b and a genotype g shared by both,
        pred(g,a) - pred(g,b)
    is an environment offset in exact arithmetic. Hence, for any shared pair
    i,j, the four-term residual
        (pred(i,a)-pred(j,a)) - (pred(i,b)-pred(j,b))
    is exactly zero.

    The frozen implementation uses float32 feature arrays. The implementation
    audit therefore grants one float32 ULP to each of the four stored
    predictions participating in the identity, plus the separately preserved
    CSV serialization allowance. This fixed arithmetic budget is not selected
    from the observed deviation.
    """
    if csv_tolerance < 0.0 or ulp_budget <= 0.0:
        raise ValueError("B17-T1 numerical tolerances must be nonnegative/positive.")
    data = frame[["genotype", "environment", "predicted"]].copy()
    env_tables = {
        str(env): part.set_index("genotype")["predicted"].astype(float).sort_index()
        for env, part in data.groupby("environment", sort=True)
    }
    rows: list[dict[str, object]] = []
    for env_a, env_b in itertools.combinations(sorted(env_tables), 2):
        a = env_tables[env_a]
        b = env_tables[env_b]
        common = a.index.intersection(b.index).sort_values()
        if len(common) < 2:
            continue
        pa = a.loc[common].to_numpy(float)
        pb = b.loc[common].to_numpy(float)
        offsets = pa - pb
        max_pairwise = float(np.max(offsets) - np.min(offsets))
        ca = pa - float(np.mean(pa))
        cb = pb - float(np.mean(pb))
        max_centered = float(np.max(np.abs(ca - cb)))
        offset_sd = float(np.std(offsets, ddof=1))
        local_max_ulp = float(np.max(_float32_ulp(np.concatenate([pa, pb]))))
        implementation_bound = float(ulp_budget * local_max_ulp + csv_tolerance)
        ratio = float(max_pairwise / local_max_ulp) if local_max_ulp > 0.0 else float("inf")
        n_pairs = int(len(common) * (len(common) - 1) // 2)
        rows.append(
            {
                "environment_a": env_a,
                "environment_b": env_b,
                "n_common_genotypes": int(len(common)),
                "n_common_unordered_genotype_pairs": n_pairs,
                "mean_prediction_offset_a_minus_b": float(np.mean(offsets)),
                "environment_offset_sd_across_common_genotypes": offset_sd,
                "max_abs_pairwise_contrast_deviation": max_pairwise,
                "max_abs_centered_prediction_deviation": max_centered,
                "local_max_float32_ulp": local_max_ulp,
                "max_pairwise_deviation_in_local_float32_ulp": ratio,
                "float32_four_term_ulp_budget": float(ulp_budget),
                "float32_implementation_bound": implementation_bound,
                "invariant_within_csv_only_precision": bool(max_pairwise <= csv_tolerance),
                "consistent_with_float32_implementation": bool(max_pairwise <= implementation_bound),
                "uses_target_outcomes": False,
            }
        )
    audit = pd.DataFrame(rows)
    if audit.empty:
        raise ValueError("B17-T1 found no environment pair with >=2 common genotypes.")
    all_ulps = _float32_ulp(data["predicted"].to_numpy(float))
    summary = InvarianceSummary(
        n_prediction_rows=int(len(data)),
        n_environments=int(data["environment"].nunique()),
        n_genotypes=int(data["genotype"].nunique()),
        n_environment_pairs_with_two_or_more_common_genotypes=int(len(audit)),
        min_common_genotypes=int(audit["n_common_genotypes"].min()),
        max_common_genotypes=int(audit["n_common_genotypes"].max()),
        total_environment_pair_common_genotype_pairs=int(
            audit["n_common_unordered_genotype_pairs"].sum()
        ),
        max_abs_pairwise_contrast_deviation=float(
            audit["max_abs_pairwise_contrast_deviation"].max()
        ),
        max_abs_centered_prediction_deviation=float(
            audit["max_abs_centered_prediction_deviation"].max()
        ),
        max_environment_offset_sd=float(
            audit["environment_offset_sd_across_common_genotypes"].max()
        ),
        max_float32_ulp_across_sealed_predictions=float(np.max(all_ulps)),
        max_pairwise_deviation_in_local_float32_ulp=float(
            audit["max_pairwise_deviation_in_local_float32_ulp"].max()
        ),
        max_float32_implementation_bound=float(
            audit["float32_implementation_bound"].max()
        ),
        all_environment_pair_contrasts_invariant_within_csv_only_precision=bool(
            audit["invariant_within_csv_only_precision"].all()
        ),
        all_environment_pair_contrasts_consistent_with_float32_implementation=bool(
            audit["consistent_with_float32_implementation"].all()
        ),
        csv_only_tolerance=float(csv_tolerance),
        float32_four_term_ulp_budget=float(ulp_budget),
    )
    return audit, summary


def operator_equivalence_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "candidate_object": "ENVIRONMENT_BLOCK_CANCELLATION_IN_WITHIN_ENVIRONMENT_CONTRASTS",
                "mathematical_status": "EXACT_IN_REAL_ARITHMETIC_FOR_FROZEN_ADDITIVE_G_PLUS_E_OPERATOR",
                "prior_art_family": "ADDITIVE_MODEL_WITHOUT_GXE_INTERACTION",
                "outcome_free_computable": True,
                "method_novelty_survives": False,
                "reason": "Environment main effect is common within environment and cancels algebraically; lack of environment-specific genotype contrasts is the standard no-interaction restriction.",
            },
            {
                "candidate_object": "RIDGE_MODE_ATTENUATION",
                "mathematical_status": "EXACT_SPECTRAL_FILTER_SIGMA2_OVER_SIGMA2_PLUS_ALPHA",
                "prior_art_family": "RIDGE_AND_KERNEL_RIDGE_SPECTRAL_FILTERING",
                "outcome_free_computable": True,
                "method_novelty_survives": False,
                "reason": "The proposed contraction factor is the standard ridge smoother spectral filter.",
            },
            {
                "candidate_object": "GENOTYPE_CONTRAST_RELIABILITY",
                "mathematical_status": "MODEL_BASED_IF_VARIANCE_MODEL_SPECIFIED",
                "prior_art_family": "BLUP_PEV_GENERALIZED_CD_ENTRY_DIFFERENCE_RELIABILITY",
                "outcome_free_computable": True,
                "method_novelty_survives": False,
                "reason": "PEV and generalized CD already quantify prospective reliability/precision of breeding-value contrasts.",
            },
            {
                "candidate_object": "TARGET_POINT_GEOMETRY_OR_LEVERAGE_UNCERTAINTY",
                "mathematical_status": "ESTABLISHED_LINEAR_SMOOTHER_OR_KRR_GEOMETRY",
                "prior_art_family": "RIDGE_LEVERAGE_RKHS_POWER_FUNCTION_KRR_ERROR_BOUNDS",
                "outcome_free_computable": True,
                "method_novelty_survives": False,
                "reason": "Geometry-dependent leverage and prediction-error bounds are established ridge/kernel uncertainty objects.",
            },
            {
                "candidate_object": "CONTRACTION_RELATIVE_TO_UNSEEN_TRUE_ENVIRONMENT_SPECIFIC_RESPONSE",
                "mathematical_status": "NOT_DISTRIBUTION_FREE_POINT_IDENTIFIED_WITHOUT_ADDITIONAL_ASSUMPTIONS",
                "prior_art_family": "IDENTIFICATION_BOUNDARY",
                "outcome_free_computable": False,
                "method_novelty_survives": False,
                "reason": "The same pre-outcome state and prediction vector are compatible with different target-response amplitudes; B17 already supplied the witness.",
            },
        ]
    )


def _verify_protocol(root: Path) -> None:
    lock = json.loads((root / LOCK_REL).read_text(encoding="utf-8"))
    if lock.get("status") != "LOCKED_BEFORE_OPERATOR_EQUIVALENCE_AUDIT":
        raise ValueError("B17-T1 lock is missing or altered.")
    if lock.get("parent_decision") != EXPECTED_PARENT:
        raise ValueError("B17-T1 parent decision does not match B17.")
    if lock.get("predeclared_decision") != DECISION:
        raise ValueError("B17-T1 predeclared terminal decision was altered.")
    forbidden = [
        "new_outcome_access_permitted",
        "b14c_outcome_input_permitted",
        "new_prediction_generation_permitted",
        "point_predictor_refit_permitted",
        "point_predictor_rescaling_permitted",
        "interval_or_support_tuning_permitted",
        "b5_genomic_change_permitted",
        "t1_clock_change_permitted",
        "t2_reopen_permitted",
        "reseal_permitted",
        "post_result_tuning_permitted",
        "new_method_claim_permitted",
        "b17_t2_permitted",
    ]
    if any(bool(lock.get(name, True)) for name in forbidden):
        raise ValueError("B17-T1 lock permits a forbidden operation.")

    amendment = json.loads((root / AMENDMENT_REL).read_text(encoding="utf-8"))
    if amendment.get("status") != "POST_EXECUTION_NUMERICAL_AMENDMENT_NO_SCIENTIFIC_DECISION_CHANGE":
        raise ValueError("B17-T1 numerical amendment is missing or altered.")
    if amendment.get("parent_lock_remains_unchanged") is not True:
        raise ValueError("B17-T1 numerical amendment must preserve the original lock.")
    if amendment.get("float32_ulp_budget_per_four_term_contrast_identity") != FLOAT32_FOUR_TERM_ULP_BUDGET:
        raise ValueError("B17-T1 float32 ULP policy differs from its recorded amendment.")
    if amendment.get("replacement_policy_selected_from_observed_maximum") is not False:
        raise ValueError("B17-T1 refuses a result-fitted numerical tolerance.")
    if amendment.get("novelty_decision_changed") is not False:
        raise ValueError("B17-T1 numerical amendment cannot change the novelty decision.")


def run(output_root: Path) -> dict[str, Path]:
    root = Path(output_root)
    _verify_protocol(root)

    b17 = pd.read_csv(root / B17_DECISION_REL)
    if len(b17) != 1 or str(b17.iloc[0]["decision"]) != EXPECTED_PARENT:
        raise ValueError("B17-T1 requires the merged B17 routing decision.")

    sealed = validate_sealed_predictions(pd.read_csv(root / SEALED_REL, low_memory=False))
    audit, summary = pairwise_invariance_audit(sealed)
    # Preserve the failed first check rather than silently redefining it.
    if summary.all_environment_pair_contrasts_invariant_within_csv_only_precision:
        raise AssertionError("B17-T1 expected the preserved first-run CSV-only check to remain false.")
    if not summary.all_environment_pair_contrasts_consistent_with_float32_implementation:
        raise AssertionError(
            "B17-T1 sealed predictions exceed the fixed float32 four-term ULP implementation budget."
        )

    equivalence = operator_equivalence_table()
    if equivalence["method_novelty_survives"].astype(bool).any():
        raise AssertionError("B17-T1 equivalence table unexpectedly promotes novelty.")

    spectral = ridge_spectral_filters(
        np.asarray([0.0, 0.25, 0.5, 1.0, 2.0, np.sqrt(10.0), 5.0, 10.0, 20.0]),
        alpha=10.0,
    )

    results = root / "reports" / "results"
    audit_path = results / "case_study_b17_t1_pairwise_invariance_audit.csv"
    summary_path = results / "case_study_b17_t1_pairwise_invariance_summary.csv"
    equivalence_path = results / "case_study_b17_t1_operator_equivalence.csv"
    spectral_path = results / "case_study_b17_t1_ridge_spectral_reference.csv"
    decision_path = results / "case_study_b17_t1_decision.csv"
    audit.to_csv(audit_path, index=False)
    pd.DataFrame([asdict(summary)]).to_csv(summary_path, index=False)
    equivalence.to_csv(equivalence_path, index=False)
    spectral.to_csv(spectral_path, index=False)
    pd.DataFrame(
        [
            {
                "stage": "B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_TEST",
                "decision": DECISION,
                "sealed_prediction_only_empirical_audit": True,
                "b14c_outcome_input_used": False,
                "new_outcome_access": False,
                "new_prediction_generation": False,
                "point_predictor_changed": False,
                "point_predictor_rescaled": False,
                "additive_contrast_invariance_exact_real_arithmetic_property": True,
                "initial_csv_only_precision_check_passed": False,
                "post_execution_numerical_amendment_recorded": True,
                "sealed_predictions_consistent_with_float32_implementation": True,
                "additive_contrast_invariance_method_novelty": False,
                "ridge_spectral_filter_method_novelty": False,
                "contrast_pev_cd_method_novelty": False,
                "kernel_leverage_error_bound_method_novelty": False,
                "true_target_amplitude_point_identified_without_assumptions": False,
                "b17_t2_permitted": False,
                "t2_reopened": False,
                "post_result_tuning_permitted": False,
                "research_branch_state": "B17_CLOSED_NO_MODEL_MODIFICATION",
            }
        ]
    ).to_csv(decision_path, index=False)
    return {
        "invariance_audit": audit_path,
        "invariance_summary": summary_path,
        "operator_equivalence": equivalence_path,
        "ridge_spectral_reference": spectral_path,
        "decision": decision_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    for name, path in paths.items():
        print(f"{name}: {path}")
    print(pd.read_csv(paths["invariance_summary"]).to_string(index=False))
    print(pd.read_csv(paths["decision"]).to_string(index=False))


if __name__ == "__main__":
    main()
