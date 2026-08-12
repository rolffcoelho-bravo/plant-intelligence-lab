import numpy as np
import pandas as pd

from plant_intelligence.models.wheat_gxe_robustness import (
    EXPANDED_GAMMA_GRID,
    LEGACY_GAMMA_GRID,
    _tuning_surface,
)
from plant_intelligence.models.wheat_gxe_baseline import ALPHA_GRID


def test_expanded_gamma_grid_resolves_original_search_boundary():
    assert set(LEGACY_GAMMA_GRID).issubset(set(EXPANDED_GAMMA_GRID))
    assert max(LEGACY_GAMMA_GRID) == 4.0
    assert max(EXPANDED_GAMMA_GRID) == 128.0
    assert len(EXPANDED_GAMMA_GRID) > len(LEGACY_GAMMA_GRID)


def test_tuning_surface_evaluates_all_candidates_and_selects_one():
    genotype_ids = [f"G{i}" for i in range(6)]
    rows = []
    for g_idx, gid in enumerate(genotype_ids):
        for e_idx in range(2):
            rows.append(
                {
                    "genotype_id": gid,
                    "environment": f"E{e_idx}",
                    "g_idx": g_idx,
                    "e_idx": e_idx,
                    "observed": 0.3 * g_idx + 0.7 * e_idx + 0.1 * ((g_idx + e_idx) % 2),
                }
            )
    train = pd.DataFrame(rows)
    k = np.eye(len(genotype_ids))
    gamma_grid = (0.5, 2.0)
    surface = _tuning_surface(train, k, gamma_grid)

    assert len(surface) == len(ALPHA_GRID) * len(gamma_grid)
    assert surface["selected"].sum() == 1
    assert surface.iloc[0]["rank"] == 1
    assert np.isfinite(surface["inner_grouped_rmse"]).all()
