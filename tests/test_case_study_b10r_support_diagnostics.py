import numpy as np
import pandas as pd

from plant_intelligence.models.maize_forward_support_diagnostics import (
    DIAGNOSTIC_E_RANKS,
    DIAGNOSTIC_GAMMA_MULTIPLIERS,
    DIAGNOSTIC_GRID,
    association_table,
    build_t2_failure_table,
    support_geometry,
)
from plant_intelligence.models.maize_forecast_time_prediction import FROZEN_CONFIG


def test_support_geometry_flags_distant_state_as_more_novel():
    frame = pd.DataFrame(
        {
            "x": [0.0, 0.2, -0.2, 0.1, 5.0],
            "y": [0.0, 0.1, -0.1, -0.2, 5.0],
        },
        index=["tr1", "tr2", "tr3", "near", "far"],
    )
    out, geom = support_geometry(
        frame,
        {"tr1", "tr2", "tr3"},
        {"near", "far"},
        gamma_multiplier=2.0,
        retained_rank=2,
        prefix="full",
    )
    out = out.set_index("environment")
    assert out.loc["far", "full_nearest_z"] > out.loc["near", "full_nearest_z"]
    assert out.loc["far", "full_max_training_kernel_similarity"] < out.loc["near", "full_max_training_kernel_similarity"]
    assert out.loc["far", "full_kernel_projection_residual"] >= out.loc["near", "full_kernel_projection_residual"]
    assert 0.0 <= out.loc["far", "full_kernel_projection_support"] <= 1.0
    assert geom.effective_rank > 0.0


def _support_rows():
    rows = []
    for environment, year, error_shift, t1_novelty, t2_novelty in [
        ("2016-A", 2016, 1.0, 0.5, 2.0),
        ("2016-B", 2016, 0.8, 0.6, 1.8),
        ("2017-A", 2017, -0.1, 0.5, 0.7),
        ("2017-B", 2017, 0.0, 0.4, 0.6),
    ]:
        for model, novelty, rmse in [
            ("G+E_T1", t1_novelty, 1.0),
            ("G+E_T2", t2_novelty, 1.0 + error_shift),
        ]:
            rows.append(
                {
                    "environment": environment,
                    "test_year": year,
                    "train_year_max": year - 1,
                    "n_train_environments": 20 if year == 2016 else 40,
                    "n_test_environments": 2,
                    "model": model,
                    "rmse": rmse,
                    "mae": rmse,
                    "full_nearest_z": novelty,
                    "full_mean5_z": novelty + 0.1,
                    "full_nearest_percentile": min(1.0, novelty / 2.0),
                    "full_max_training_kernel_similarity": 1.0 / (1.0 + novelty),
                    "full_local_kernel_density5": 1.0 / (1.0 + novelty),
                    "full_kernel_mass": 2.0 / (1.0 + novelty),
                    "full_kernel_projection_support": max(0.0, 1.0 - novelty / 3.0),
                    "full_kernel_projection_residual": min(1.0, novelty / 3.0),
                    "weather_nearest_z": novelty,
                    "weather_mean5_z": novelty + 0.1,
                    "weather_nearest_percentile": min(1.0, novelty / 2.0),
                    "weather_max_training_kernel_similarity": 1.0 / (1.0 + novelty),
                    "weather_local_kernel_density5": 1.0 / (1.0 + novelty),
                    "weather_kernel_projection_support": max(0.0, 1.0 - novelty / 3.0),
                    "weather_kernel_projection_residual": min(1.0, novelty / 3.0),
                    "nearest_training_location_km": novelty * 10.0,
                    "city_seen_previously": year > 2016,
                    "coordinate_seen_previously": year > 2016,
                    "soil_mukey_seen_previously": True,
                }
            )
    return pd.DataFrame(rows)


def test_t2_failure_table_preserves_direction_of_support_shift():
    failure = build_t2_failure_table(_support_rows())
    row = failure[failure.environment.eq("2016-A")].iloc[0]
    assert np.isclose(row.rmse_t2_minus_t1, 1.0)
    assert row.delta_full_nearest_z_t2_minus_t1 > 0
    assert row.delta_full_max_training_kernel_similarity_t2_minus_t1 < 0
    assert bool(row.t2_worse_than_t1)


def test_association_table_relates_support_to_t2_deterioration_without_selection():
    failure = build_t2_failure_table(_support_rows())
    out = association_table(failure)
    nearest = out[out.feature.eq("t2_full_nearest_z")].iloc[0]
    similarity = out[out.feature.eq("t2_full_max_training_kernel_similarity")].iloc[0]
    assert nearest.pooled_spearman > 0
    assert similarity.pooled_spearman < 0


def test_geometry_grid_is_diagnostic_and_contains_frozen_b10_cell():
    assert set(DIAGNOSTIC_E_RANKS) == {8, 16, 32}
    assert set(DIAGNOSTIC_GAMMA_MULTIPLIERS) == {0.5, 1.0, 2.0, 4.0}
    assert len(DIAGNOSTIC_GRID) == 12
    matches = [
        cfg
        for cfg in DIAGNOSTIC_GRID
        if cfg.e_rank == FROZEN_CONFIG.e_rank
        and cfg.gamma_multiplier == FROZEN_CONFIG.gamma_multiplier
        and cfg.alpha == FROZEN_CONFIG.alpha
        and cfg.g_rank == FROZEN_CONFIG.g_rank
    ]
    assert len(matches) == 1
