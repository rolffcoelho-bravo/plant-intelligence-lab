import numpy as np
import pandas as pd
import pytest

from plant_intelligence.models.maize_forecast_time_prediction import (
    FROZEN_CONFIG,
    MODEL_ORDER,
    build_environment_state_matrices,
    paired_cluster_bootstrap,
    validate_b9_inputs,
    value_of_waiting,
)


def _inputs():
    envs = pd.DataFrame(
        {
            "environment": ["2014-A", "2015-A", "2016-A"],
            "year": [2014, 2015, 2016],
            "planting_date": ["2014-05-01", "2015-05-02", "2016-05-03"],
            "latitude": [40.0, 40.0, 40.0],
            "longitude": [-90.0, -90.0, -90.0],
            "plant_population_proxy": [np.nan, 8.0, 9.0],
        }
    )
    rows = []
    horizons = [
        ("T0_preseason", 10.0),
        ("T1_30DAP", 20.0),
        ("T2_60DAP_reproductive_window_proxy", 30.0),
    ]
    for env_i, env in enumerate(envs.environment):
        for horizon, base in horizons:
            rows.append(
                {
                    "environment": env,
                    "horizon": horizon,
                    "planting_date": envs.loc[env_i, "planting_date"],
                    "uses_future_weather": False,
                    "uses_observed_phenology": False,
                    "ssurgo_mukey": "soil_a" if env_i < 2 else "soil_b",
                    "wx_t2m": base + env_i,
                    "wx_t2m_min": base - 1 + env_i,
                    "wx_t2m_max": base + 1 + env_i,
                    "wx_prectotcorr": base * 2 + env_i,
                    "wx_allsky_sfc_sw_dwn": base * 3 + env_i,
                    "wx_rh2m": 60 + env_i,
                    "wx_ws2m": 2 + env_i / 10,
                }
            )
    states = pd.DataFrame(rows)
    forward = pd.DataFrame(
        {
            "scenario": ["forward_year_2016"],
            "test_year": [2016],
            "environment": ["2016-A"],
            "train_year_max": [2015],
            "admission": ["FORWARD_YEAR_LOCKED"],
        }
    )
    return states, envs, forward


def test_frozen_configuration_is_predeclared_b6r_modal_choice():
    assert FROZEN_CONFIG.g_rank == 20
    assert FROZEN_CONFIG.e_rank == 16
    assert FROZEN_CONFIG.gamma_multiplier == 2.0
    assert FROZEN_CONFIG.alpha == 10.0
    assert tuple(MODEL_ORDER) == ("G", "G+E_T0", "G+E_T1", "G+E_T2")


def test_environment_state_matrices_preserve_three_locked_horizons():
    states, envs, forward = _inputs()
    validate_b9_inputs(states, envs, forward)
    matrices, audit = build_environment_state_matrices(states, envs)
    assert set(matrices) == {
        "T0_preseason",
        "T1_30DAP",
        "T2_60DAP_reproductive_window_proxy",
    }
    columns = None
    for matrix in matrices.values():
        assert list(matrix.index) == ["2014-A", "2015-A", "2016-A"]
        assert not matrix.isna().any().any()
        columns = list(matrix.columns) if columns is None else columns
        assert list(matrix.columns) == columns
    assert len(audit) == 3
    assert not audit["uses_future_weather"].astype(bool).any()
    assert not audit["uses_observed_phenology"].astype(bool).any()
    assert matrices["T0_preseason"].loc["2014-A", "wx_t2m"] == 10.0
    assert matrices["T2_60DAP_reproductive_window_proxy"].loc["2014-A", "wx_t2m"] == 30.0


def test_b10_refuses_future_information():
    states, envs, forward = _inputs()
    states.loc[0, "uses_future_weather"] = True
    with pytest.raises(ValueError, match="future realized weather"):
        validate_b9_inputs(states, envs, forward)


def test_b10_refuses_nonchronological_forward_manifest():
    states, envs, forward = _inputs()
    forward.loc[0, "train_year_max"] = 2016
    with pytest.raises(ValueError, match="temporal order"):
        validate_b9_inputs(states, envs, forward)


def _prediction_frame():
    rows = []
    observed = [0.0, 1.0, 2.0, 3.0]
    envs = ["2016-A", "2016-A", "2017-B", "2017-B"]
    years = [2016, 2016, 2017, 2017]
    preds = {
        "G": [1.0, 2.0, 3.0, 4.0],
        "G+E_T0": [0.8, 1.8, 2.8, 3.8],
        "G+E_T1": [0.5, 1.5, 2.5, 3.5],
        "G+E_T2": [0.1, 1.1, 2.1, 3.1],
    }
    for i, y in enumerate(observed):
        for model in MODEL_ORDER:
            rows.append(
                {
                    "genotype": f"g{i}",
                    "environment": envs[i],
                    "observed": y,
                    "test_year": years[i],
                    "regime": "FORWARD-YEAR-B10",
                    "model": model,
                    "predicted": preds[model][i],
                }
            )
    return pd.DataFrame(rows)


def test_value_of_waiting_is_positive_when_later_state_is_better():
    out = value_of_waiting(_prediction_frame())
    wait = out[out["comparison"].eq("wait_T1_to_T2")].iloc[0]
    assert wait["value_of_waiting_rmse"] > 0
    assert wait["pct_rmse_improvement"] > 0


def test_bootstrap_supports_environment_and_year_clusters():
    out = paired_cluster_bootstrap(_prediction_frame(), reps=50)
    assert set(out["bootstrap_cluster"]) == {"environment", "test_year"}
    assert (out["bootstrap_reps"] == 50).all()
    assert out.loc[out["comparison"].eq("wait_T1_to_T2"), "improvement_frequency"].min() == 1.0
