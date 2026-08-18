"""B18-T0: forecast-time GxE novelty gate.

This stage is hypothesis-only. It verifies the merged Case Study B closure,
records the direct prior-art collisions found in the hostile audit, rejects broad
method novelty, and allows only a narrower information-parity benchmark kill
test. It does not read outcome-bearing artifacts, fit models, generate
predictions, or tune any component of the frozen Case Study B system.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

LOCK_REL = Path("reports/results/case_study_b18_t0_forecast_time_novelty_lock.json")
CLOSURE_DECISION_REL = Path("reports/results/case_study_b_closure_decision.csv")
B18_GATE_REL = Path("reports/results/case_study_b_b18_gate.csv")

DECISION = (
    "B18_T0_BROAD_FORECAST_TIME_GXE_NOVELTY_REJECTED_"
    "INFORMATION_PARITY_BENCHMARK_HYPOTHESIS_SURVIVES_KILL_TEST_ONLY"
)
NEXT_STAGE = "B18_T1_INFORMATION_PARITY_BENCHMARK_NOVELTY_TEST"


def _bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise ValueError(f"Cannot interpret boolean value {value!r}")


def verify_parent(root: Path) -> dict:
    lock = json.loads((root / LOCK_REL).read_text(encoding="utf-8"))
    if lock.get("status") != "LOCKED_BEFORE_PRIOR_ART_EQUIVALENCE_SYNTHESIS":
        raise ValueError("B18-T0 lock is missing or altered.")
    if lock.get("predeclared_decision") != DECISION:
        raise ValueError("B18-T0 decision differs from the locked decision.")
    if lock.get("next_stage_if_gate_valid") != NEXT_STAGE:
        raise ValueError("B18-T0 next-stage routing differs from the lock.")

    forbidden = [
        "new_outcome_access_permitted",
        "new_prediction_generation_permitted",
        "model_fitting_permitted",
        "hyperparameter_tuning_permitted",
        "point_predictor_change_permitted",
        "interaction_architecture_development_permitted",
        "b5_genotype_representation_change_permitted",
        "t1_clock_change_permitted",
        "t2_reopening_permitted",
        "interval_or_support_tuning_permitted",
        "reseal_permitted",
        "post_result_tuning_permitted",
        "b14c_performance_may_select_hypothesis",
        "b18_model_development_permitted_after_t0",
    ]
    if any(bool(lock.get(name, True)) for name in forbidden):
        raise ValueError("B18-T0 lock permits a forbidden operation.")

    closure = pd.read_csv(root / CLOSURE_DECISION_REL, low_memory=False)
    if len(closure) != 1:
        raise ValueError("B18-T0 expects one Case Study B closure decision row.")
    row = closure.iloc[0]
    if str(row["decision"]) != lock["parent_case_study_b_decision"]:
        raise ValueError("B18-T0 parent Case Study B closure decision changed.")
    if not _bool(row["case_study_b_closed"]):
        raise ValueError("B18-T0 requires Case Study B to remain closed.")
    if _bool(row["b18_automatic_model_development_permitted"]):
        raise ValueError("B18-T0 cannot run if automatic B18 model development is permitted.")
    if not _bool(row["b18_separate_hypothesis_gate_permitted"]):
        raise ValueError("B18-T0 requires the separate hypothesis gate to be permitted.")

    gate = pd.read_csv(root / B18_GATE_REL, low_memory=False).set_index("gate")
    if str(gate.loc["B18_SEPARATE_HYPOTHESIS_AND_NOVELTY_AUDIT", "permitted"]).lower() != "true":
        raise ValueError("Merged closure does not permit the B18 hypothesis gate.")
    if str(gate.loc["B18_AUTOMATIC_MODEL_DEVELOPMENT", "permitted"]).lower() != "false":
        raise ValueError("Merged closure unexpectedly permits automatic B18 model development.")
    return lock


def prior_art_matrix() -> pd.DataFrame:
    rows = [
        {
            "doi": "10.1093/bioinformatics/btz197",
            "year": 2019,
            "source": "Gillberg et al.",
            "tested_object": "FUTURE_GXE_WITHOUT_TARGET_SEASON_IN_SEASON_WEATHER",
            "direct_collision": True,
            "what_is_already_done": "New genotype, new location and new year prediction; in-season weather unavailable; historical weather used instead; compared interaction model against ideal in-season GxE, additive G+E, GE-BLUP and GBLUP.",
            "implication": "Broad claim that forecast-time information constraints create a new GxE prediction problem is rejected.",
        },
        {
            "doi": "10.1007/s00122-026-05280-z",
            "year": 2026,
            "source": "Eckhoff et al.",
            "tested_object": "FUTURE_YEAR_ENVIRONMENT_SPECIFIC_GENOTYPE_RANKING_FROM_HISTORICAL_WEATHER",
            "direct_collision": True,
            "what_is_already_done": "Historical weather used to infer future-year genotype rankings; future-year ranking improvement evaluated across GxE ML/DNN approaches.",
            "implication": "Future environment-specific ranking from forecast-available proxies is already occupied.",
        },
        {
            "doi": "10.3389/fpls.2020.01120",
            "year": 2020,
            "source": "Shahhosseini et al.",
            "tested_object": "PARTIAL_IN_SEASON_WEATHER_PREFIX_FORECASTING",
            "direct_collision": False,
            "what_is_already_done": "Corn yield forecasts compared complete in-season weather against partial knowledge at multiple calendar issue dates.",
            "implication": "Nested decision-time weather prefixes are established as a crop forecasting protocol even though the study is not genotype-specific GxE genomic prediction.",
        },
        {
            "doi": "10.1093/plphys/kiag344",
            "year": 2026,
            "source": "Adak et al.",
            "tested_object": "TEMPORAL_DAP_WINDOWS_IN_GENOMIC_PREDICTION_ACROSS_ENVIRONMENTS",
            "direct_collision": False,
            "what_is_already_done": "Temporal environmental and phenomic trajectories over days after planting are used to identify predictive windows and improve genomic prediction across environments.",
            "implication": "Using early/temporal DAP windows with genomic prediction is not itself novel; strict forecast-time locking would need to be the distinct contribution.",
        },
        {
            "doi": "10.1093/g3journal/jkad006",
            "year": 2023,
            "source": "Kick et al.",
            "tested_object": "DEEP_GENOMIC_ENVIRONMENT_MANAGEMENT_INTERACTIONS_WITH_TIME_INDEXED_WEATHER",
            "direct_collision": False,
            "what_is_already_done": "Deep models integrate genomic, soil, weather and management time series with interaction layers; salient post-planting time points are analyzed.",
            "implication": "A B18 based merely on a nonlinear interaction architecture or time-indexed weather is not novel.",
        },
        {
            "doi": "10.1093/bib/bbaf414",
            "year": 2025,
            "source": "EXGEP",
            "tested_object": "EXPLAINABLE_ENSEMBLE_GXE_WITH_G2F_FULL_SEASON_ENVIRONMENTAL_FEATURES",
            "direct_collision": False,
            "what_is_already_done": "G2F genotype and environmental features are integrated through explainable ensemble ML; weather is summarized across planting-to-harvest.",
            "implication": "The obvious ensemble/ML GxE repair space is occupied and often uses information that would be unavailable at an early decision time.",
        },
        {
            "doi": "10.1371/journal.pcbi.1013729",
            "year": 2026,
            "source": "Morshedian and Domaratzki",
            "tested_object": "LSTM_ATTENTION_GRAPH_GXE_FORWARD_TIME_EVALUATION",
            "direct_collision": False,
            "what_is_already_done": "Interaction-capable graph/recurrent models are evaluated under a forward-time train/test split.",
            "implication": "Forward-time splitting plus GNN/LSTM architecture is not a novelty route.",
        },
    ]
    return pd.DataFrame(rows)


def next_gate_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "gate": "B18_BROAD_FORECAST_TIME_GXE_METHOD_NOVELTY",
                "permitted": False,
                "reason": "Directly occupied by Gillberg et al. 2019 and reinforced by future-year ranking work in 2026.",
            },
            {
                "gate": "B18_ADD_INTERACTION_ARCHITECTURE",
                "permitted": False,
                "reason": "Interaction-capable GxE architectures are heavily occupied and Case Study B closure explicitly forbids this as a starting claim.",
            },
            {
                "gate": "B18_PARTIAL_WEATHER_PREFIX_IS_NOVEL_BY_ITSELF",
                "permitted": False,
                "reason": "Issue-date/partial-weather crop forecasting and DAP-window prediction are established outside and inside crop prediction literature.",
            },
            {
                "gate": "B18_INFORMATION_PARITY_BENCHMARK_HYPOTHESIS",
                "permitted": True,
                "reason": "A narrower question remains uneliminated: compare multiple GxE model classes under identical nested decision-time information sets and test ranking/contrast instability. This is benchmark/protocol novelty only and remains unestablished.",
            },
            {
                "gate": "B18_MODEL_FITTING_AFTER_T0",
                "permitted": False,
                "reason": "B18-T1 must first determine whether the information-parity benchmark itself is already present in primary GxE literature.",
            },
        ]
    )


def run(output_root: Path) -> dict[str, Path]:
    root = Path(output_root)
    lock = verify_parent(root)
    prior = prior_art_matrix()
    if not prior["direct_collision"].any():
        raise AssertionError("B18-T0 requires at least one direct prior-art collision for the broad hypothesis.")
    if not bool(prior.loc[prior["doi"].eq("10.1093/bioinformatics/btz197"), "direct_collision"].iloc[0]):
        raise AssertionError("Gillberg et al. 2019 must remain a direct collision.")

    next_gate = next_gate_matrix()
    if str(next_gate.loc[next_gate["gate"].eq("B18_MODEL_FITTING_AFTER_T0"), "permitted"].iloc[0]).lower() != "false":
        raise AssertionError("B18-T0 cannot permit model fitting.")

    results = root / "reports" / "results"
    prior_path = results / "case_study_b18_t0_prior_art_matrix.csv"
    gate_path = results / "case_study_b18_t0_next_gate.csv"
    decision_path = results / "case_study_b18_t0_decision.csv"
    prior.to_csv(prior_path, index=False)
    next_gate.to_csv(gate_path, index=False)
    pd.DataFrame(
        [
            {
                "stage": "B18_T0_FORECAST_TIME_GXE_NOVELTY_GATE",
                "decision": DECISION,
                "broad_forecast_time_gxe_method_novelty_supported": False,
                "information_parity_benchmark_hypothesis_novelty_established": False,
                "information_parity_benchmark_hypothesis_may_enter_t1_kill_test": True,
                "new_outcome_access": False,
                "new_prediction_generation": False,
                "model_fitting": False,
                "hyperparameter_tuning": False,
                "point_predictor_changed": False,
                "interaction_architecture_developed": False,
                "b14c_performance_used_to_select_hypothesis": False,
                "b18_model_development_permitted": False,
                "next_stage": NEXT_STAGE,
                "kill_condition": lock["kill_condition_for_t1"],
            }
        ]
    ).to_csv(decision_path, index=False)
    return {"prior_art": prior_path, "next_gate": gate_path, "decision": decision_path}


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
