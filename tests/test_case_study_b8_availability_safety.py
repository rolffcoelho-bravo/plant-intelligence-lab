import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_decision_horizon_safety import (
    availability_audit,
    historical_location_proxy,
)
from plant_intelligence.models.maize_environment_process_kernels import build_ec_audit


def test_training_fallback_excludes_its_own_environment_row():
    ecov = pd.DataFrame(
        {"x": [1.0, 3.0, 5.0], "z": [2.0, 4.0, 6.0]},
        index=["2018-LOC1", "2019-LOC2", "2020-LOC3"],
    )
    train = set(ecov.index)
    proxy, audit = historical_location_proxy(ecov, train)
    expected = ecov.loc[["2019-LOC2", "2020-LOC3"]].mean(axis=0)
    assert np.allclose(proxy.loc["2018-LOC1"], expected)
    row = audit[audit.environment == "2018-LOC1"].iloc[0]
    assert row.history_source == "global_training_history_fallback_excluding_self"
    assert not bool(row.uses_own_current_year_ecov)


def test_held_out_current_year_values_do_not_change_preseason_proxy():
    ecov = pd.DataFrame(
        {"x": [1.0, 3.0, 10.0], "z": [2.0, 4.0, 20.0]},
        index=["2018-LOC1", "2019-LOC1", "2020-LOC1"],
    )
    train = {"2018-LOC1", "2019-LOC1"}
    first, audit = historical_location_proxy(ecov, train)
    changed = ecov.copy()
    changed.loc["2020-LOC1"] = [100.0, 200.0]
    second, _ = historical_location_proxy(changed, train)
    assert np.allclose(first.loc["2020-LOC1"], second.loc["2020-LOC1"])
    row = audit[audit.environment == "2020-LOC1"].iloc[0]
    assert row.history_source == "same_location_training_history"
    assert not bool(row.uses_outer_test_ecov)


def test_availability_audit_separates_source_provenance_from_current_year_use():
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
    genomic = frame[frame.horizon == "Pre-season-G-only"].iloc[0]
    history = frame[frame.horizon == "Pre-season-location-history"].iloc[0]
    early = frame[frame.horizon == "Pre-flowering-observed"].iloc[0]

    assert not bool(genomic.source_ecov_uses_observed_silking_calibration)
    assert bool(history.source_ecov_uses_observed_silking_calibration)
    assert not bool(history.uses_heldout_current_year_ecov_or_silking)
    assert bool(early.source_ecov_uses_observed_silking_calibration)
    assert bool(early.uses_heldout_current_year_ecov_or_silking)
