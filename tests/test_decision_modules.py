import numpy as np
import pandas as pd

from plant_intelligence.optimization.active_learning import _rank
from plant_intelligence.uncertainty.conformal import _finite_sample_quantile


def test_finite_sample_quantile_is_monotone_in_coverage():
    residuals = np.array([0.1, 0.2, 0.4, 0.8, 1.6])
    q80 = _finite_sample_quantile(residuals, 0.80)
    q90 = _finite_sample_quantile(residuals, 0.90)
    q95 = _finite_sample_quantile(residuals, 0.95)
    assert q80 <= q90 <= q95


def test_predicted_response_ranking_prioritizes_larger_forecasts():
    frame = pd.DataFrame(
        {
            "y_pred": [0.5, 3.0, 1.5],
            "half_width_90": [0.2, 0.1, 0.4],
        }
    )
    ranked = _rank(frame, "predicted_response")
    assert ranked.iloc[0]["y_pred"] == 3.0


def test_uncertainty_ranking_prioritizes_wider_intervals():
    frame = pd.DataFrame(
        {
            "y_pred": [0.5, 3.0, 1.5],
            "half_width_90": [0.2, 0.1, 0.4],
        }
    )
    ranked = _rank(frame, "uncertainty")
    assert ranked.iloc[0]["half_width_90"] == 0.4


def test_balanced_ranking_returns_all_candidates():
    frame = pd.DataFrame(
        {
            "y_pred": [0.5, 3.0, 1.5],
            "half_width_90": [0.2, 0.1, 0.4],
        }
    )
    ranked = _rank(frame, "balanced")
    assert len(ranked) == len(frame)
    assert ranked["acquisition_score"].between(0.0, 1.0).all()
