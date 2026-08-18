import numpy as np
import pytest

from plant_intelligence.uncertainty import maize_b15_calibration_transport as b15


def test_exact_transport_decomposition_identity():
    source_f = [0.80, 0.90, 0.95]
    target_f = [0.84, 0.86, 0.97]
    source_w = [0.50, 0.30, 0.20]
    target_w = [0.20, 0.50, 0.30]
    out = b15.finite_discrete_transport_decomposition(
        source_f, target_f, source_w, target_w
    )
    assert np.isclose(
        out.target_gap - out.source_gap,
        out.mixture_shift + out.conditional_drift,
        rtol=0,
        atol=1e-15,
    )
    assert abs(out.identity_residual) <= 1e-15


def test_zero_conditional_drift_leaves_only_environment_mixture_shift():
    f = [0.70, 0.90, 0.98]
    out = b15.finite_discrete_transport_decomposition(
        f, f, [0.6, 0.3, 0.1], [0.1, 0.3, 0.6]
    )
    assert np.isclose(out.conditional_drift, 0.0, atol=1e-15)
    assert np.isclose(
        out.target_gap - out.source_gap, out.mixture_shift, atol=1e-15
    )


def test_zero_mixture_shift_leaves_only_conditional_score_drift():
    weights = [0.25, 0.75]
    out = b15.finite_discrete_transport_decomposition(
        [0.82, 0.88], [0.91, 0.93], weights, weights
    )
    assert np.isclose(out.mixture_shift, 0.0, atol=1e-15)
    assert np.isclose(
        out.target_gap - out.source_gap, out.conditional_drift, atol=1e-15
    )


def test_supnorm_drift_bound_implies_target_gap_certificate():
    source_f = [0.80, 0.91, 0.95]
    target_f = [0.83, 0.89, 0.99]
    source_w = [0.5, 0.3, 0.2]
    target_w = [0.2, 0.5, 0.3]
    out = b15.finite_discrete_transport_decomposition(
        source_f, target_f, source_w, target_w
    )
    epsilon = b15.conditional_supnorm_bound(source_f, target_f)
    cert = b15.bounded_transport_interval(
        out.source_gap, out.mixture_shift, epsilon
    )
    assert cert.lower - 1e-15 <= out.target_gap <= cert.upper + 1e-15


def test_certificate_crossing_zero_does_not_identify_transport_sign():
    cert = b15.bounded_transport_interval(
        source_gap=-0.03,
        mixture_shift=0.01,
        conditional_drift_bound=0.04,
    )
    assert cert.lower < 0 < cert.upper
    assert not cert.sign_identified
    assert not cert.certifies_undercoverage
    assert not cert.certifies_overcoverage


def test_certificate_can_prospectively_certify_undercoverage_only_if_whole_bound_negative():
    cert = b15.bounded_transport_interval(
        source_gap=-0.06,
        mixture_shift=0.01,
        conditional_drift_bound=0.02,
    )
    assert cert.upper < 0
    assert cert.sign_identified
    assert cert.certifies_undercoverage
    assert not cert.certifies_overcoverage


def test_no_free_transport_two_target_worlds_share_preoutcome_information_but_change_gap_sign():
    source_f = np.array([0.90, 0.90, 0.90])
    source_w = np.array([0.2, 0.5, 0.3])
    target_w = np.array([0.4, 0.1, 0.5])
    low_world, high_world = b15.no_free_transport_witness(
        source_f, target_w, separation=0.06
    )
    low = b15.finite_discrete_transport_decomposition(
        source_f, low_world, source_w, target_w
    )
    high = b15.finite_discrete_transport_decomposition(
        source_f, high_world, source_w, target_w
    )
    assert np.isclose(low.source_gap, high.source_gap, atol=1e-15)
    assert np.isclose(low.mixture_shift, high.mixture_shift, atol=1e-15)
    assert low.target_gap < 0
    assert high.target_gap > 0


def test_historical_b12_b14c_motivation_constants_are_not_interpreted_as_a_new_rule():
    b12_env_balanced_90 = 0.8487186682822535
    b14c_control_env_balanced_90 = 0.8997721030003023
    b14c_adaptive_env_balanced_90 = 0.9521031534328204

    assert np.isclose(
        b15.calibration_gap(b12_env_balanced_90),
        -0.0512813317177465,
        rtol=0,
        atol=1e-15,
    )
    assert np.isclose(
        b15.calibration_gap(b14c_control_env_balanced_90),
        -0.00022789699969771848,
        rtol=0,
        atol=1e-15,
    )
    assert np.isclose(
        b15.calibration_gap(b14c_adaptive_env_balanced_90),
        0.05210315343282035,
        rtol=0,
        atol=1e-15,
    )


def test_invalid_probability_and_cdf_inputs_fail_closed():
    with pytest.raises(ValueError, match="sum to one"):
        b15.finite_discrete_transport_decomposition(
            [0.9, 0.9], [0.9, 0.9], [0.3, 0.3], [0.5, 0.5]
        )
    with pytest.raises(ValueError, match="CDF values"):
        b15.finite_discrete_transport_decomposition(
            [0.9, 1.1], [0.9, 0.9], [0.5, 0.5], [0.5, 0.5]
        )
