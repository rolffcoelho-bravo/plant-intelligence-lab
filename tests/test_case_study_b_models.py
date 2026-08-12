import numpy as np
import pandas as pd

from plant_intelligence.models.wheat_gxe_baseline import (
    MODEL_ENV,
    MODEL_G,
    MODEL_GE,
    MODEL_GXE,
    _kernel_cross_predict,
    _kernel_train_matvec,
    build_splits,
    fit_model,
    genomic_relationship,
    predict_model,
)
from plant_intelligence.data.wheat_gxe import (
    build_cv2_sparse,
    build_cv_e,
    build_cv_g,
    build_cv_ge_scenarios,
)


def test_genomic_relationship_is_symmetric_and_normalized():
    geno = pd.DataFrame(
        {
            "m1": [0, 1, 2, 1, 0, 2],
            "m2": [2, 2, 1, 0, 0, 1],
            "m3": [0, 1, 0, 1, 2, 2],
            "constant": [1, 1, 1, 1, 1, 1],
        }
    )
    k, audit = genomic_relationship(geno)
    assert k.shape == (6, 6)
    assert np.allclose(k, k.T)
    assert np.isclose(np.mean(np.diag(k)), 1.0)
    assert audit["markers_nonconstant"] == 3.0


def test_structured_kernel_matches_dense_kernel():
    k = np.asarray(
        [
            [1.0, 0.2, -0.1],
            [0.2, 1.0, 0.3],
            [-0.1, 0.3, 1.0],
        ]
    )
    train_g = np.asarray([0, 0, 1, 1, 2, 2])
    train_e = np.asarray([0, 1, 0, 1, 0, 1])
    vector = np.asarray([0.4, -0.2, 1.1, 0.3, -0.8, 0.5])
    gamma = 0.7
    dense = k[np.ix_(train_g, train_g)]
    dense += gamma * dense * (train_e[:, None] == train_e[None, :])
    structured = _kernel_train_matvec(vector, train_g, train_e, k, gamma)
    assert np.allclose(structured, dense @ vector)

    coefficients = np.asarray([0.1, -0.3, 0.6, 0.5, -0.2, 0.8])
    test_g = np.asarray([2, 0, 1])
    test_e = np.asarray([0, 1, 1])
    cross = k[np.ix_(test_g, train_g)]
    cross += gamma * cross * (test_e[:, None] == train_e[None, :])
    structured_pred = _kernel_cross_predict(
        coefficients, train_g, train_e, test_g, test_e, k, gamma
    )
    assert np.allclose(structured_pred, cross @ coefficients)


def test_environment_mean_uses_seen_environment_and_global_fallback():
    k = np.eye(3)
    y = np.asarray([1.0, 3.0, 10.0, 14.0])
    train_g = np.asarray([0, 1, 0, 1])
    train_e = np.asarray([0, 0, 1, 1])
    fitted = fit_model(y, train_g, train_e, k, MODEL_ENV)
    pred = predict_model(
        fitted,
        np.asarray([2, 2, 2]),
        np.asarray([0, 1, 2]),
        k,
    )
    assert np.allclose(pred[:2], [2.0, 12.0])
    assert np.isclose(pred[2], np.mean(y))


def test_kernel_models_fit_finite_predictions():
    k = np.asarray(
        [
            [1.0, 0.3, 0.1, 0.0],
            [0.3, 1.0, 0.2, 0.1],
            [0.1, 0.2, 1.0, 0.4],
            [0.0, 0.1, 0.4, 1.0],
        ]
    )
    train_g = np.repeat(np.arange(4), 2)
    train_e = np.tile(np.arange(2), 4)
    y = 0.4 * train_g + 0.7 * train_e + np.asarray([0.0, 0.1, -0.1, 0.0, 0.2, 0.1, 0.0, -0.2])
    for model_name, gamma in ((MODEL_G, 0.0), (MODEL_GE, 0.0), (MODEL_GXE, 1.0)):
        fitted = fit_model(y, train_g, train_e, k, model_name, alpha=1.0, gamma=gamma)
        pred = predict_model(fitted, np.asarray([0, 3]), np.asarray([1, 0]), k)
        assert np.isfinite(pred).all()
        assert fitted.cg_iterations > 0


def test_locked_split_builder_has_expected_counts_and_no_leakage():
    genotype_ids = [f"W{i:03d}" for i in range(1, 21)]
    environments = ("ME1", "ME2", "ME3", "ME4")
    rows = []
    for g_idx, gid in enumerate(genotype_ids):
        for e_idx, env in enumerate(environments):
            rows.append(
                {
                    "genotype_id": gid,
                    "environment": env,
                    "g_idx": g_idx,
                    "e_idx": e_idx,
                    "observed": float(g_idx + e_idx),
                }
            )
    cells = pd.DataFrame(rows)
    cv_g = build_cv_g(genotype_ids, n_splits=5, seed=11)
    cv2 = build_cv2_sparse(genotype_ids, environments)
    cv_e = build_cv_e(environments)
    cv_ge = build_cv_ge_scenarios(cv_g, environments)
    splits = build_splits(cells, cv_g, cv2, cv_e, cv_ge)

    counts = pd.Series([s.regime for s in splits]).value_counts().to_dict()
    assert counts == {"CV-GE": 20, "CV-G": 5, "CV-E": 4, "CV2": 1}

    for split in splits:
        train = cells.iloc[split.train_index]
        test = cells.iloc[split.test_index]
        if split.regime == "CV-G":
            assert set(train["genotype_id"]).isdisjoint(set(test["genotype_id"]))
        elif split.regime == "CV2":
            assert len(test) == len(genotype_ids)
            assert test["genotype_id"].nunique() == len(genotype_ids)
        elif split.regime == "CV-E":
            assert set(train["environment"]).isdisjoint(set(test["environment"]))
        elif split.regime == "CV-GE":
            assert set(train["genotype_id"]).isdisjoint(set(test["genotype_id"]))
            assert set(train["environment"]).isdisjoint(set(test["environment"]))
