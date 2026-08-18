"""Case Study B15: calibration-error transportability theory primitives.

B15 is theory/diagnostic only.  It does not modify the frozen G+E_T1 point
predictor, construct a new prediction interval, tune an adaptive rule, or read
new outcomes.  The central question is whether a calibration error observed in
one deployment domain is identifiable as information about calibration error in
a later domain.

For a fixed interval threshold q and target coverage tau, let

    F_t(q | z) = P(R_t <= q | Z_t=z)

be the conditional CDF of the nonconformity score and let mu_t be the deployment
distribution over environment states z.  Population coverage is

    C_t(q) = int F_t(q | z) d mu_t(z)

and the signed calibration gap is Delta_t(q) = C_t(q) - tau.

For source s and target t,

    Delta_t - Delta_s = Gamma_mix + Gamma_cond,

where Gamma_mix changes only the environment mixture while holding the source
conditional score law fixed, and Gamma_cond changes the conditional score law
under the target mixture.  This module implements the exact finite-support form
of that identity and the corresponding bounded-drift certificate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TARGET_NOMINAL = 0.90
THEORY_STAGE = "B15_CALIBRATION_TRANSPORTABILITY_THEORY"


@dataclass(frozen=True)
class TransportDecomposition:
    """Exact finite-support decomposition of a cross-domain calibration change."""

    nominal: float
    source_coverage: float
    target_coverage: float
    source_gap: float
    target_gap: float
    mixture_shift: float
    conditional_drift: float
    identity_residual: float


@dataclass(frozen=True)
class TransportCertificate:
    """Interval for the unidentified target calibration gap under a drift bound."""

    center: float
    conditional_drift_bound: float
    lower: float
    upper: float

    @property
    def sign_identified(self) -> bool:
        return bool(self.upper < 0.0 or self.lower > 0.0)

    @property
    def certifies_undercoverage(self) -> bool:
        return bool(self.upper < 0.0)

    @property
    def certifies_overcoverage(self) -> bool:
        return bool(self.lower > 0.0)


def _probability_vector(values: np.ndarray | list[float], name: str) -> np.ndarray:
    out = np.asarray(values, dtype=float)
    if out.ndim != 1 or out.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional vector.")
    if np.any(~np.isfinite(out)) or np.any(out < 0.0):
        raise ValueError(f"{name} must contain finite nonnegative values.")
    total = float(out.sum())
    if not np.isclose(total, 1.0, rtol=0.0, atol=1e-12):
        raise ValueError(f"{name} must sum to one; found {total!r}.")
    return out


def _cdf_vector(values: np.ndarray | list[float], name: str) -> np.ndarray:
    out = np.asarray(values, dtype=float)
    if out.ndim != 1 or out.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional vector.")
    if np.any(~np.isfinite(out)) or np.any((out < 0.0) | (out > 1.0)):
        raise ValueError(f"{name} must contain finite CDF values in [0, 1].")
    return out


def calibration_gap(coverage: float, nominal: float = TARGET_NOMINAL) -> float:
    """Return the signed population calibration gap coverage - nominal."""

    coverage = float(coverage)
    nominal = float(nominal)
    if not 0.0 <= coverage <= 1.0:
        raise ValueError("coverage must lie in [0, 1].")
    if not 0.0 < nominal < 1.0:
        raise ValueError("nominal must lie strictly between zero and one.")
    return float(coverage - nominal)


def finite_discrete_transport_decomposition(
    source_conditional_cdf: np.ndarray | list[float],
    target_conditional_cdf: np.ndarray | list[float],
    source_weights: np.ndarray | list[float],
    target_weights: np.ndarray | list[float],
    nominal: float = TARGET_NOMINAL,
) -> TransportDecomposition:
    """Compute the exact source-to-target calibration transport identity.

    All vectors use a common finite environment support.  Zero weights are
    allowed, so the union of source/target support may be represented without
    deleting states.

    Gamma_mix  = sum_z F_s(q|z) [mu_t(z)-mu_s(z)]
    Gamma_cond = sum_z [F_t(q|z)-F_s(q|z)] mu_t(z)
    """

    f_source = _cdf_vector(source_conditional_cdf, "source_conditional_cdf")
    f_target = _cdf_vector(target_conditional_cdf, "target_conditional_cdf")
    w_source = _probability_vector(source_weights, "source_weights")
    w_target = _probability_vector(target_weights, "target_weights")
    if not (f_source.shape == f_target.shape == w_source.shape == w_target.shape):
        raise ValueError("All transport vectors must have identical shape.")

    nominal = float(nominal)
    if not 0.0 < nominal < 1.0:
        raise ValueError("nominal must lie strictly between zero and one.")

    source_coverage = float(np.dot(f_source, w_source))
    target_coverage = float(np.dot(f_target, w_target))
    source_gap = calibration_gap(source_coverage, nominal)
    target_gap = calibration_gap(target_coverage, nominal)
    mixture_shift = float(np.dot(f_source, w_target - w_source))
    conditional_drift = float(np.dot(f_target - f_source, w_target))
    identity_residual = float((target_gap - source_gap) - (mixture_shift + conditional_drift))

    return TransportDecomposition(
        nominal=nominal,
        source_coverage=source_coverage,
        target_coverage=target_coverage,
        source_gap=source_gap,
        target_gap=target_gap,
        mixture_shift=mixture_shift,
        conditional_drift=conditional_drift,
        identity_residual=identity_residual,
    )


def bounded_transport_interval(
    source_gap: float,
    mixture_shift: float,
    conditional_drift_bound: float,
) -> TransportCertificate:
    """Bound the target gap when |Gamma_cond| is prospectively bounded.

    If |Gamma_cond| <= epsilon, then

        Delta_t in [Delta_s + Gamma_mix - epsilon,
                    Delta_s + Gamma_mix + epsilon].

    A certificate whose interval crosses zero does not identify the sign of the
    target calibration error and therefore cannot, by itself, justify a signed
    carry-forward correction.
    """

    source_gap = float(source_gap)
    mixture_shift = float(mixture_shift)
    epsilon = float(conditional_drift_bound)
    if not np.isfinite(source_gap) or not np.isfinite(mixture_shift):
        raise ValueError("source_gap and mixture_shift must be finite.")
    if not np.isfinite(epsilon) or epsilon < 0.0:
        raise ValueError("conditional_drift_bound must be finite and nonnegative.")
    center = source_gap + mixture_shift
    return TransportCertificate(
        center=float(center),
        conditional_drift_bound=epsilon,
        lower=float(center - epsilon),
        upper=float(center + epsilon),
    )


def conditional_supnorm_bound(
    source_conditional_cdf: np.ndarray | list[float],
    target_conditional_cdf: np.ndarray | list[float],
) -> float:
    """Return max_z |F_t(q|z)-F_s(q|z)| on a common finite support."""

    f_source = _cdf_vector(source_conditional_cdf, "source_conditional_cdf")
    f_target = _cdf_vector(target_conditional_cdf, "target_conditional_cdf")
    if f_source.shape != f_target.shape:
        raise ValueError("Conditional CDF vectors must have identical shape.")
    return float(np.max(np.abs(f_target - f_source)))


def no_free_transport_witness(
    source_conditional_cdf: np.ndarray | list[float],
    target_weights: np.ndarray | list[float],
    nominal: float = TARGET_NOMINAL,
    separation: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """Construct two target conditional laws with the same pre-outcome mixture.

    The construction is a finite-support witness for non-identifiability.  Both
    target worlds share the same source history and the same target environment
    weights, while their conditional score CDF values are shifted in opposite
    directions whenever the requested separation stays inside [0, 1].

    It is a proof helper, not an estimator and not a proposed adaptive rule.
    """

    f_source = _cdf_vector(source_conditional_cdf, "source_conditional_cdf")
    _probability_vector(target_weights, "target_weights")
    nominal = float(nominal)
    separation = float(separation)
    if not 0.0 < nominal < 1.0:
        raise ValueError("nominal must lie strictly between zero and one.")
    if not np.isfinite(separation) or separation <= 0.0:
        raise ValueError("separation must be finite and positive.")

    lower_room = float(np.min(f_source))
    upper_room = float(np.min(1.0 - f_source))
    if separation > min(lower_room, upper_room) + 1e-15:
        raise ValueError("Requested separation leaves the valid CDF range [0, 1].")
    return f_source - separation, f_source + separation
