"""Terminal Case Study B closure and scientific-contribution audit.

The closure stage synthesizes already-merged B12--B17 evidence. It does not
open a new outcome, generate predictions, tune an interval/support rule, refit
or rescale the point predictor, alter B5/T1/T2, or create a B18 model.

The purpose is deliberately conservative: classify each stage by evidentiary
status, state what the full sequence supports scientifically, forbid inflated
publication claims, and route any future B18 work through a separate hypothesis
and novelty gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

LOCK_REL = Path("reports/results/case_study_b_closure_lock.json")

B12_PRIMARY = Path("reports/results/case_study_b12_2022_primary_status.csv")
B12_DIAGNOSTIC = Path("reports/results/case_study_b12_2022_available_case_summary.csv")
B12_COVERAGE = Path("reports/results/case_study_b12_2022_available_case_coverage.csv")
B13_LOCK = Path("reports/results/case_study_b13_preoutcome_lock.csv")
B13A = Path("reports/results/case_study_b13a_2023_lock_decision.csv")
B13S = Path("reports/results/case_study_b13s_2023_lock_decision.csv")
B14A = Path("reports/results/case_study_b14a_2024_lock_decision.csv")
B14B = Path("reports/results/case_study_b14b_2024_seal_decision.csv")
B14C_PRIMARY = Path("reports/results/case_study_b14c_2024_primary_summary.csv")
B14C_INTERVAL = Path("reports/results/case_study_b14c_2024_interval_summary.csv")
B14C_DECISION = Path("reports/results/case_study_b14c_2024_decision.csv")
B15_LOCK = Path("reports/results/case_study_b15_theory_lock.json")
B16_SUMMARY = Path("reports/results/case_study_b16_2024_error_structure_summary.csv")
B16_DECISION = Path("reports/results/case_study_b16_decision.csv")
B17_DECISION = Path("reports/results/case_study_b17_decision.csv")
B17T1_DECISION = Path("reports/results/case_study_b17_t1_decision.csv")

CLOSURE_DECISION = (
    "CASE_STUDY_B_CLOSED_EXTERNAL_VALIDATION_CONTRIBUTION_SUPPORTED_"
    "METHOD_NOVELTY_NOT_SUPPORTED_B18_SEPARATE_HYPOTHESIS_GATE_ONLY"
)
PUBLICATION_FRAME = (
    "SEAL_FIRST_BLINDED_EXTERNAL_VALIDATION_AND_FAILURE_ANALYSIS_"
    "NOT_NEW_PREDICTIVE_METHOD"
)


def _one_csv(root: Path, rel: Path) -> pd.Series:
    frame = pd.read_csv(root / rel, low_memory=False)
    if len(frame) != 1:
        raise ValueError(f"Closure audit expected one row in {rel}, found {len(frame)}")
    return frame.iloc[0]


def _bool(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Cannot interpret boolean value {value!r}")


def _close(a: float, b: float, tol: float = 1e-12) -> bool:
    return bool(np.isclose(float(a), float(b), atol=tol, rtol=0.0))


def verify_lock(root: Path) -> dict:
    lock = json.loads((root / LOCK_REL).read_text(encoding="utf-8"))
    if lock.get("status") != "LOCKED_BEFORE_SYNTHESIS":
        raise ValueError("Case Study B closure lock is missing or altered.")
    if lock.get("predeclared_closure_decision") != CLOSURE_DECISION:
        raise ValueError("Closure decision differs from the locked decision.")
    if lock.get("predeclared_publication_frame") != PUBLICATION_FRAME:
        raise ValueError("Publication frame differs from the locked frame.")
    forbidden = [
        "new_outcome_access_permitted",
        "new_prediction_generation_permitted",
        "point_predictor_change_permitted",
        "point_predictor_rescaling_permitted",
        "interval_or_support_tuning_permitted",
        "b5_genotype_representation_change_permitted",
        "t1_clock_change_permitted",
        "t2_reopening_permitted",
        "reseal_permitted",
        "post_result_tuning_permitted",
        "b18_model_development_permitted_inside_closure",
        "b18_automatic_opening_permitted",
    ]
    if any(bool(lock.get(name, True)) for name in forbidden):
        raise ValueError("Closure lock permits a forbidden operation.")
    boundary = lock.get("publication_language_boundary", {})
    if boundary.get("calendar_time_prospective_claim_permitted") is not False:
        raise ValueError("Closure must forbid calendar-time prospective overclaiming.")
    if boundary.get("seal_first_blinded_external_validation_claim_permitted") is not True:
        raise ValueError("Closure must preserve the accurate seal-first blinded wording.")
    return lock


def verify_evidence(root: Path) -> dict[str, object]:
    b12p = _one_csv(root, B12_PRIMARY)
    b12d = _one_csv(root, B12_DIAGNOSTIC)
    b12cov = pd.read_csv(root / B12_COVERAGE, low_memory=False)
    b13 = _one_csv(root, B13_LOCK)
    b13a = _one_csv(root, B13A)
    b13s = _one_csv(root, B13S)
    b14a = _one_csv(root, B14A)
    b14b = _one_csv(root, B14B)
    b14cp = _one_csv(root, B14C_PRIMARY)
    b14cd = _one_csv(root, B14C_DECISION)
    b14ci = pd.read_csv(root / B14C_INTERVAL, low_memory=False)
    b15 = json.loads((root / B15_LOCK).read_text(encoding="utf-8"))
    b16s = _one_csv(root, B16_SUMMARY)
    b16d = _one_csv(root, B16_DECISION)
    b17 = _one_csv(root, B17_DECISION)
    b17t1 = _one_csv(root, B17T1_DECISION)

    # B12: preserve incomplete primary cohort and diagnostic-only available-case result.
    if str(b12p["primary_status"]) != "B12_PRIMARY_INCOMPLETE_OFFICIAL_OUTCOME_MATCH":
        raise AssertionError("B12 primary state changed.")
    if int(b12p["n_sealed_predictions"]) != 420 or int(b12p["n_officially_observable"]) != 387:
        raise AssertionError("B12 sealed/observable counts changed.")
    if int(b12p["n_missing_official_answer_keys"]) != 33:
        raise AssertionError("B12 missing-key count changed.")
    if _bool(b12p["primary_confirmatory_evaluable"]):
        raise AssertionError("B12 primary confirmatory status was inflated.")
    if _bool(b12p["available_case_diagnostic_confirmatory"]):
        raise AssertionError("B12 available-case diagnostic was inflated to confirmatory.")
    if _bool(b12p["selection_uses_outcome_value"]):
        raise AssertionError("B12 selection boundary changed.")
    if str(b12d["decision"]) != "B12_AVAILABLE_CASE_DIAGNOSTIC_90_CRITERION_NOT_MET":
        raise AssertionError("B12 diagnostic decision changed.")
    if _bool(b12d["confirmatory"]) or int(b12d["n_evaluated_available_cases"]) != 387:
        raise AssertionError("B12 available-case diagnostic status/count changed.")
    cov90 = b12cov[np.isclose(pd.to_numeric(b12cov["nominal"]), 0.90, atol=1e-12, rtol=0.0)]
    if len(cov90) != 1:
        raise AssertionError("B12 must contain exactly one 90% available-case coverage row.")
    b12cov90 = cov90.iloc[0]
    if not _close(b12cov90["environment_balanced_coverage"], 0.8487186682822535):
        raise AssertionError("B12 environment-balanced 90% coverage changed.")
    if _bool(b12cov90["confirmatory"]) or _bool(b12cov90["selection_uses_outcome_value"]):
        raise AssertionError("B12 90% coverage row violates diagnostic/selection boundary.")

    # B13: pre-outcome rule lock existed but 2023 could not be evaluated.
    if str(b13["stage_state"]) != "B13_PREOUTCOME_CALIBRATION_RULE_LOCKED":
        raise AssertionError("B13 protocol lock changed.")
    if not _close(b13["adaptive_quantile_level"], 0.9512813317177465):
        raise AssertionError("B13 adaptive level changed.")
    if str(b13a["decision"]) != "B13A_2023_T1_CONTEXT_INSUFFICIENT" or int(b13a["n_candidate_cells"]) != 0:
        raise AssertionError("B13A source-compatibility state changed.")
    if str(b13s["decision"]) != "B13S_2023_NO_ADMISSIBLE_PLANTING_DATE_RECOVERY":
        raise AssertionError("B13-S recovery state changed.")
    if int(b13s["n_admissible_planting_dates"]) != 0:
        raise AssertionError("B13-S unexpectedly recovered planting dates.")

    # B14: source-compatible -> sealed -> reveal, with no outcome-value cohort selection.
    if str(b14a["decision"]) != "B14A_2024_READY_FOR_PREOUTCOME_SEAL":
        raise AssertionError("B14A gate changed.")
    if int(b14a["n_candidate_cells"]) != 798 or int(b14a["n_candidate_environments"]) != 19:
        raise AssertionError("B14A candidate universe changed.")
    if str(b14b["decision"]) != "B14B_2024_SEALED_PREDICTIONS_READY_FOR_REVEAL":
        raise AssertionError("B14B seal decision changed.")
    if int(b14b["n_predictions"]) != 798 or _bool(b14b["observed_values_accessed"]):
        raise AssertionError("B14B seal boundary changed.")
    if str(b14cp["primary_estimand"]) != "OFFICIALLY_OBSERVABLE_SEALED_KEYS":
        raise AssertionError("B14C estimand changed.")
    if int(b14cp["n_officially_observable"]) != 779 or int(b14cp["n_sealed_keys_absent_from_official"]) != 19:
        raise AssertionError("B14C primary cohort changed.")
    if _bool(b14cp["selection_uses_outcome_value"]) or _bool(b14cp["post_reveal_protocol_amendment"]):
        raise AssertionError("B14C cohort/protocol integrity changed.")
    if not _close(b14cp["rmse"], 2.6197348508709113) or not _close(b14cp["correlation"], 0.390901094352944):
        raise AssertionError("B14C point metrics changed.")

    intervals = b14ci.set_index("rule")
    if set(intervals.index) != {"FROZEN_B11_90", "ONE_SIDED_CLUSTER_DRIFT_GUARD_90"}:
        raise AssertionError("B14C interval competitors changed.")
    c0 = intervals.loc["FROZEN_B11_90"]
    c1 = intervals.loc["ONE_SIDED_CLUSTER_DRIFT_GUARD_90"]
    if not _bool(c0["calibration_pass"]) or _bool(c1["calibration_pass"]):
        raise AssertionError("B14C control/adaptive pass state changed.")
    if not float(c0["mean_interval_score"]) < float(c1["mean_interval_score"]):
        raise AssertionError("B14C efficiency ordering changed.")
    if not _close(c0["environment_balanced_coverage"], 0.8997721030003023):
        raise AssertionError("B14C C0 environment-balanced coverage changed.")
    if not _close(c1["environment_balanced_coverage"], 0.9521031534328204):
        raise AssertionError("B14C C1 environment-balanced coverage changed.")
    if not _bool(b14cd["control_calibration_pass"]) or _bool(b14cd["adaptive_calibration_pass"]):
        raise AssertionError("B14C authoritative booleans changed.")

    # B15: novelty closed after equivalence audit.
    if b15.get("status") != "CLOSED_AFTER_T1_PRIOR_ART_EQUIVALENCE":
        raise AssertionError("B15 closure state changed.")
    if b15.get("t1_decision") != "B15_T1_FEEDBACK_DECISION_NOVELTY_REJECTED_TERMINATE_B15":
        raise AssertionError("B15-T1 decision changed.")
    if b15.get("b15_closed") is not True or b15.get("b15_t2_permitted") is not False:
        raise AssertionError("B15 terminal routing changed.")

    # B16/B17: diagnostic and negative novelty stages only.
    if str(b16d["decision"]) != "B16_DIAGNOSTIC_COMPLETE_NO_MODEL_CHANGE":
        raise AssertionError("B16 decision changed.")
    if _bool(b16d["method_novelty_claim"]) or _bool(b16d["point_predictor_changed"]):
        raise AssertionError("B16 was improperly promoted.")
    if not _close(b16s["environment_bias_sse_fraction"], 0.4296201953688075):
        raise AssertionError("B16 environment SSE fraction changed.")
    if not _close(b16s["within_environment_sse_fraction"], 0.5703798046311924):
        raise AssertionError("B16 within-environment SSE fraction changed.")
    if not _close(b16s["median_predicted_to_observed_sd_ratio"], 0.2882996096719246):
        raise AssertionError("B16 dispersion ratio changed.")
    if str(b17["decision"]) != "B17_BROAD_RESPONSE_AMPLITUDE_NOVELTY_REJECTED_OPEN_ARCHITECTURE_CONTRACTION_TEST":
        raise AssertionError("B17 decision changed.")
    if _bool(b17["broad_response_amplitude_method_novelty"]):
        raise AssertionError("B17 novelty was inflated.")
    if str(b17t1["decision"]) != "B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_REJECTED_TERMINATE_B17":
        raise AssertionError("B17-T1 terminal decision changed.")
    if str(b17t1["research_branch_state"]) != "B17_CLOSED_NO_MODEL_MODIFICATION":
        raise AssertionError("B17 branch is not closed.")

    return {
        "b12p": b12p,
        "b12d": b12d,
        "b12cov90": b12cov90,
        "b13": b13,
        "b13a": b13a,
        "b13s": b13s,
        "b14a": b14a,
        "b14b": b14b,
        "b14cp": b14cp,
        "c0": c0,
        "c1": c1,
        "b15": b15,
        "b16s": b16s,
        "b17t1": b17t1,
    }


def stage_classification(e: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["B12_PRIMARY", "ABORTED_CONFIRMATORY_EXTERNAL_TEST", "NEGATIVE_DATA_COMPLETENESS", False,
             "420-row seal preserved; 33 sealed keys absent from official answer; confirmatory primary cohort not evaluable."],
            ["B12_AVAILABLE_CASE", "POST_REVEAL_DIAGNOSTIC", "NEGATIVE_CALIBRATION_TRANSPORT_SIGNAL", False,
             "387 observable sealed keys; 90% environment-balanced coverage 0.8487186683; inherited criterion not met."],
            ["B13", "PREOUTCOME_PROTOCOL_LOCK", "UNEVALUATED_2023_CALIBRATION_EXPERIMENT", False,
             "C0/C1 locked before any 2023 outcome; adaptive level fixed at 0.9512813317177465."],
            ["B13A", "SOURCE_COMPATIBILITY_GATE", "NEGATIVE_INFORMATION_INTERFACE_RESULT", False,
             "No explicit planting date in allow-listed 2023 pre-outcome sources; zero T1-feasible environments."],
            ["B13S", "PROVENANCE_RECOVERY_AUDIT", "NEGATIVE_INFORMATION_INTERFACE_RESULT", False,
             "Independent authoritative metadata still yielded zero admissible exact planting dates; 2023 path closed."],
            ["B14A", "SOURCE_COMPATIBILITY_GATE", "POSITIVE_PRESEAL_FEASIBILITY", False,
             "Frozen T1 reconstruction feasible for 19 environments; 798-cell candidate universe fixed without outcomes."],
            ["B14B", "BLINDED_PREOUTCOME_SEAL", "IMMUTABLE_EXTERNAL_PREDICTION_ARTIFACT", False,
             "798 predictions sealed before repository outcome access; predictor and uncertainty rules frozen."],
            ["B14C", "SEAL_FIRST_BLINDED_EXTERNAL_TEST", "CONFIRMATORY_EXTERNAL_EVALUATION", True,
             "779 officially observable sealed keys; point and interval metrics evaluated with no outcome-value selection or amendment."],
            ["B15_B15T1", "HOSTILE_THEORY_NOVELTY_AUDIT", "NEGATIVE_METHOD_NOVELTY_RESULT", False,
             "Calibration-transport and feedback-decision objects reduced to existing partial-identification/robust-decision theory."],
            ["B16", "POSTOUTCOME_DIAGNOSTIC", "SUPPORTED_MIXED_FAILURE_MECHANISM", False,
             "Outcome-closed decomposition: 42.96% environment-offset SSE and 57.04% centered within-environment SSE."],
            ["B17_B17T1", "HOSTILE_MECHANISM_NOVELTY_AUDIT", "NEGATIVE_METHOD_NOVELTY_WITH_STRUCTURAL_INTERPRETATION", False,
             "Response-amplitude novelty rejected; additive G+E contrast invariance is exact real-arithmetic no-interaction structure, not new theory."],
        ],
        columns=["stage", "evidence_class", "scientific_status", "confirmatory_external_anchor", "closure_interpretation"],
    )


def contribution_matrix(e: dict[str, object]) -> pd.DataFrame:
    b14cp = e["b14cp"]
    c0 = e["c0"]
    c1 = e["c1"]
    b16 = e["b16s"]
    rows = [
        {
            "candidate_contribution": "SEAL_FIRST_BLINDED_EXTERNAL_VALIDATION_DISCIPLINE",
            "support_status": "SUPPORTED_RESEARCH_DESIGN_AND_PROVENANCE_CONTRIBUTION",
            "generic_method_novelty": False,
            "publication_role": "PRIMARY",
            "evidence": "B12 seal preservation plus B14A/B14B/B14C source-gate -> seal -> reveal chain",
            "boundary": "Do not call the 2026 execution calendar-time prospective; 2024 outcomes were already public, but were not accessed before the seal.",
        },
        {
            "candidate_contribution": "EARLY_DECISION_TIME_INFORMATION_BOUNDARY_T1_30DAP",
            "support_status": "SUPPORTED_OPERATIONAL_EXPERIMENTAL_CONSTRAINT",
            "generic_method_novelty": False,
            "publication_role": "PRIMARY_CONTEXT",
            "evidence": "Frozen planting-through-30-DAP environmental state preserved across external source gates",
            "boundary": "Information-time discipline is a study design choice, not by itself a new GxE model.",
        },
        {
            "candidate_contribution": "TEMPORAL_INTERVAL_CALIBRATION_NONMONOTONICITY",
            "support_status": "SUPPORTED_B12_DIAGNOSTIC_PLUS_B14C_CONFIRMATORY",
            "generic_method_novelty": False,
            "publication_role": "PRIMARY_EMPIRICAL_RESULT",
            "evidence": (
                f"2022 diagnostic env-balanced 90% coverage={float(e['b12cov90']['environment_balanced_coverage']):.12f}; "
                f"2024 C0={float(c0['environment_balanced_coverage']):.12f}; C1={float(c1['environment_balanced_coverage']):.12f}"
            ),
            "boundary": "B12 is diagnostic because the 420-row confirmatory cohort was incomplete; do not present 2022 as a completed confirmatory failure.",
        },
        {
            "candidate_contribution": "ONE_SIDED_SEASON_FEEDBACK_GUARD",
            "support_status": "REJECTED_BY_2024_EXTERNAL_TEST",
            "generic_method_novelty": False,
            "publication_role": "PRIMARY_NEGATIVE_RESULT",
            "evidence": (
                f"C1 calibration_pass=False and interval_score={float(c1['mean_interval_score']):.6f} > "
                f"C0={float(c0['mean_interval_score']):.6f}"
            ),
            "boundary": "No post-hoc alternative feedback rule may be substituted into the B14C result.",
        },
        {
            "candidate_contribution": "SOURCE_INTERFACE_AS_DEPLOYABILITY_CONDITION",
            "support_status": "SUPPORTED_OPERATIONAL_SCIENCE",
            "generic_method_novelty": False,
            "publication_role": "SECONDARY",
            "evidence": "2023 T1 reconstruction impossible under authoritative pre-outcome sources; 2024 reconstruction feasible without changing the clock.",
            "boundary": "This is a provenance/information-interface finding, not model-performance evidence for 2023.",
        },
        {
            "candidate_contribution": "2024_POINT_PREDICTION_EXTERNAL_GENERALIZATION",
            "support_status": "SUPPORTED_MODEST_NONTRIVIAL_EXTERNAL_PERFORMANCE",
            "generic_method_novelty": False,
            "publication_role": "PRIMARY_EMPIRICAL_RESULT",
            "evidence": (
                f"n={int(b14cp['n_officially_observable'])}, RMSE={float(b14cp['rmse']):.6f}, "
                f"R2={float(b14cp['r2']):.6f}, Pearson={float(b14cp['correlation']):.6f}"
            ),
            "boundary": "Performance does not establish superiority to current interaction-capable GxE methods because no prospective locked challenger was tested in B14C.",
        },
        {
            "candidate_contribution": "MIXED_EXTERNAL_FAILURE_MECHANISM",
            "support_status": "SUPPORTED_DIAGNOSTICALLY",
            "generic_method_novelty": False,
            "publication_role": "MECHANISTIC_SUPPORT",
            "evidence": (
                f"environment SSE fraction={float(b16['environment_bias_sse_fraction']):.6f}; "
                f"within-environment fraction={float(b16['within_environment_sse_fraction']):.6f}; "
                f"median predicted/observed SD ratio={float(b16['median_predicted_to_observed_sd_ratio']):.6f}"
            ),
            "boundary": "B16 is postoutcome diagnosis, not a validated correction or new decomposition method.",
        },
        {
            "candidate_contribution": "ADDITIVE_G_PLUS_E_NO_INTERACTION_LIMITATION",
            "support_status": "SUPPORTED_STRUCTURAL_INTERPRETATION_PRIOR_ART",
            "generic_method_novelty": False,
            "publication_role": "MECHANISTIC_SUPPORT",
            "evidence": "Within-environment environmental main effect cancels from genotype contrasts; B17-T1 closes novelty.",
            "boundary": "Do not present additive contrast invariance, ridge shrinkage, PEV/CD or KRR leverage as new theory.",
        },
        {
            "candidate_contribution": "SUPPORT_BASED_ABSTENTION",
            "support_status": "NOT_EXTERNALLY_VALIDATED_AS_SELECTIVE_ERROR_MECHANISM",
            "generic_method_novelty": False,
            "publication_role": "LIMITATION",
            "evidence": "Observable B12/B14C cells remained supported; prior selective filtering did not establish useful error separation.",
            "boundary": "No claim that support abstention improves deployed risk without a new sealed experiment containing abstention cases.",
        },
        {
            "candidate_contribution": "NEW_CALIBRATION_TRANSPORT_OR_FEEDBACK_DECISION_METHOD",
            "support_status": "NOVELTY_REJECTED_B15",
            "generic_method_novelty": False,
            "publication_role": "EXCLUDED_CLAIM",
            "evidence": "B15 and B15-T1 terminated after prior-art equivalence.",
            "boundary": "Background lemmas may explain the problem; they are not method contributions.",
        },
        {
            "candidate_contribution": "NEW_RESPONSE_AMPLITUDE_OR_ARCHITECTURE_CONTRACTION_METHOD",
            "support_status": "NOVELTY_REJECTED_B17",
            "generic_method_novelty": False,
            "publication_role": "EXCLUDED_CLAIM",
            "evidence": "B17/B17-T1 terminate with no model modification.",
            "boundary": "Under-dispersion and no-interaction contraction are diagnostics/known structure, not a new methodology.",
        },
    ]
    return pd.DataFrame(rows)


def claim_ledger() -> pd.DataFrame:
    claims = [
        ("Seal-first blinded external validation of a frozen early-season G+E_T1 system on the public 2024 G2F release.", True, "PRIMARY_ALLOWED"),
        ("The 2024 evaluation was calendar-time prospective before outcomes became public.", False, "PROHIBITED_OVERCLAIM"),
        ("The 2022 420-cell confirmatory cohort failed calibration.", False, "PROHIBITED_B12_INFLATION"),
        ("The 2022 available-case cohort supplied negative diagnostic evidence for interval transport.", True, "ALLOWED_WITH_DIAGNOSTIC_LABEL"),
        ("The frozen B11 90% interval rule recovered admissible 2024 calibration while the carried-forward one-sided guard over-covered and was less efficient.", True, "PRIMARY_ALLOWED"),
        ("Calibration error evolves monotonically from season to season.", False, "CONTRADICTED_BY_CASE_STUDY_B"),
        ("The 2023 target season was unevaluable under the fixed T1 information interface without inventing a planting-date proxy.", True, "ALLOWED_SOURCE_INTERFACE_RESULT"),
        ("B16 establishes a new error-decomposition methodology.", False, "PROHIBITED_NOVELTY_INFLATION"),
        ("B16 shows that 2024 failure is mixed: environment offsets plus substantial within-environment error and under-dispersion.", True, "ALLOWED_DIAGNOSTIC_INTERPRETATION"),
        ("B17 establishes a new response-amplitude transport method.", False, "PROHIBITED_NOVELTY_INFLATION"),
        ("The additive G+E architecture cannot modulate genotype contrasts by environment in exact arithmetic.", True, "ALLOWED_STRUCTURAL_BACKGROUND"),
        ("Case Study B validates support-based abstention as a selective-risk mechanism.", False, "PROHIBITED_UNSUPPORTED_CLAIM"),
        ("Case Study B introduces a new state-of-the-art GxE predictive architecture.", False, "PROHIBITED_UNSUPPORTED_CLAIM"),
    ]
    return pd.DataFrame(claims, columns=["claim", "permitted", "claim_class"])


def literature_boundary() -> pd.DataFrame:
    rows = [
        ("10.1093/genetics/iyae195", "Washburn et al. 2025", "G2F prediction competition and diverse model strategies; test feedback was limited but not zero.", "Supports distinguishing our one-shot repository seal discipline from competition feedback, but does not create algorithmic novelty."),
        ("10.1186/s13104-026-07629-5", "Chen et al. 2026", "Official G2F 2024 competition resource; 2014-2023 training and 2024 test data, with observed values unavailable to participants during competition and now public.", "Forces accurate wording: our 2026 execution is blinded/seal-first relative to repository access, not calendar-time prospective."),
        ("10.1093/genetics/iyae171", "Hu et al. 2025", "MegaLMM extension predicts new environments using environmental covariates and latent factor loadings.", "Generic environment-conditioned GxE transport is occupied."),
        ("10.1093/genetics/iyae179", "Xavier et al. 2025", "Scalable latent/multivariate GxE covariance models including MegaLMM/MegaSEM/XFA/HCS.", "Complex interaction-capable GxE architecture is occupied."),
        ("10.1007/s00122-025-04865-4", "Avagyan et al. 2025", "Penalized factorial regression/reaction norms for GxE prediction.", "Genotype-specific environmental response slopes are occupied."),
        ("10.1007/s00122-025-05103-7", "Hrachov et al. 2026", "Regression frameworks for GxE and prediction into unseen environments.", "Unseen-environment reaction-norm/regression framing is occupied."),
        ("10.1007/s00122-026-05280-z", "Eckhoff et al. 2026", "ML/DNN target and loss engineering for within-environment genotype differences; MSED/shrinkage diagnostics.", "Response-amplitude/difference-shrinkage route is directly occupied."),
        ("10.1371/journal.pcbi.1013729", "Morshedian & Domaratzki 2026", "LSTM-attention GNN explicitly models GxE with a forward-time 2014-2021/2022 split.", "A B18 based merely on adding nonlinear GxE interactions or a forward-time split would not be novel."),
        ("10.1093/g3journal/jkab440", "Rogers et al. 2022", "Environment-specific maize genomic prediction with environmental covariates and environmental similarity.", "Environmental-similarity and main-effect G+E prediction are established."),
        ("10.1093/g3journal/jkad006", "Kick et al. 2023", "Deep learning integrates genetic, environment and management data with interaction layers and time-indexed weather.", "Multimodal interaction modeling is established; early post-planting weather importance is already studied."),
        ("10.1093/plphys/kiag344", "Adak et al. 2026", "Temporal phenomics/environment index plus genomic prediction across environments, with growth windows in days after planting.", "Decision-time/early-season environmental windows are not automatically novel; B18 needs a sharper hypothesis than truncating weather."),
    ]
    return pd.DataFrame(rows, columns=["doi", "primary_source", "occupied_or_contextual_space", "closure_implication"])


def b18_gate() -> pd.DataFrame:
    rows = [
        {
            "gate": "B18_AUTOMATIC_MODEL_DEVELOPMENT",
            "permitted": False,
            "reason": "Interaction-capable GxE models, reaction norms, latent-factor methods, deep multimodal models and GNNs already occupy the obvious repair space.",
        },
        {
            "gate": "B18_SEPARATE_HYPOTHESIS_AND_NOVELTY_AUDIT",
            "permitted": True,
            "reason": "A new branch may ask a sharply distinct question, but must survive primary-literature and identifiability audit before code/model fitting.",
        },
        {
            "gate": "B18_ACCEPTABLE_STARTING_QUESTION",
            "permitted": True,
            "reason": "Test whether enforcing a forecast-time information set changes the learnable GxE contrast operator and external ranking relative to full-season methods, without claiming that interaction modeling itself is new.",
        },
        {
            "gate": "B18_FORBIDDEN_STARTING_QUESTION_ADD_GXE",
            "permitted": False,
            "reason": "Adding GxE interactions after B17 is an obvious repair and is heavily covered by existing literature.",
        },
        {
            "gate": "B18_FORBIDDEN_STARTING_QUESTION_TUNE_2024_FAILURE",
            "permitted": False,
            "reason": "No B18 hypothesis may be tuned against B14C outcomes and then presented as prospective evidence.",
        },
    ]
    return pd.DataFrame(rows)


def run(output_root: Path) -> dict[str, Path]:
    root = Path(output_root)
    verify_lock(root)
    evidence = verify_evidence(root)

    stages = stage_classification(evidence)
    contributions = contribution_matrix(evidence)
    claims = claim_ledger()
    literature = literature_boundary()
    b18 = b18_gate()

    if stages["confirmatory_external_anchor"].sum() != 1:
        raise AssertionError("Closure must have exactly one completed confirmatory external anchor: B14C.")
    if contributions["generic_method_novelty"].astype(bool).any():
        raise AssertionError("Closure audit may not manufacture method novelty.")
    if claims.loc[claims["claim_class"].str.startswith("PROHIBITED"), "permitted"].any():
        raise AssertionError("A prohibited publication claim was marked permitted.")
    if b18.loc[b18["gate"].eq("B18_AUTOMATIC_MODEL_DEVELOPMENT"), "permitted"].iloc[0]:
        raise AssertionError("B18 model development cannot open automatically.")

    results = root / "reports" / "results"
    stages_path = results / "case_study_b_closure_stage_classification.csv"
    contributions_path = results / "case_study_b_contribution_matrix.csv"
    claims_path = results / "case_study_b_publication_claim_ledger.csv"
    literature_path = results / "case_study_b_literature_boundary.csv"
    b18_path = results / "case_study_b_b18_gate.csv"
    decision_path = results / "case_study_b_closure_decision.csv"

    stages.to_csv(stages_path, index=False)
    contributions.to_csv(contributions_path, index=False)
    claims.to_csv(claims_path, index=False)
    literature.to_csv(literature_path, index=False)
    b18.to_csv(b18_path, index=False)
    pd.DataFrame(
        [
            {
                "stage": "CASE_STUDY_B_CLOSURE_AND_SCIENTIFIC_CONTRIBUTION_AUDIT",
                "decision": CLOSURE_DECISION,
                "publication_frame": PUBLICATION_FRAME,
                "completed_confirmatory_external_anchor": "B14C_2024",
                "b12_primary_confirmatory_complete": False,
                "b14c_primary_n": 779,
                "b14c_rmse": float(evidence["b14cp"]["rmse"]),
                "b14c_r2": float(evidence["b14cp"]["r2"]),
                "b14c_correlation": float(evidence["b14cp"]["correlation"]),
                "b14c_control_calibration_pass": True,
                "b14c_adaptive_calibration_pass": False,
                "method_novelty_supported": False,
                "calendar_time_prospective_claim_permitted": False,
                "seal_first_blinded_external_validation_claim_permitted": True,
                "support_abstention_validated": False,
                "new_outcome_access": False,
                "new_prediction_generation": False,
                "point_predictor_changed": False,
                "interval_or_support_tuning": False,
                "t2_reopened": False,
                "post_result_tuning_permitted": False,
                "b18_automatic_model_development_permitted": False,
                "b18_separate_hypothesis_gate_permitted": True,
                "case_study_b_closed": True,
            }
        ]
    ).to_csv(decision_path, index=False)

    return {
        "stages": stages_path,
        "contributions": contributions_path,
        "claims": claims_path,
        "literature": literature_path,
        "b18": b18_path,
        "decision": decision_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    for name, path in paths.items():
        print(f"{name}: {path}")
    print(pd.read_csv(paths["decision"]).to_string(index=False))


if __name__ == "__main__":
    main()
