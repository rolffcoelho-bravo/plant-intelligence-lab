import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_decision_horizons import (
    HORIZONS,
    availability_audit,
    historical_location_proxy,
    horizon_columns,
    location_code,
)
from plant_intelligence.models.maize_environment_process_kernels import build_ec_audit


def test_location_code_is_stable_across_years():
    assert location_code("2014-IAH1") == "IAH1"
    assert location_code("2021-IAH1") == "IAH1"


def test_early_horizon_excludes_later_and_target_proximal_columns():
    ecov = pd.DataFrame(
        {
            "TT_GerEme": [1.0, 2.0],
            "TT_EmeEnJ": [1.0, 2.0],
            "TT_EnJFlo": [1.0, 2.0],
            "TT_FlaFlw": [1.0, 2.0],
            "yield_FlaFlw": [1.0, 2.0],
            "SW_StGEnG": [1.0, 2.0],
        },
        index=["e1", "e2"],
    )
    audit = build_ec_audit(ecov)
    pre = horizon_columns(audit, HORIZONS[2])
    flowering = horizon_columns(audit, HORIZONS[3])
    reproductive = horizon_columns(audit, HORIZONS[4])
    assert set(pre) == {"TT_GerEme", "TT_EmeEnJ"}
    assert "TT_EnJFlo" in flowering
    assert "TT_FlaFlw" in reproductive
    assert "yield_FlaFlw" not in reproductive
    assert "SW_StGEnG" not in reproductive


def test_preseason_proxy_ignores_held_out_current_year_values():
    ecov = pd.DataFrame(
        {"x": [1.0, 3.0, 50.0, 7.0], "z": [2.0, 4.0, 60.0, 8.0]},
        index=["2018-LOC1", "2019-LOC1", "2020-LOC1", "2020-LOC2"],
    )
    train = {"2018-LOC1", "2019-LOC1"}
    proxy_a, audit_a = historical_location_proxy(ecov, train)
    changed = ecov.copy()
    changed.loc["2020-LOC1"] = [500.0, 600.0]
    proxy_b, _ = historical_location_proxy(changed, train)
    assert np.allclose(proxy_a.loc["2020-LOC1"], proxy_b.loc["2020-LOC1"])
    row = audit_a[audit_a.environment == "2020-LOC1"].iloc[0]
    assert row.history_source == "same_location_training_history"
    assert not bool(row.uses_outer_test_ecov)
    assert not bool(row.uses_own_current_year_ecov)


def test_training_proxy_excludes_its_own_environment_row():
    ecov = pd.DataFrame(
        {"x": [1.0, 3.0, 5.0]},
        index=["2018-LOC1", "2019-LOC1", "2020-LOC2"],
    )
    proxy, audit = historical_location_proxy(ecov, set(ecov.index))
    assert np.isclose(proxy.loc["2018-LOC1", "x"], 3.0)
    assert np.isclose(proxy.loc["2019-LOC1", "x"], 1.0)
    row = audit[audit.environment == "2018-LOC1"].iloc[0]
    assert row.n_same_location_history_environments == 1


def test_availability_audit_marks_source_level_caveat():
    ecov = pd.DataFrame(
        {
            "TT_GerEme": [1.0, 2.0],
            "TT_EmeEnJ": [1.0, 2.0],
            "TT_EnJFlo": [1.0, 2.0],
            "SW_FlaFlw": [1.0, 2.0],
            "yield_FlaFlw": [1.0, 2.0],
        },
        index=["e1", "e2"],
    )
    frame = availability_audit(build_ec_audit(ecov))
    g = frame[frame.horizon == "Pre-season-G-only"].iloc[0]
    hist = frame[frame.horizon == "Pre-season-location-history"].iloc[0]
    early = frame[frame.horizon == "Pre-flowering-observed"].iloc[0]
    assert g.availability_state == "PROSPECTIVE_SUPPORTED_G_ONLY"
    assert hist.availability_state == "PROSPECTIVE_PROXY_TRAINING_HISTORY_ONLY"
    assert early.availability_state == "RETROSPECTIVE_HORIZON_PROXY"
    assert not bool(g.source_phenology_calibrated_to_observed_silking)
    assert bool(early.source_phenology_calibrated_to_observed_silking)
