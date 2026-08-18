import numpy as np
import pandas as pd

from plant_intelligence.diagnostics.maize_b17_response_amplitude_transport import (
    DECISION,
    amplitude_nonidentification_witness,
    direct_pairwise_msed,
    environment_response_amplitude,
    pairwise_msed_from_residuals,
)


def test_pairwise_msed_identity_matches_direct_ordered_pairs():
    residual = np.array([1.0, -2.0, 0.5, 4.0, -1.5])
    fast = pairwise_msed_from_residuals(residual)
    direct = direct_pairwise_msed(residual)
    assert np.isclose(fast, direct, atol=1e-12, rtol=0.0)


def test_environment_amplitude_decomposes_dispersion_slope_into_correlation_and_scale():
    frame = pd.DataFrame(
        {
            "environment": ["E1"] * 6,
            "predicted": [1.0, 2.0, 3.0, 4.0, 5.0, 7.0],
            "observed": [2.0, 3.0, 7.0, 8.0, 11.0, 13.0],
        }
    )
    env, summary = environment_response_amplitude(frame)
    row = env.iloc[0]
    assert np.isfinite(row["observed_on_predicted_slope"])
    assert np.isclose(
        row["observed_on_predicted_slope"],
        row["slope_from_correlation_and_scale"],
        atol=1e-12,
        rtol=0.0,
    )
    assert abs(float(row["slope_identity_residual"])) < 1e-12
    assert summary.n_cells == 6
    assert summary.n_environments == 1


def test_amplitude_is_not_point_identified_from_same_prediction_vector_alone():
    prediction = np.array([1.0, 2.0, 4.0, 8.0])
    witness = amplitude_nonidentification_witness(prediction)
    assert len(witness) == 2
    assert witness["same_preoutcome_information"].all()
    assert witness["same_prediction_vector"].all()
    assert not witness["forecast_time_target_amplitude_point_identified"].any()
    ratios = witness.set_index("world")["predicted_to_observed_sd_ratio"]
    assert np.isclose(ratios["WORLD_A"], 2.0)
    assert np.isclose(ratios["WORLD_B"], 0.5)


def test_b17_decision_is_a_novelty_rejection_not_a_model_promotion():
    assert DECISION == "B17_BROAD_RESPONSE_AMPLITUDE_NOVELTY_REJECTED_OPEN_ARCHITECTURE_CONTRACTION_TEST"
