"""Case Study B13: forward calibration drift adaptation primitives.

B13 keeps the frozen G+E_T1 point predictor unchanged and compares exactly two
90% interval rules for the next season:

* FROZEN_B11_90: finite-sample 90% residual quantile through the latest revealed
  season.
* ONE_SIDED_CLUSTER_DRIFT_GUARD_90: the same residual pool, but the target
  quantile level is increased by the previous season's environment-balanced
  undercoverage deficit. Favorable prior coverage is not allowed to narrow the
  interval.

This module contains only pre-reveal mathematical/protocol primitives. It does
not acquire future outcomes or perform post-result tuning.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from plant_intelligence.uncertainty.maize_forward_uncertainty import finite_sample_quantile

TARGET_NOMINAL = 0.90
MAX_ADAPTIVE_LEVEL = 0.995
CONTROL = "FROZEN_B11_90"
ADAPTIVE = "ONE_SIDED_CLUSTER_DRIFT_GUARD_90"
PRIMARY_ESTIMAND = "OFFICIALLY_OBSERVABLE_SEALED_KEYS"
SEALED_STATE = "B13_2023_TWO_COMPETITOR_ARTIFACT_SEALED"


@dataclass(frozen=True)
class DriftGuardState:
    target_nominal: float
    previous_environment_balanced_coverage: float
    undercoverage_deficit: float
    adaptive_quantile_level: float


def environment_balanced_coverage(
    frame: pd.DataFrame,
    covered_col: str,
    environment_col: str = "environment",
) -> float:
    """Give every environment equal weight in the season-level coverage state."""

    if frame.empty:
        raise ValueError("Cannot compute environment-balanced coverage on an empty frame.")
    if covered_col not in frame or environment_col not in frame:
        raise KeyError("Coverage frame is missing required columns.")
    covered = frame[covered_col]
    if covered.isna().any():
        raise ValueError("Coverage indicator contains missing values.")
    if frame[environment_col].isna().any():
        raise ValueError("Environment identifier contains missing values.")
    env_cov = frame.assign(_covered=covered.astype(bool).astype(float)).groupby(environment_col)["_covered"].mean()
    if env_cov.empty:
        raise ValueError("No environments available for coverage aggregation.")
    return float(env_cov.mean())


def drift_guard_state(
    previous_environment_balanced_coverage: float,
    target_nominal: float = TARGET_NOMINAL,
    max_level: float = MAX_ADAPTIVE_LEVEL,
) -> DriftGuardState:
    """Deterministic one-sided season feedback with no learning-rate parameter."""

    previous = float(previous_environment_balanced_coverage)
    target = float(target_nominal)
    cap = float(max_level)
    if not 0.0 <= previous <= 1.0:
        raise ValueError("Previous environment-balanced coverage must lie in [0, 1].")
    if not 0.0 < target < 1.0:
        raise ValueError("Target nominal coverage must lie strictly between 0 and 1.")
    if not target <= cap < 1.0:
        raise ValueError("Adaptive cap must be at least target_nominal and below one.")
    deficit = max(0.0, target - previous)
    adaptive = min(cap, target + deficit)
    return DriftGuardState(target, previous, deficit, adaptive)


def competitor_half_widths(
    residuals: np.ndarray | pd.Series,
    previous_environment_balanced_coverage: float,
) -> dict[str, float]:
    """Return locked 90% control and drift-guard half-widths from one residual pool."""

    state = drift_guard_state(previous_environment_balanced_coverage)
    control_q = finite_sample_quantile(residuals, TARGET_NOMINAL)
    adaptive_q = finite_sample_quantile(residuals, state.adaptive_quantile_level)
    if adaptive_q + 1e-12 < control_q:
        raise AssertionError("One-sided B13 drift guard cannot be narrower than control.")
    return {CONTROL: float(control_q), ADAPTIVE: float(adaptive_q)}


def interval_score_90(
    observed: np.ndarray | pd.Series,
    lower: np.ndarray | pd.Series,
    upper: np.ndarray | pd.Series,
) -> np.ndarray:
    """Winkler interval score for a central 90% prediction interval."""

    y = np.asarray(observed, dtype=float)
    lo = np.asarray(lower, dtype=float)
    hi = np.asarray(upper, dtype=float)
    if not (y.shape == lo.shape == hi.shape):
        raise ValueError("Observed/lower/upper arrays must have identical shape.")
    if np.any(~np.isfinite(y)) or np.any(~np.isfinite(lo)) or np.any(~np.isfinite(hi)):
        raise ValueError("Interval score inputs must be finite.")
    if np.any(lo > hi):
        raise ValueError("Lower interval bound cannot exceed upper bound.")
    alpha = 1.0 - TARGET_NOMINAL
    width = hi - lo
    low_penalty = (2.0 / alpha) * (lo - y) * (y < lo)
    high_penalty = (2.0 / alpha) * (y - hi) * (y > hi)
    return width + low_penalty + high_penalty


def officially_observable_sealed_cohort(
    sealed: pd.DataFrame,
    official_answer: pd.DataFrame,
    genotype_col: str = "genotype",
    environment_col: str = "environment",
    observed_col: str = "observed",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prospectively declared B13 primary estimand based on exact key presence only.

    A key present in the official answer with a missing/non-numeric outcome is a
    data-integrity failure; it is never silently dropped after inspecting value.
    """

    keys = [genotype_col, environment_col]
    for col in keys:
        if col not in sealed or col not in official_answer:
            raise KeyError(f"Missing key column {col!r}.")
    if observed_col not in official_answer:
        raise KeyError(f"Missing observed outcome column {observed_col!r}.")
    if sealed.duplicated(keys).any():
        raise ValueError("Sealed B13 artifact contains duplicate keys.")
    if official_answer.duplicated(keys).any():
        raise ValueError("Official B13 answer contains duplicate keys.")

    answer = official_answer[keys + [observed_col]].copy()
    answer[observed_col] = pd.to_numeric(answer[observed_col], errors="coerce")
    answer_keys = answer[keys].copy()
    answer_keys["official_answer_key_present"] = True

    audit = sealed[keys].merge(answer_keys, on=keys, how="left", validate="one_to_one")
    audit["official_answer_key_present"] = audit["official_answer_key_present"].fillna(False).astype(bool)
    cohort = sealed.merge(answer, on=keys, how="left", validate="one_to_one")
    cohort = cohort.merge(audit, on=keys, how="left", validate="one_to_one")

    present = cohort["official_answer_key_present"].astype(bool)
    if cohort.loc[present, observed_col].isna().any():
        raise ValueError(
            "Official answer contains a sealed key with missing/non-numeric outcome; "
            "B13 forbids outcome-value-based row deletion."
        )
    if cohort.loc[~present, observed_col].notna().any():
        raise AssertionError("Outcome attached to a key absent from the official key set.")

    observable = cohort.loc[present].copy()
    if observable.empty:
        raise ValueError("No sealed B13 key is officially observable.")
    audit["primary_estimand"] = PRIMARY_ESTIMAND
    audit["selection_uses_outcome_value"] = False
    audit["post_reveal_protocol_amendment"] = False
    return observable, audit


