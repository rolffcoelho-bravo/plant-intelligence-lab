import numpy as np
import pytest

from plant_intelligence.uncertainty import maize_b15_t1_feedback_decision as b15t1


def test_same_preoutcome_ambiguity_class_can_make_all_three_feedback_directions_statewise_optimal():
    actions = ["NARROW", "RETAIN", "WIDEN"]
    loss = [
        [1.0, 2.0, 4.0],
        [1.0, 2.0, 3.0],
        [1.0, 2.0, 3.0],
    ]
    coverage = [
        [0.91, 0.95, 0.99],
        [0.86, 0.92, 0.97],
        [0.80, 0.88, 0.93],
    ]

    out = b15t1.feedback_decision_analysis(loss, coverage, actions)

    assert out.statewise_optimal_actions == (("NARROW",), ("RETAIN",), ("WIDEN",))
    assert out.identified_optimal_action_set == ("NARROW", "RETAIN", "WIDEN")
    assert not out.point_identified
    assert b15t1.feedback_direction_set(
        out.identified_optimal_action_set,
        {"NARROW": -1, "RETAIN": 0, "WIDEN": 1},
    ) == (-1, 0, 1)


def test_robust_coverage_constraint_can_leave_only_widen_as_admissible_action():
    actions = ["NARROW", "RETAIN", "WIDEN"]
    loss = [
        [1.0, 1.5, 2.0],
        [1.0, 1.4, 2.2],
    ]
    coverage = [
        [0.92, 0.94, 0.97],
        [0.84, 0.89, 0.93],
    ]

    out = b15t1.feedback_decision_analysis(loss, coverage, actions)

    assert out.robustly_feasible_actions == ("WIDEN",)
    assert out.minimax_loss_actions == ("WIDEN",)
    assert out.minimax_regret_actions == ("WIDEN",)


def test_point_identification_requires_same_optimal_action_across_all_admissible_worlds():
    actions = ["NARROW", "RETAIN", "WIDEN"]
    loss = [
        [2.0, 1.0, 3.0],
        [2.5, 1.2, 3.2],
        [2.1, 1.1, 3.1],
    ]
    coverage = [
        [0.91, 0.94, 0.98],
        [0.90, 0.93, 0.97],
        [0.92, 0.95, 0.99],
    ]

    out = b15t1.feedback_decision_analysis(loss, coverage, actions)

    assert out.point_identified
    assert out.identified_optimal_action_set == ("RETAIN",)
    assert b15t1.feedback_direction_set(
        out.identified_optimal_action_set,
        {"NARROW": -1, "RETAIN": 0, "WIDEN": 1},
    ) == (0,)


def test_minimax_regret_is_computed_against_each_worlds_best_coverage_feasible_action():
    actions = ["A", "B"]
    loss = [
        [0.0, 2.0],
        [4.0, 1.0],
    ]
    coverage = [
        [0.95, 0.95],
        [0.95, 0.95],
    ]

    out = b15t1.feedback_decision_analysis(loss, coverage, actions)

    assert np.allclose(out.worst_case_regret, [3.0, 2.0])
    assert out.minimax_regret_actions == ("B",)


def test_tied_statewise_optima_expand_identified_set_but_can_share_direction():
    actions = ["RETAIN_A", "RETAIN_B", "WIDEN"]
    loss = [[1.0, 1.0, 2.0], [1.0, 1.0, 3.0]]
    coverage = [[0.93, 0.94, 0.98], [0.92, 0.95, 0.99]]

    out = b15t1.feedback_decision_analysis(loss, coverage, actions)

    assert not out.point_identified
    assert out.identified_optimal_action_set == ("RETAIN_A", "RETAIN_B")
    assert b15t1.feedback_direction_set(
        out.identified_optimal_action_set,
        {"RETAIN_A": 0, "RETAIN_B": 0, "WIDEN": 1},
    ) == (0,)


def test_no_robustly_feasible_action_is_reported_without_inventing_a_decision():
    actions = ["A", "B"]
    loss = [[1.0, 2.0], [2.0, 1.0]]
    coverage = [[0.95, 0.85], [0.85, 0.95]]

    out = b15t1.feedback_decision_analysis(loss, coverage, actions)

    assert out.robustly_feasible_actions == ()
    assert out.minimax_loss_actions == ()
    assert out.minimax_regret_actions == ()
    assert not out.point_identified


def test_invalid_inputs_fail_closed():
    with pytest.raises(ValueError, match="identical shape"):
        b15t1.feedback_decision_analysis(
            [[1.0, 2.0]], [[0.9]], ["A", "B"]
        )

    with pytest.raises(ValueError, match="coverage values"):
        b15t1.feedback_decision_analysis(
            [[1.0]], [[1.1]], ["A"]
        )

    with pytest.raises(ValueError, match="no action satisfying"):
        b15t1.feedback_decision_analysis(
            [[1.0, 2.0]], [[0.80, 0.85]], ["A", "B"]
        )

    with pytest.raises(KeyError, match="Missing direction"):
        b15t1.feedback_direction_set(["A"], {})
