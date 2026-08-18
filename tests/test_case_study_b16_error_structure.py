import numpy as np
import pandas as pd

from plant_intelligence.diagnostics import maize_b16_error_structure as b16


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "genotype": ["g1", "g2", "g3", "g1", "g2", "g3"],
            "environment": ["e1", "e1", "e1", "e2", "e2", "e2"],
            "predicted": [1.0, 2.0, 3.0, 2.0, 4.0, 6.0],
            "observed": [3.0, 4.0, 5.0, 1.0, 4.0, 7.0],
        }
    )


def test_sse_decomposition_is_exact():
    env, summary = b16.decompose(_frame())
    assert len(env) == 2
    assert np.isclose(
        summary.raw_sse,
        summary.environment_mean_bias_sse + summary.within_environment_centered_sse,
        rtol=0,
        atol=1e-12,
    )
    assert abs(summary.sse_identity_residual) <= 1e-12
    assert np.isclose(
        summary.environment_bias_sse_fraction + summary.within_environment_sse_fraction,
        1.0,
        atol=1e-12,
    )


def test_pure_environment_offsets_have_zero_centered_error_and_perfect_ordering():
    frame = pd.DataFrame(
        {
            "genotype": ["a", "b", "c", "a", "b", "c"],
            "environment": ["e1"] * 3 + ["e2"] * 3,
            "predicted": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "observed": [3.0, 4.0, 5.0, 1.0, 2.0, 3.0],
        }
    )
    env, summary = b16.decompose(frame)
    assert np.isclose(summary.within_environment_centered_sse, 0.0, atol=1e-12)
    assert np.isclose(summary.environment_bias_sse_fraction, 1.0, atol=1e-12)
    assert np.isclose(summary.oracle_environment_intercept_corrected_rmse, 0.0, atol=1e-12)
    assert np.allclose(env["pearson"], 1.0)
    assert np.allclose(env["spearman"], 1.0)


def test_within_environment_ordering_error_survives_mean_residual_removal():
    frame = pd.DataFrame(
        {
            "genotype": ["a", "b", "c"],
            "environment": ["e1"] * 3,
            "predicted": [1.0, 2.0, 3.0],
            "observed": [3.0, 2.0, 1.0],
        }
    )
    env, summary = b16.decompose(frame)
    assert summary.within_environment_centered_sse > 0
    assert np.isclose(env.iloc[0]["pearson"], -1.0, atol=1e-12)
    assert np.isclose(env.iloc[0]["spearman"], -1.0, atol=1e-12)
    assert summary.oracle_environment_intercept_corrected_rmse > 0


def test_oracle_environment_intercept_never_increases_rmse():
    _, summary = b16.decompose(_frame())
    assert summary.oracle_environment_intercept_corrected_rmse <= summary.raw_rmse + 1e-12
    assert 0.0 <= summary.oracle_rmse_reduction_fraction <= 1.0


def test_b12_reference_remains_diagnostic_only():
    frame = pd.DataFrame(
        {
            "environment": ["e1", "e2"],
            "rmse": [2.0, 4.0],
            "r2": [-1.0, 0.2],
            "correlation": [0.1, 0.5],
            "diagnostic_only": [True, True],
            "selection_uses_outcome_value": [False, False],
        }
    )
    out = b16.b12_reference(frame).iloc[0]
    assert np.isclose(out["median_within_environment_pearson"], 0.3)
    assert np.isclose(out["fraction_environments_negative_r2"], 0.5)
    assert bool(out["confirmatory"]) is False
    assert bool(out["used_to_fit_or_tune_b16"]) is False
