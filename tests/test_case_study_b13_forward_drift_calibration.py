import numpy as np
import pandas as pd
import pytest

from plant_intelligence.uncertainty.maize_b13_forward_drift_calibration import (
    ADAPTIVE,
    CONTROL,
    PRIMARY_ESTIMAND,
    branch_decision,
    calibration_pass,
    competitor_half_widths,
    drift_guard_state,
    environment_balanced_coverage,
    interval_score_90,
    officially_observable_sealed_cohort,
)


def test_environment_balanced_coverage_does_not_weight_dense_environment_more():
    frame = pd.DataFrame(
        {
            "environment": ["A"] * 10 + ["B"] * 2,
            "covered": [True] * 10 + [False] * 2,
        }
    )
    assert environment_balanced_coverage(frame, "covered") == pytest.approx(0.5)


def test_b12_published_environment_balanced_coverage_implies_locked_b13_level():
    state = drift_guard_state(0.8487186682822535)
    assert state.undercoverage_deficit == pytest.approx(0.05128133171774652)
    assert state.adaptive_quantile_level == pytest.approx(0.9512813317177465)


def test_one_sided_guard_never_narrows_after_overcoverage():
    state = drift_guard_state(0.96)
    assert state.undercoverage_deficit == 0.0
    assert state.adaptive_quantile_level == pytest.approx(0.90)


def test_drift_guard_cap_is_enforced():
    state = drift_guard_state(0.0)
    assert state.adaptive_quantile_level == pytest.approx(0.995)


def test_adaptive_half_width_cannot_be_smaller_than_control():
    residuals = np.linspace(0.01, 10.0, 200)
    widths = competitor_half_widths(residuals, 0.84)
    assert widths[ADAPTIVE] >= widths[CONTROL]


def test_interval_score_penalizes_misses_heavily():
    y = np.array([0.0, 3.0])
    lower = np.array([-1.0, -1.0])
    upper = np.array([1.0, 1.0])
    scores = interval_score_90(y, lower, upper)
    assert scores[0] == pytest.approx(2.0)
    assert scores[1] > scores[0]


def test_officially_observable_cohort_selected_by_key_presence_only():
    sealed = pd.DataFrame(
        {
            "genotype": ["g1", "g2", "g3"],
            "environment": ["e1", "e1", "e2"],
            "predicted": [1.0, 2.0, 3.0],
        }
    )
    answer = pd.DataFrame(
        {
            "genotype": ["g1", "g3"],
            "environment": ["e1", "e2"],
            "observed": [1000.0, -999.0],
        }
    )
    cohort, audit = officially_observable_sealed_cohort(sealed, answer)
    assert set(zip(cohort["genotype"], cohort["environment"])) == {("g1", "e1"), ("g3", "e2")}
    assert audit["official_answer_key_present"].sum() == 2
    assert audit["selection_uses_outcome_value"].eq(False).all()
    assert audit["post_reveal_protocol_amendment"].eq(False).all()
    assert audit["primary_estimand"].eq(PRIMARY_ESTIMAND).all()


def test_changing_numerical_outcomes_cannot_change_b13_cohort_membership():
    sealed = pd.DataFrame(
        {
            "genotype": ["g1", "g2", "g3"],
            "environment": ["e1", "e1", "e2"],
            "predicted": [1.0, 2.0, 3.0],
        }
    )
    answer_a = pd.DataFrame(
        {
            "genotype": ["g1", "g3"],
            "environment": ["e1", "e2"],
            "observed": [1.1, 3.2],
        }
    )
    answer_b = answer_a.copy()
    answer_b["observed"] = [1e12, -1e12]
    cohort_a, _ = officially_observable_sealed_cohort(sealed, answer_a)
    cohort_b, _ = officially_observable_sealed_cohort(sealed, answer_b)
    keys_a = list(zip(cohort_a["genotype"], cohort_a["environment"]))
    keys_b = list(zip(cohort_b["genotype"], cohort_b["environment"]))
    assert keys_a == keys_b


def test_present_key_with_missing_outcome_aborts_instead_of_posthoc_drop():
    sealed = pd.DataFrame({"genotype": ["g1"], "environment": ["e1"], "predicted": [1.0]})
    answer = pd.DataFrame({"genotype": ["g1"], "environment": ["e1"], "observed": [np.nan]})
    with pytest.raises(ValueError, match="missing/non-numeric"):
        officially_observable_sealed_cohort(sealed, answer)


def test_calibration_criterion_inherits_three_point_tolerance_and_cluster_ci():
    assert calibration_pass(0.88, 0.84, 0.93)
    assert not calibration_pass(0.85, 0.80, 0.94)
    assert not calibration_pass(0.89, 0.91, 0.97)


def test_adaptive_requires_efficiency_to_be_promoted():
    assert branch_decision(False, True, 10.0, 9.0) == "B13_ADAPTIVE_DRIFT_GUARD_PROMOTED"
    assert branch_decision(False, True, 9.0, 10.0) == "B13_ADAPTIVE_CALIBRATION_PASS_BUT_INEFFICIENT"
    assert branch_decision(True, True, 9.0, 9.0) == "B13_BOTH_INTERVAL_RULES_PASS_KEEP_FROZEN_B11"
    assert branch_decision(False, False, 9.0, 9.0) == "B13_BOTH_INTERVAL_RULES_FAIL"
