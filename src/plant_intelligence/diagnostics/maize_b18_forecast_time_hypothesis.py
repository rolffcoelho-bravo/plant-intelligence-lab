"""B18 forecast-time information hypothesis and hostile novelty audit.

B18 is theory/audit only. It does not fit a model, generate predictions, access a
new outcome, reopen T2, change the frozen B5 genomic representation, alter the
T1_30DAP clock, tune uncertainty/support rules, or use B14C outcomes to select a
new architecture.

The candidate question inherited from the Case Study B closure asks whether a
forecast-time information restriction can create a distinct scientific object
separating interaction capacity from later-season information availability.
The executable audit deliberately kills the branch if that object is already
covered by prior GxE work under unavailable/uncertain future weather or if the
mathematical decomposition reduces to standard risk/conditional-expectation
logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

LOCK_REL = Path("reports/results/case_study_b18_hypothesis_lock.json")
PARENT_CLOSURE_REL = Path("reports/results/case_study_b_closure_decision.csv")
PARENT_B18_GATE_REL = Path("reports/results/case_study_b_b18_gate.csv")

TERMINAL_DECISION = "B18_FORECAST_TIME_INFORMATION_NOVELTY_REJECTED_NO_MODEL_DEVELOPMENT"


def _as_bool(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Cannot interpret boolean value {value!r}")


def verify_lock(root: Path) -> dict:
    lock = json.loads((root / LOCK_REL).read_text(encoding="utf-8"))
    if lock.get("status") != "LOCKED_BEFORE_MODEL_DEVELOPMENT":
        raise ValueError("B18 hypothesis lock is missing or altered.")
    if lock.get("predeclared_terminal_decision_if_any_kill_condition_holds") != TERMINAL_DECISION:
        raise ValueError("B18 terminal kill decision differs from the predeclared lock.")
    forbidden = [
        "new_outcome_access_permitted",
        "new_prediction_generation_permitted",
        "model_fitting_permitted",
        "hyperparameter_search_permitted",
        "point_predictor_change_permitted",
        "b5_genotype_representation_change_permitted",
        "t1_clock_change_permitted",
        "t2_reopening_permitted",
        "interval_or_support_tuning_permitted",
        "reseal_permitted",
        "post_result_tuning_permitted",
    ]
    if any(bool(lock.get(name, True)) for name in forbidden):
        raise ValueError("B18 lock permits a forbidden model/data operation.")
    if lock.get("novelty_must_survive_primary_literature_before_model_code") is not True:
        raise ValueError("B18 novelty-before-code requirement is not locked.")
    return lock


def verify_parent_closure(root: Path) -> None:
    closure = pd.read_csv(root / PARENT_CLOSURE_REL, low_memory=False)
    if len(closure) != 1:
        raise ValueError("Expected exactly one Case Study B closure decision row.")
    row = closure.iloc[0]
    expected = (
        "CASE_STUDY_B_CLOSED_EXTERNAL_VALIDATION_CONTRIBUTION_SUPPORTED_"
        "METHOD_NOVELTY_NOT_SUPPORTED_B18_SEPARATE_HYPOTHESIS_GATE_ONLY"
    )
    if str(row["decision"]) != expected:
        raise AssertionError("B18 parent closure decision changed.")
    if not _as_bool(row["case_study_b_closed"]):
        raise AssertionError("Case Study B is not closed in the parent decision.")
    if _as_bool(row["b18_automatic_model_development_permitted"]):
        raise AssertionError("Parent closure unexpectedly permits automatic B18 model development.")
    if not _as_bool(row["b18_separate_hypothesis_gate_permitted"]):
        raise AssertionError("Parent closure does not permit the B18 hypothesis gate.")

    gate = pd.read_csv(root / PARENT_B18_GATE_REL, low_memory=False).set_index("gate")
    if _as_bool(gate.loc["B18_AUTOMATIC_MODEL_DEVELOPMENT", "permitted"]):
        raise AssertionError("Merged B18 gate permits automatic model development.")
    if not _as_bool(gate.loc["B18_SEPARATE_HYPOTHESIS_AND_NOVELTY_AUDIT", "permitted"]):
        raise AssertionError("Merged B18 gate does not authorize this audit.")


def architecture_information_decomposition(
    additive_forecast_risk: float,
    interaction_forecast_risk: float,
    interaction_oracle_risk: float,
) -> dict[str, float]:
    """Exact telescoping decomposition of risk differences.

    R(A0,F_t)-R(A1,F_T)
      = [R(A0,F_t)-R(A1,F_t)] + [R(A1,F_t)-R(A1,F_T)].

    The first term is an architecture-capacity contrast at the same admissible
    forecast-time information set. The second is an information/oracle contrast
    holding the interaction-capable architecture fixed. This identity is useful
    for experimental design but is not claimed as new mathematics.
    """

    values = np.asarray(
        [additive_forecast_risk, interaction_forecast_risk, interaction_oracle_risk],
        dtype=float,
    )
    if not np.isfinite(values).all():
        raise ValueError("Risks must be finite.")
    capacity_gain = float(additive_forecast_risk - interaction_forecast_risk)
    later_information_gain = float(interaction_forecast_risk - interaction_oracle_risk)
    total_gap = float(additive_forecast_risk - interaction_oracle_risk)
    residual = float(total_gap - capacity_gain - later_information_gain)
    return {
        "capacity_gain_same_information": capacity_gain,
        "later_information_gain_same_architecture": later_information_gain,
        "total_additive_forecast_to_interaction_oracle_gap": total_gap,
        "identity_residual": residual,
    }


def finite_bayes_squared_risk(
    outcomes: Sequence[float],
    probabilities: Sequence[float],
    information_labels: Sequence[object],
) -> float:
    """Bayes squared-error risk for a finite information partition.

    The Bayes predictor in each information cell is its conditional mean. This is
    an executable witness for the standard fact that refining the information
    set cannot increase Bayes squared-error risk.
    """

    y = np.asarray(outcomes, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    labels = np.asarray(information_labels, dtype=object)
    if not (len(y) == len(p) == len(labels)) or len(y) == 0:
        raise ValueError("Outcomes, probabilities and information labels must align and be nonempty.")
    if len(y) == 0:
        raise ValueError("Finite witness must contain at least one state.")
    if not np.isfinite(y).all() or not np.isfinite(p).all() or (p < 0).any():
        raise ValueError("Finite witness contains invalid values.")
    total_p = float(p.sum())
    if not np.isclose(total_p, 1.0, atol=1e-12, rtol=0.0):
        raise ValueError("Probabilities must sum to one.")

    risk = 0.0
    for label in dict.fromkeys(labels.tolist()):
        mask = labels == label
        mass = float(p[mask].sum())
        if mass <= 0.0:
            continue
        mean = float(np.sum(p[mask] * y[mask]) / mass)
        risk += float(np.sum(p[mask] * np.square(y[mask] - mean)))
    return risk


def nested_information_witness() -> dict[str, float | bool]:
    """Return a finite strict refinement witness under squared loss."""

    outcomes = [0.0, 2.0, 8.0, 10.0]
    probabilities = [0.25, 0.25, 0.25, 0.25]
    forecast_labels = ["coarse", "coarse", "coarse", "coarse"]
    partial_labels = ["low", "low", "high", "high"]
    oracle_labels = ["s0", "s1", "s2", "s3"]

    forecast = finite_bayes_squared_risk(outcomes, probabilities, forecast_labels)
    partial = finite_bayes_squared_risk(outcomes, probabilities, partial_labels)
    oracle = finite_bayes_squared_risk(outcomes, probabilities, oracle_labels)
    return {
        "forecast_bayes_risk": forecast,
        "partial_bayes_risk": partial,
        "oracle_bayes_risk": oracle,
        "nested_risk_nonincreasing": bool(forecast >= partial >= oracle),
        "strict_information_value_in_witness": bool(forecast > partial > oracle),
    }


def genotype_contrast_ranking_witness() -> pd.DataFrame:
    """Finite witness that later information can change a genotype ranking.

    The forecast-time conditional mean contrast is positive, while one possible
    later state has a negative contrast. This demonstrates why later information
    can change rankings, not a novel identification theorem.
    """

    frame = pd.DataFrame(
        {
            "late_state": ["S0", "S1"],
            "probability": [0.5, 0.5],
            "genotype_contrast_g1_minus_g2": [-2.0, 4.0],
        }
    )
    expected = float(
        np.sum(frame["probability"] * frame["genotype_contrast_g1_minus_g2"])
    )
    frame["forecast_time_expected_contrast"] = expected
    frame["forecast_time_ranking"] = "G1_GT_G2" if expected > 0 else "G2_GT_G1"
    frame["late_state_ranking"] = np.where(
        frame["genotype_contrast_g1_minus_g2"] > 0,
        "G1_GT_G2",
        "G2_GT_G1",
    )
    frame["ranking_differs_from_forecast_time"] = (
        frame["late_state_ranking"] != frame["forecast_time_ranking"]
    )
    return frame


def literature_boundary() -> pd.DataFrame:
    """Primary-source hostile-audit map frozen for the B18 gate."""

    rows = [
        {
            "doi": "10.1093/bioinformatics/btz197",
            "source": "Gillberg et al. 2019",
            "collision": "DIRECT",
            "occupied_space": "GxE prediction for genuinely new years, locations and genotypes without in-season weather; historical weather replaces unavailable target-season covariates; realistic historical-weather and non-realistic in-season/oracle settings are explicitly compared.",
            "kill_condition": "DIRECT_PRIOR_ART_COMPARES_DECISION_TIME_LEGAL_ENVIRONMENTAL_INFORMATION_WITH_IN_SEASON_ORACLE_INFORMATION_FOR_GXE_PREDICTION",
        },
        {
            "doi": "10.1038/s41467-020-18480-y",
            "source": "de los Campos et al. 2020",
            "collision": "DIRECT",
            "occupied_space": "GxE cultivar-performance prediction under uncertain future weather using field trials, DNA, historical weather and Monte Carlo integration over future-weather/model uncertainty.",
            "kill_condition": "DIRECT_PRIOR_ART_MODELS_FUTURE_CULTIVAR_PERFORMANCE_UNDER_UNCERTAIN_WEATHER",
        },
        {
            "doi": "10.1007/s00122-026-05280-z",
            "source": "Eckhoff et al. 2026",
            "collision": "DIRECT",
            "occupied_space": "Future-year GxE genotype ranking when actual target-year weather is unavailable at decision time; historical weather is used as a proxy, with within-environment genotype-difference objectives.",
            "kill_condition": "DIRECT_PRIOR_ART_USES_WEATHER_FORECASTS_OR_HISTORICAL_WEATHER_FOR_VARIETY_SELECTION_OR_RANKING",
        },
        {
            "doi": "10.1007/s10669-018-9695-4",
            "source": "Zhong et al. 2018",
            "collision": "ADJACENT_DECISION_THEORY",
            "occupied_space": "Risk-sensitive seed-variety yield modeling and future planting decisions under weather uncertainty.",
            "kill_condition": "NARROWER_DECISION_VALUE_ROUTE_REDUCES_TO_EXISTING_VALUE_OF_INFORMATION_OR_RISK_SENSITIVE_CULTIVAR_SELECTION",
        },
        {
            "doi": "10.1016/j.crm.2023.100541",
            "source": "Kayamo et al. 2023",
            "collision": "ADJACENT_DECISION_THEORY",
            "occupied_space": "Value-of-information analysis for seasonal-forecast-based cultivar choice.",
            "kill_condition": "NARROWER_DECISION_VALUE_ROUTE_REDUCES_TO_EXISTING_VALUE_OF_INFORMATION_OR_RISK_SENSITIVE_CULTIVAR_SELECTION",
        },
        {
            "doi": "10.1371/journal.pcbi.1013729",
            "source": "Morshedian and Domaratzki 2026",
            "collision": "ARCHITECTURE_PRIOR_ART",
            "occupied_space": "Interaction-capable LSTM-attention GNN for maize GxE with forward-time evaluation on unseen genotypes and environments.",
            "kill_condition": "OBVIOUS_INTERACTION_ARCHITECTURE_ROUTE_ALREADY_OCCUPIED",
        },
        {
            "doi": "10.1016/j.fcr.2026.110593",
            "source": "Li et al. 2026",
            "collision": "ARCHITECTURE_AND_TEMPORAL_CONTEXT",
            "occupied_space": "Cultivar-specific crop-climate fusion with phenology-aligned climate factors and nonlinear ML across environments.",
            "kill_condition": "OBVIOUS_CROP_CLIMATE_FUSION_ROUTE_ALREADY_OCCUPIED",
        },
    ]
    return pd.DataFrame(rows)


def formal_audit() -> pd.DataFrame:
    witness = nested_information_witness()
    decomposition = architecture_information_decomposition(10.0, 8.0, 6.0)
    ranking = genotype_contrast_ranking_witness()
    rows = [
        {
            "object": "ARCHITECTURE_INFORMATION_RISK_TELESCOPING",
            "status": "BACKGROUND_IDENTITY_NOT_NOVEL",
            "method_novelty": False,
            "reason": "Exact difference-of-risks telescoping separates same-information architecture capacity from same-architecture extra information, but introduces no new statistical object.",
            "executable_witness": f"identity_residual={decomposition['identity_residual']}",
        },
        {
            "object": "NESTED_INFORMATION_BAYES_RISK",
            "status": "STANDARD_CONDITIONAL_EXPECTATION_LOGIC",
            "method_novelty": False,
            "reason": "Under squared loss, conditional expectation is the Bayes predictor and a refined information set cannot worsen Bayes risk.",
            "executable_witness": (
                f"coarse={witness['forecast_bayes_risk']};partial={witness['partial_bayes_risk']};"
                f"oracle={witness['oracle_bayes_risk']}"
            ),
        },
        {
            "object": "FORECAST_TIME_VS_LATE_INFORMATION_GENOTYPE_RANKING",
            "status": "USEFUL_WITNESS_NOT_NOVEL_THEOREM",
            "method_novelty": False,
            "reason": "A future environmental state can reverse a genotype contrast relative to its forecast-time conditional mean; this is ordinary state-contingent decision/prediction logic.",
            "executable_witness": f"ranking_reversals={int(ranking['ranking_differs_from_forecast_time'].sum())}",
        },
        {
            "object": "FORECAST_TIME_GXE_PREDICTION_WITHOUT_IN_SEASON_WEATHER",
            "status": "DIRECT_PRIOR_ART_COLLISION",
            "method_novelty": False,
            "reason": "Gillberg et al. directly impose the missing-in-season-weather constraint and compare realistic historical-weather GxE to an in-season ideal/oracle setting.",
            "executable_witness": "10.1093/bioinformatics/btz197",
        },
        {
            "object": "FUTURE_PERFORMANCE_UNDER_WEATHER_UNCERTAINTY",
            "status": "DIRECT_PRIOR_ART_COLLISION",
            "method_novelty": False,
            "reason": "de los Campos et al. integrate GxE, historical weather and future-weather uncertainty for cultivar performance distributions.",
            "executable_witness": "10.1038/s41467-020-18480-y",
        },
        {
            "object": "FORECAST_INFORMATION_VALUE_FOR_CULTIVAR_DECISION",
            "status": "VALUE_OF_INFORMATION_TERRITORY_OCCUPIED",
            "method_novelty": False,
            "reason": "Seasonal forecast value for cultivar choice and risk-sensitive seed-variety decisions already occupy the obvious decision-value extension.",
            "executable_witness": "10.1016/j.crm.2023.100541",
        },
    ]
    return pd.DataFrame(rows)


def decision_frame(literature: pd.DataFrame, formal: pd.DataFrame) -> pd.DataFrame:
    direct_collisions = int(literature["collision"].eq("DIRECT").sum())
    surviving_novel_objects = int(formal["method_novelty"].astype(bool).sum())
    kill_condition_triggered = direct_collisions > 0 or surviving_novel_objects == 0
    if not kill_condition_triggered:
        raise AssertionError("B18 kill test unexpectedly survived; audit logic must be revisited before model work.")
    return pd.DataFrame(
        [
            {
                "stage": "B18_FORECAST_TIME_INFORMATION_HYPOTHESIS_AUDIT",
                "decision": TERMINAL_DECISION,
                "direct_primary_prior_art_collisions": direct_collisions,
                "surviving_novel_formal_objects": surviving_novel_objects,
                "architecture_information_decomposition_novel": False,
                "nested_information_risk_theorem_novel": False,
                "forecast_time_gxe_problem_novel": False,
                "forecast_value_cultivar_decision_problem_novel": False,
                "method_novelty_supported": False,
                "model_development_permitted": False,
                "new_outcome_access": False,
                "new_prediction_generation": False,
                "model_fitting": False,
                "hyperparameter_search": False,
                "point_predictor_changed": False,
                "b5_genotype_representation_changed": False,
                "t1_clock_changed": False,
                "t2_reopened": False,
                "interval_or_support_tuning": False,
                "reseal": False,
                "post_result_tuning_permitted": False,
                "next_action": "RETURN_TO_REPOSITORY_ROADMAP_OR_MANUSCRIPT_WITH_B18_RECORDED_AS_NEGATIVE_NOVELTY_AUDIT",
            }
        ]
    )


def run(output_root: Path) -> dict[str, Path]:
    root = Path(output_root)
    verify_lock(root)
    verify_parent_closure(root)

    literature = literature_boundary()
    formal = formal_audit()
    ranking = genotype_contrast_ranking_witness()
    decision = decision_frame(literature, formal)

    if not literature["collision"].eq("DIRECT").any():
        raise AssertionError("B18 hostile audit lost its direct prior-art collision.")
    if formal["method_novelty"].astype(bool).any():
        raise AssertionError("B18 formal audit improperly manufactures novelty.")
    if not nested_information_witness()["strict_information_value_in_witness"]:
        raise AssertionError("Nested-information witness is not strict.")

    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)
    formal_path = results / "case_study_b18_formal_audit.csv"
    literature_path = results / "case_study_b18_literature_boundary.csv"
    ranking_path = results / "case_study_b18_ranking_witness.csv"
    decision_path = results / "case_study_b18_decision.csv"

    formal.to_csv(formal_path, index=False)
    literature.to_csv(literature_path, index=False)
    ranking.to_csv(ranking_path, index=False)
    decision.to_csv(decision_path, index=False)
    return {
        "formal": formal_path,
        "literature": literature_path,
        "ranking": ranking_path,
        "decision": decision_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    outputs = run(args.output_root)
    for key, path in outputs.items():
        print(f"{key}: {path}")
    print(pd.read_csv(outputs["decision"]).to_string(index=False))


if __name__ == "__main__":
    main()
