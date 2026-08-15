import numpy as np
import pandas as pd

from plant_intelligence.uncertainty.maize_forward_uncertainty import (
    ABSTAIN,
    INSUFFICIENT,
    RETAIN,
    SUPPORT_EDGE,
    SUPPORT_WITHIN,
    calibrate_forward_intervals,
    finite_sample_quantile,
    reliability_state,
    support_group,
)


# B11 software checks are intentionally lightweight; the GitHub Actions B11
# workflow performs the frozen real-data T1 reproduction and forward audit.
def _synthetic_cells() -> pd.DataFrame:
    rows = []
    for year in range(2016, 2022):
        for env_i in range(6):
            group = SUPPORT_EDGE if env_i == 5 else SUPPORT_WITHIN
            for g in range(50):
                observed = float(g % 7) + 0.1 * env_i
                error_scale = 2.0 if group == SUPPORT_EDGE else 1.0
                predicted = observed + error_scale * (0.2 + 0.01 * (g % 5))
                rows.append(
                    {
                        "genotype": f"g{g}",
                        "environment": f"{year}-e{env_i}",
                        "test_year": year,
                        "train_year_max": year - 1,
                        "observed": observed,
                        "predicted": predicted,
                        "absolute_error": abs(observed - predicted),
                        "support_group": group,
                        "full_nearest_percentile": 1.0 if group == SUPPORT_EDGE else 0.5,
                    }
                )
    return pd.DataFrame(rows)


def test_finite_sample_quantile_uses_ceiling_rank():
    scores = np.arange(1.0, 11.0)
    # ceil((10+1)*0.8)=9, therefore the ninth order statistic is selected.
    assert finite_sample_quantile(scores, 0.8) == 9.0


def test_support_boundary_is_outcome_free_envelope_rule():
    assert support_group(0.999) == SUPPORT_WITHIN
    assert support_group(1.0) == SUPPORT_EDGE
    assert support_group(1.2) == SUPPORT_EDGE


def test_reliability_states_preserve_insufficient_history():
    assert reliability_state(0, SUPPORT_WITHIN) == INSUFFICIENT
    assert reliability_state(1, SUPPORT_EDGE) == INSUFFICIENT
    assert reliability_state(2, SUPPORT_WITHIN) == RETAIN
    assert reliability_state(2, SUPPORT_EDGE) == ABSTAIN


def test_forward_calibration_never_uses_current_or_future_year():
    audit, by_year, evaluated = calibrate_forward_intervals(_synthetic_cells())
    early = audit[audit["test_year"].isin([2016, 2017])]
    assert early["status"].eq(INSUFFICIENT).all()
    later = audit[audit["test_year"] >= 2018]
    assert later["status"].eq("CALIBRATION_AVAILABLE").all()
    assert (later["calibration_year_max"] < later["test_year"]).all()
    assert later["test_year_used_for_calibration"].eq(False).all()
    assert later["future_year_used_for_calibration"].eq(False).all()
    assert sorted(evaluated["test_year"].unique().tolist()) == [2018, 2019, 2020, 2021]
    assert set(evaluated["reliability_state"]) == {RETAIN, ABSTAIN}


def test_support_adaptive_quantile_uses_historical_stratum_when_sufficient():
    _, by_year, _ = calibrate_forward_intervals(_synthetic_cells())
    row = by_year[(by_year["test_year"] == 2018) & np.isclose(by_year["nominal"], 0.90)].iloc[0]
    # Prior 2016-2017 supply 10 within-support and 2 edge environments.
    # The within group therefore has enough environments for its own quantile,
    # while the edge group must use the chronological global fallback.
    assert row["within_group_quantile_source"] == "SUPPORT_GROUP_CHRONOLOGICAL"
    assert row["edge_group_quantile_source"] == "GLOBAL_CHRONOLOGICAL_FALLBACK"
