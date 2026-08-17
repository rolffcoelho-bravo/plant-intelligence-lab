from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plant_intelligence.uncertainty import maize_b13_sequential_drift_calibration as b13


def test_recency_envelope_never_narrows(monkeypatch):
    def fake_quantiles(historical, support_state):
        return {
            80: (1.0, "LOCKED"),
            90: (2.0, "LOCKED"),
            95: (3.0, "LOCKED"),
        }

    monkeypatch.setattr(b13.b12, "_quantiles", fake_quantiles)
    historical = pd.DataFrame(
        {
            "absolute_error": [0.5, 1.0, 2.0],
            "test_year": [2019, 2020, 2021],
            "environment": ["A", "B", "C"],
        }
    )
    recent = pd.DataFrame(
        {
            "absolute_error": [0.2, 1.2, 2.4, 4.5, 6.0],
            "environment": ["R1", "R1", "R2", "R2", "R3"],
        }
    )

    policy = b13.construct_drift_policy(historical, recent)

    assert len(policy) == 6
    assert policy["adaptive_never_narrows"].all()
    assert (policy["adaptive_half_width"] >= policy["baseline_half_width"]).all()
    assert not policy["target_outcomes_accessed"].any()
    assert not policy["predictive_model_refit"].any()
    assert not policy["t2_branch_reopened"].any()


def test_outcome_free_roster_is_cartesian_and_blind():
    roster = b13.build_outcome_free_roster(["G2", "G1"], ["E2", "E1"])
    assert len(roster) == 4
    assert set(map(tuple, roster[["genotype", "environment"]].to_numpy())) == {
        ("G1", "E1"),
        ("G1", "E2"),
        ("G2", "E1"),
        ("G2", "E2"),
    }
    assert not roster["target_outcomes_used_to_construct_roster"].any()


def test_predeclared_cohort_depends_on_finite_key_presence_not_yield_magnitude():
    predictions = pd.DataFrame(
        {
            "genotype": ["G1", "G2", "G3"],
            "environment": ["E_2023", "E_2023", "E_2023"],
            "predicted": [1.0, 2.0, 3.0],
        }
    )
    trait_a = pd.DataFrame(
        {
            "Env": ["E_2023", "E_2023", "E_2023", "E_2023"],
            "Hybrid": ["G1", "G1", "G2", "G3"],
            "Yield_Mg_ha": [1.0, 3.0, 5.0, np.nan],
        }
    )
    trait_b = trait_a.copy()
    trait_b["Yield_Mg_ha"] = [1000.0, -900.0, 777.0, np.nan]

    outcomes_a = b13.aggregate_target_outcomes(trait_a)
    outcomes_b = b13.aggregate_target_outcomes(trait_b)
    cohort_a = b13.predeclared_evaluation_cohort(predictions, outcomes_a)
    cohort_b = b13.predeclared_evaluation_cohort(predictions, outcomes_b)

    assert set(map(tuple, cohort_a[["genotype", "environment"]].to_numpy())) == {
        ("G1", "E_2023"),
        ("G2", "E_2023"),
    }
    assert set(map(tuple, cohort_b[["genotype", "environment"]].to_numpy())) == set(
        map(tuple, cohort_a[["genotype", "environment"]].to_numpy())
    )
    assert outcomes_a.loc[outcomes_a["genotype"].eq("G1"), "observed"].iloc[0] == 2.0
    assert not cohort_a["selection_uses_outcome_magnitude"].any()
    assert cohort_a["selection_uses_outcome_availability"].all()


def test_stage_a_blind_guard_rejects_target_trait_file(tmp_path: Path):
    forbidden = tmp_path / b13.TARGET_TRAIT_BASENAME
    forbidden.write_text("Env,Hybrid,Yield\n", encoding="utf-8")
    with pytest.raises(b13.B13ProtocolViolation):
        b13.assert_target_blind([tmp_path])


def test_prediction_and_policy_seal_detect_tampering(tmp_path: Path):
    policy = pd.DataFrame(
        [
            {
                "schema": b13.POLICY_SCHEMA,
                "support_group": b13.SUPPORT_WITHIN,
                "nominal": 0.90,
                "baseline_half_width": 2.0,
                "adaptive_half_width": 2.5,
            }
        ]
    )
    policy_path = tmp_path / "policy.csv"
    policy.to_csv(policy_path, index=False)

    predictions = pd.DataFrame(
        {
            "genotype": ["G1"],
            "environment": ["E1_2023"],
            "predicted": [10.0],
            "reliability_state": [b13.RETAIN],
            "b11_lower_90": [8.0],
            "b11_upper_90": [12.0],
            "b13_lower_90": [7.5],
            "b13_upper_90": [12.5],
        }
    )
    prediction_path = tmp_path / "predictions.csv"
    seal_path = tmp_path / "seal.json"
    b13.write_prediction_seal(
        predictions,
        prediction_path,
        seal_path,
        policy_path,
        {},
    )
    verified = b13.verify_prediction_seal(
        prediction_path,
        seal_path,
        policy_path,
    )
    assert verified["target_outcomes_accessed"] is False

    prediction_path.write_text(
        prediction_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(b13.B13ProtocolViolation):
        b13.verify_prediction_seal(prediction_path, seal_path, policy_path)


def _decision_frame(baseline_cov, adaptive_cov, low=0.87, high=0.93):
    return pd.DataFrame(
        [
            {
                "method": b13.BASELINE_METHOD,
                "nominal": 0.90,
                "empirical_coverage": baseline_cov,
                "environment_cluster_ci95_low": low,
                "environment_cluster_ci95_high": high,
            },
            {
                "method": b13.ADAPTIVE_METHOD,
                "nominal": 0.90,
                "empirical_coverage": adaptive_cov,
                "environment_cluster_ci95_low": low,
                "environment_cluster_ci95_high": high,
            },
        ]
    )


def test_b13_decision_states_are_predeclared():
    assert (
        b13.b13_decision(_decision_frame(0.85, 0.90), 200, 10)
        == "B13_DRIFT_ADAPTATION_RESTORES_90_CALIBRATION"
    )
    assert (
        b13.b13_decision(_decision_frame(0.89, 0.90), 200, 10)
        == "B13_BOTH_INTERVAL_RULES_PASS_90_CALIBRATION"
    )
    assert (
        b13.b13_decision(_decision_frame(0.90, 0.85), 200, 10)
        == "B13_DRIFT_ADAPTATION_DEGRADES_90_CALIBRATION"
    )
    assert (
        b13.b13_decision(_decision_frame(0.84, 0.85), 200, 10)
        == "B13_DRIFT_ADAPTATION_INSUFFICIENT"
    )
    assert (
        b13.b13_decision(_decision_frame(0.90, 0.90), 99, 10)
        == "B13_INSUFFICIENT_EXTERNAL_OVERLAP"
    )
    assert (
        b13.b13_decision(_decision_frame(0.90, 0.90), 200, 4)
        == "B13_INSUFFICIENT_EXTERNAL_OVERLAP"
    )
