import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_transfer import (
    FeatureMap,
    _attach_folds,
    _metric_row,
    paired_environment_bootstrap,
    tensor_features,
)


def test_tensor_feature_map_matches_product_kernel_identity():
    g = np.asarray([[1.0, 2.0], [3.0, -1.0]], dtype=np.float32)
    e = np.asarray([[2.0, 0.5, 1.0], [-2.0, 1.0, 0.0]], dtype=np.float32)
    ge = tensor_features(g, e)
    observed = float(ge[0] @ ge[1])
    expected = float((g[0] @ g[1]) * (e[0] @ e[1]))
    assert np.isclose(observed, expected)


def test_locked_fold_attachment_covers_cells():
    cells = pd.DataFrame(
        {
            "genotype": ["g1", "g2"],
            "environment": ["e1", "e2"],
            "observed": [1.0, 2.0],
        }
    )
    env = pd.DataFrame({"environment": ["e1", "e2"], "environment_fold": [0, 1]})
    geno = pd.DataFrame({"genotype": ["g1", "g2"], "genotype_fold": [1, 0]})
    attached = _attach_folds(cells, env, geno)
    assert attached["environment_fold"].tolist() == [0, 1]
    assert attached["genotype_fold"].tolist() == [1, 0]


def test_strict_double_cold_start_definition_is_disjoint():
    cells = pd.DataFrame(
        {
            "environment_fold": [0, 0, 1, 1],
            "genotype_fold": [0, 1, 0, 1],
        }
    )
    efold, gfold = 0, 1
    train = cells[(cells["environment_fold"] != efold) & (cells["genotype_fold"] != gfold)]
    test = cells[(cells["environment_fold"] == efold) & (cells["genotype_fold"] == gfold)]
    assert len(test) == 1
    assert not (train["environment_fold"] == efold).any()
    assert not (train["genotype_fold"] == gfold).any()


def test_metrics_are_exact_for_perfect_prediction():
    y = np.asarray([1.0, 2.0, 3.0])
    metrics = _metric_row(y, y.copy())
    assert metrics["rmse"] == 0.0
    assert metrics["mae"] == 0.0
    assert metrics["r2"] == 1.0
    assert np.isclose(metrics["correlation"], 1.0)


def test_environment_cluster_bootstrap_detects_dominant_challenger():
    rows = []
    for env in ["e1", "e2", "e3", "e4"]:
        for i in range(5):
            observed = float(i)
            preds = {
                "G": observed + 1.0,
                "G+E": observed + 0.4,
                "G+E+GxE": observed + 0.1,
            }
            for model, predicted in preds.items():
                rows.append(
                    {
                        "regime": "CV-E-continuous",
                        "genotype": f"g{i}",
                        "environment": env,
                        "observed": observed,
                        "model": model,
                        "predicted": predicted,
                    }
                )
    result = paired_environment_bootstrap(pd.DataFrame(rows), reps=200)
    full_vs_g = result[(result["challenger"] == "G+E+GxE") & (result["reference"] == "G")].iloc[0]
    assert full_vs_g["delta_challenger_minus_reference"] < 0
    assert full_vs_g["ci95_high"] < 0
