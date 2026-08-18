import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plant_intelligence.diagnostics.maize_b18_forecast_time_hypothesis import (
    TERMINAL_DECISION,
    architecture_information_decomposition,
    finite_bayes_squared_risk,
    formal_audit,
    genotype_contrast_ranking_witness,
    literature_boundary,
    nested_information_witness,
    run,
    verify_lock,
    verify_parent_closure,
)


ROOT = Path(__file__).resolve().parents[1]


def test_b18_lock_is_model_closed():
    lock = verify_lock(ROOT)
    assert lock["status"] == "LOCKED_BEFORE_MODEL_DEVELOPMENT"
    assert lock["predeclared_terminal_decision_if_any_kill_condition_holds"] == TERMINAL_DECISION
    for key in [
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
    ]:
        assert lock[key] is False


def test_parent_closure_authorizes_only_hypothesis_gate():
    verify_parent_closure(ROOT)
    closure = pd.read_csv(ROOT / "reports/results/case_study_b_closure_decision.csv").iloc[0]
    assert str(closure["b18_automatic_model_development_permitted"]).lower() == "false"
    assert str(closure["b18_separate_hypothesis_gate_permitted"]).lower() == "true"


def test_architecture_information_decomposition_is_exact():
    result = architecture_information_decomposition(10.0, 8.25, 6.0)
    assert np.isclose(result["capacity_gain_same_information"], 1.75)
    assert np.isclose(result["later_information_gain_same_architecture"], 2.25)
    assert np.isclose(result["total_additive_forecast_to_interaction_oracle_gap"], 4.0)
    assert abs(result["identity_residual"]) <= 1e-12


def test_architecture_information_decomposition_rejects_nonfinite():
    with pytest.raises(ValueError):
        architecture_information_decomposition(np.nan, 1.0, 0.0)


def test_nested_information_refinement_reduces_bayes_squared_risk():
    witness = nested_information_witness()
    assert witness["nested_risk_nonincreasing"] is True
    assert witness["strict_information_value_in_witness"] is True
    assert witness["forecast_bayes_risk"] > witness["partial_bayes_risk"] > witness["oracle_bayes_risk"]
    assert np.isclose(witness["oracle_bayes_risk"], 0.0)


def test_finite_bayes_risk_validates_probabilities():
    with pytest.raises(ValueError):
        finite_bayes_squared_risk([0.0, 1.0], [0.6, 0.6], ["a", "a"])


def test_later_information_can_change_genotype_ranking():
    witness = genotype_contrast_ranking_witness()
    assert np.isclose(witness["forecast_time_expected_contrast"].iloc[0], 1.0)
    assert witness["forecast_time_ranking"].eq("G1_GT_G2").all()
    assert witness["ranking_differs_from_forecast_time"].sum() == 1


def test_primary_literature_contains_direct_kill_collisions():
    literature = literature_boundary()
    assert literature["collision"].eq("DIRECT").sum() >= 3
    dois = set(literature["doi"])
    assert "10.1093/bioinformatics/btz197" in dois
    assert "10.1038/s41467-020-18480-y" in dois
    assert "10.1007/s00122-026-05280-z" in dois
    assert "10.1016/j.crm.2023.100541" in dois


def test_no_formal_object_is_promoted_to_novel_method():
    audit = formal_audit()
    assert audit["method_novelty"].astype(bool).sum() == 0
    assert "DIRECT_PRIOR_ART_COLLISION" in set(audit["status"])
    assert "BACKGROUND_IDENTITY_NOT_NOVEL" in set(audit["status"])
    assert "STANDARD_CONDITIONAL_EXPECTATION_LOGIC" in set(audit["status"])


def test_end_to_end_b18_audit_writes_terminal_no_model_decision(tmp_path):
    # Reuse immutable merged locks in a temporary repository-shaped root.
    for rel in [
        "reports/results/case_study_b18_hypothesis_lock.json",
        "reports/results/case_study_b_closure_decision.csv",
        "reports/results/case_study_b_b18_gate.csv",
    ]:
        src = ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

    outputs = run(tmp_path)
    decision = pd.read_csv(outputs["decision"]).iloc[0]
    assert decision["decision"] == TERMINAL_DECISION
    assert str(decision["method_novelty_supported"]).lower() == "false"
    assert str(decision["model_development_permitted"]).lower() == "false"
    assert str(decision["new_outcome_access"]).lower() == "false"
    assert str(decision["new_prediction_generation"]).lower() == "false"
    assert str(decision["post_result_tuning_permitted"]).lower() == "false"
    assert decision["next_action"] == "RETURN_TO_REPOSITORY_ROADMAP_OR_MANUSCRIPT_WITH_B18_RECORDED_AS_NEGATIVE_NOVELTY_AUDIT"
