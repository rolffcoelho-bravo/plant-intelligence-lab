"""B15-T1 feedback-decision identification primitives.

This module is a hostile-audit scaffold, not a new calibration algorithm.
It formalizes the finite ambiguity-set decision problem that remained after B15:
for a fixed set of interval-feedback actions and admissible future worlds, which
actions are statewise optimal, identified, robustly feasible, minimax, or
minimax-regret?

The module deliberately contains no predictor fitting, no outcome acquisition,
no interval retuning, and no new adaptive rule.  Its purpose is to make the
candidate B15-T1 object explicit enough to test for equivalence with classical
partial-identification and robust statistical decision theory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

TARGET_NOMINAL = 0.90
STAGE = "B15_T1_FEEDBACK_DECISION_NOVELTY_TEST"


@dataclass(frozen=True)
class FeedbackDecisionResult:
    """Finite-world action-identification and robust-decision summary."""

    action_names: tuple[str, ...]
    statewise_optimal_actions: tuple[tuple[str, ...], ...]
    identified_optimal_action_set: tuple[str, ...]
    point_identified: bool
    robustly_feasible_actions: tuple[str, ...]
    minimax_loss_actions: tuple[str, ...]
    minimax_regret_actions: tuple[str, ...]
    worst_case_loss: tuple[float, ...]
    worst_case_regret: tuple[float, ...]


def _matrix(values: np.ndarray | Sequence[Sequence[float]], name: str) -> np.ndarray:
    out = np.asarray(values, dtype=float)
    if out.ndim != 2 or out.shape[0] == 0 or out.shape[1] == 0:
        raise ValueError(f"{name} must be a non-empty two-dimensional matrix.")
    if np.any(~np.isfinite(out)):
        raise ValueError(f"{name} must contain only finite values.")
    return out


def _actions(action_names: Sequence[str], n_actions: int) -> tuple[str, ...]:
    actions = tuple(str(x) for x in action_names)
    if len(actions) != n_actions:
        raise ValueError("action_names length must match the number of matrix columns.")
    if any(not x for x in actions):
        raise ValueError("action_names cannot contain empty names.")
    if len(set(actions)) != len(actions):
        raise ValueError("action_names must be unique.")
    return actions


def _argmin_indices(values: np.ndarray, candidates: np.ndarray, atol: float) -> np.ndarray:
    if candidates.size == 0:
        return candidates
    candidate_values = values[candidates]
    best = float(np.min(candidate_values))
    return candidates[np.isclose(candidate_values, best, rtol=0.0, atol=atol)]


def feedback_decision_analysis(
    loss_by_world_action: np.ndarray | Sequence[Sequence[float]],
    coverage_by_world_action: np.ndarray | Sequence[Sequence[float]],
    action_names: Sequence[str],
    nominal: float = TARGET_NOMINAL,
    atol: float = 1e-12,
) -> FeedbackDecisionResult:
    """Analyze a finite ambiguity class under a coverage-constrained loss.

    Rows are admissible future worlds P in the pre-outcome ambiguity class and
    columns are predeclared feedback actions a.  `loss_by_world_action[w, a]`
    is the population decision loss in world w after taking action a, while
    `coverage_by_world_action[w, a]` is its population interval coverage.

    Statewise optimal actions minimize loss subject to coverage >= nominal in
    each world.  Their union is the identified set of optimal actions induced by
    the ambiguity class.  It is point-identified only when that union is a
    singleton.

    Robust minimax and minimax-regret actions are restricted to actions whose
    coverage constraint holds in every admissible world.

    These are standard ambiguity-set decision objects.  B15-T1 uses them to
    test novelty; their implementation is not itself claimed as a contribution.
    """

    loss = _matrix(loss_by_world_action, "loss_by_world_action")
    coverage = _matrix(coverage_by_world_action, "coverage_by_world_action")
    if loss.shape != coverage.shape:
        raise ValueError("loss and coverage matrices must have identical shape.")
    actions = _actions(action_names, loss.shape[1])

    nominal = float(nominal)
    atol = float(atol)
    if not 0.0 < nominal < 1.0:
        raise ValueError("nominal must lie strictly between zero and one.")
    if atol < 0.0 or not np.isfinite(atol):
        raise ValueError("atol must be finite and nonnegative.")
    if np.any((coverage < 0.0) | (coverage > 1.0)):
        raise ValueError("coverage values must lie in [0, 1].")

    statewise: list[tuple[str, ...]] = []
    union_indices: set[int] = set()
    statewise_best_loss = np.empty(loss.shape[0], dtype=float)

    for world in range(loss.shape[0]):
        feasible = np.flatnonzero(coverage[world] >= nominal - atol)
        if feasible.size == 0:
            raise ValueError(
                f"Admissible world {world} has no action satisfying the coverage constraint."
            )
        best = _argmin_indices(loss[world], feasible, atol)
        statewise_best_loss[world] = float(np.min(loss[world, feasible]))
        union_indices.update(int(i) for i in best)
        statewise.append(tuple(actions[int(i)] for i in best))

    identified_indices = np.array(sorted(union_indices), dtype=int)
    identified_set = tuple(actions[int(i)] for i in identified_indices)

    robust_feasible = np.flatnonzero(np.all(coverage >= nominal - atol, axis=0))
    if robust_feasible.size == 0:
        minimax_loss = np.array([], dtype=int)
        minimax_regret = np.array([], dtype=int)
    else:
        worst_loss = np.max(loss, axis=0)
        minimax_loss = _argmin_indices(worst_loss, robust_feasible, atol)

        regret = loss - statewise_best_loss[:, None]
        worst_regret_values = np.max(regret, axis=0)
        minimax_regret = _argmin_indices(worst_regret_values, robust_feasible, atol)

    worst_case_loss = tuple(float(x) for x in np.max(loss, axis=0))
    regret = loss - statewise_best_loss[:, None]
    worst_case_regret = tuple(float(x) for x in np.max(regret, axis=0))

    return FeedbackDecisionResult(
        action_names=actions,
        statewise_optimal_actions=tuple(statewise),
        identified_optimal_action_set=identified_set,
        point_identified=len(identified_set) == 1,
        robustly_feasible_actions=tuple(actions[int(i)] for i in robust_feasible),
        minimax_loss_actions=tuple(actions[int(i)] for i in minimax_loss),
        minimax_regret_actions=tuple(actions[int(i)] for i in minimax_regret),
        worst_case_loss=worst_case_loss,
        worst_case_regret=worst_case_regret,
    )


def feedback_direction_set(
    identified_optimal_action_set: Sequence[str],
    action_direction: dict[str, int],
) -> tuple[int, ...]:
    """Return identified feedback directions {-1, 0, +1} for optimal actions.

    The mapping is supplied explicitly so B15-T1 does not infer semantics from
    action names.  A singleton result means direction is identified even when
    multiple actions of the same direction tie; multiple directions mean the
    feedback direction is not identified by the ambiguity class.
    """

    directions: set[int] = set()
    for action in identified_optimal_action_set:
        if action not in action_direction:
            raise KeyError(f"Missing direction for action {action!r}.")
        direction = int(action_direction[action])
        if direction not in (-1, 0, 1):
            raise ValueError("Action directions must be -1, 0, or +1.")
        directions.add(direction)
    if not directions:
        raise ValueError("identified_optimal_action_set cannot be empty.")
    return tuple(sorted(directions))