def calibration_pass(
    empirical_coverage: float,
    cluster_ci_low: float,
    cluster_ci_high: float,
    target: float = TARGET_NOMINAL,
    max_gap: float = 0.03,
) -> bool:
    """Inherited B11/B12 external calibration criterion."""

    coverage = float(empirical_coverage)
    low = float(cluster_ci_low)
    high = float(cluster_ci_high)
    return bool(abs(coverage - target) <= max_gap and low <= target <= high)


def branch_decision(
    control_pass: bool,
    adaptive_pass: bool,
    control_mean_interval_score: float,
    adaptive_mean_interval_score: float,
) -> str:
    """Predeclared complexity-penalizing B13 decision rule."""

    c_score = float(control_mean_interval_score)
    a_score = float(adaptive_mean_interval_score)
    if not np.isfinite(c_score) or not np.isfinite(a_score):
        raise ValueError("Interval scores must be finite.")
    if adaptive_pass:
        if a_score < c_score - 1e-12:
            return "B13_ADAPTIVE_DRIFT_GUARD_PROMOTED"
        if control_pass:
            return "B13_BOTH_INTERVAL_RULES_PASS_KEEP_FROZEN_B11"
        return "B13_ADAPTIVE_CALIBRATION_PASS_BUT_INEFFICIENT"
    if control_pass:
        return "B13_BOTH_INTERVAL_RULES_PASS_KEEP_FROZEN_B11"
    return "B13_BOTH_INTERVAL_RULES_FAIL"
