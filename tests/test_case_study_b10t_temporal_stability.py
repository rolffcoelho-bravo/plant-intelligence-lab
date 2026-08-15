import numpy as np
import pandas as pd

from plant_intelligence.models.maize_geometry_temporal_stability import (
    EXPECTED_YEARS,
    T2_HORIZON,
    adjacent_rank_stability,
    configuration_stability,
    outcome_free_shift_table,
    rank_table,
    shift_associations,
    summary_table,
    validate_inputs,
)


def _inputs(reverse_last=False):
    configs = [f"cfg_{i:02d}" for i in range(12)]
    grid_rows = []
    for yi, year in enumerate(EXPECTED_YEARS):
        order = list(range(12))
        if reverse_last and year == EXPECTED_YEARS[-1]:
            order = list(reversed(order))
        score_by_cfg = {configs[idx]: float(rank + 1) for rank, idx in enumerate(order)}
        for i, config in enumerate(configs):
            grid_rows.append(
                {
                    "test_year": year,
                    "config": config,
                    "e_rank_requested": [8, 16, 32][i // 4],
                    "gamma_multiplier": [0.5, 1.0, 2.0, 4.0][i % 4],
                    "diagnostic_only_no_selection": True,
                    "rmse": score_by_cfg[config],
                    "frozen_t1_rmse": 20.0,
                }
            )
    grid = pd.DataFrame(grid_rows)

    year_rows = []
    kernel_rows = []
    for i, year in enumerate(EXPECTED_YEARS):
        year_rows.append(
            {
                "test_year": year,
                "n_train_environments": 20 + i * 10,
                "median_t2_full_nearest_z": 5.0 - i * 0.2,
                "median_t2_max_kernel_similarity": 0.5 + i * 0.05,
                "median_t2_local_kernel_density5": 0.3 + i * 0.04,
                "median_t2_projection_residual": 0.6 - i * 0.03,
                "median_t2_weather_nearest_z": 1.8 - i * 0.1,
            }
        )
        kernel_rows.append(
            {
                "test_year": year,
                "horizon": T2_HORIZON,
                "full_training_kernel_effective_rank": 13.0 + i,
                "weather_training_kernel_effective_rank": 7.0 + i * 0.5,
                "full_rbf_gamma": 0.03 - i * 0.002,
                "weather_rbf_gamma": 0.16 + i * 0.004,
            }
        )
    return grid, pd.DataFrame(year_rows), pd.DataFrame(kernel_rows)


def test_validate_inputs_accepts_locked_six_year_twelve_geometry_grid():
    grid, years, kernel = _inputs()
    validate_inputs(grid, years, kernel)


def test_identical_rankings_have_perfect_persistence_and_zero_regret():
    grid, _, _ = _inputs()
    ranked = rank_table(grid)
    stability = adjacent_rank_stability(ranked)
    assert len(stability) == 5
    assert np.allclose(stability["spearman_rank_rho"], 1.0)
    assert np.allclose(stability["top3_overlap_fraction"], 1.0)
    assert np.allclose(stability["lagged_winner_regret"], 0.0)
    assert stability["winner_persisted"].all()


def test_rank_reversal_is_detected_as_instability():
    grid, _, _ = _inputs(reverse_last=True)
    ranked = rank_table(grid)
    stability = adjacent_rank_stability(ranked)
    final = stability.iloc[-1]
    assert np.isclose(final["spearman_rank_rho"], -1.0)
    assert np.isclose(final["rank_inversion_score"], 1.0)
    assert final["lagged_winner_next_year_rank"] == 12.0
    assert final["lagged_winner_regret"] > 0


def test_outcome_free_shift_audit_and_summary_are_explicitly_descriptive():
    grid, years, kernel = _inputs(reverse_last=True)
    ranked = rank_table(grid)
    stability = adjacent_rank_stability(ranked)
    configs = configuration_stability(ranked)
    shift = outcome_free_shift_table(stability, years, kernel)
    assoc = shift_associations(shift)
    summary = summary_table(stability, configs)
    assert len(shift) == 5
    assert "outcome_free_shift_index" in shift.columns
    assert len(assoc) == 11
    assert assoc["descriptive_only_small_n"].all()
    assert summary.loc[0, "controller_admission"] == "NOT_JUSTIFIED_BY_RANK_PERSISTENCE_AUDIT"
