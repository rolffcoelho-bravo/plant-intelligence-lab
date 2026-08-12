import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_transfer_robustness import (
    GRID,
    BASE,
    choose,
    environment_map,
    novelty,
    sliced,
)
from plant_intelligence.models.maize_environment_transfer import FeatureMap


def test_grid_is_small_locked_and_contains_required_dimensions():
    assert len(GRID) == 9
    assert GRID[0] == BASE
    assert {c.g_rank for c in GRID} == {10, 20, 40}
    assert {c.e_rank for c in GRID} == {8, 16, 32}
    assert {c.gamma_multiplier for c in GRID} == {0.5, 1.0, 2.0}
    assert {c.alpha for c in GRID} == {3.0, 10.0, 30.0}


def test_config_selection_uses_lowest_inner_rmse():
    df = pd.DataFrame({"config": ["baseline", "ridge_3", "ridge_30"], "inner_rmse": [1.0, 0.8, 0.9]})
    assert choose(df) == "ridge_3"


def test_slice_feature_map_renormalizes_requested_rank():
    fmap = FeatureMap(ids=("a", "b"), values=np.ones((2, 4), dtype=np.float32), metadata={"feature_dim": 4})
    result = sliced(fmap, 2)
    assert result.values.shape == (2, 2)
    assert np.allclose(result.values, np.sqrt(2.0))


def test_environment_map_accepts_rank_and_bandwidth():
    ecov = pd.DataFrame(
        np.asarray([[0, 0], [1, 0], [0, 1], [1, 1], [2, 1], [1, 2]], dtype=float),
        index=[f"e{i}" for i in range(6)],
        columns=["x", "y"],
    )
    fmap = environment_map(ecov, {"e0", "e1", "e2", "e3", "e4"}, rank=2, gamma_multiplier=2.0)
    assert fmap.values.shape == (6, 2)
    assert fmap.metadata["gamma_multiplier"] == 2.0


def test_novelty_is_lower_for_near_environment_than_far_environment():
    ecov = pd.DataFrame(
        [[0.0, 0.0], [0.1, 0.0], [0.0, 0.1], [0.1, 0.1], [0.05, 0.05], [5.0, 5.0]],
        index=["t0", "t1", "t2", "t3", "near", "far"],
        columns=["x", "y"],
    )
    out = novelty(ecov, {"t0", "t1", "t2", "t3"}, {"near", "far"}, 1.0).set_index("environment")
    assert out.loc["near", "novelty_mean5_z"] < out.loc["far", "novelty_mean5_z"]
    assert out.loc["near", "max_training_kernel_similarity"] > out.loc["far", "max_training_kernel_similarity"]
