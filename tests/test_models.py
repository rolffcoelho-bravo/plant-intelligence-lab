import numpy as np
import pandas as pd

from plant_intelligence.models import (
    evaluate_predictions,
    evaluate_regression,
    make_elastic_net,
    make_kernel_ridge,
    make_lightgbm,
    make_random_forest,
    make_xgboost,
)


def toy_regression(seed=7):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(40, 12))
    beta = np.zeros(12)
    beta[:3] = [1.5, -0.8, 0.5]
    y = X @ beta + rng.normal(scale=0.2, size=40)
    return X, y


def test_metrics_are_finite():
    metrics = evaluate_regression([1, 2, 3], [1.1, 1.9, 3.2])
    assert np.isfinite(metrics.rmse)
    assert np.isfinite(metrics.mae)
    assert np.isfinite(metrics.r2)
    assert np.isfinite(metrics.predictive_correlation)
    assert metrics.n == 3


def test_fold_evaluation():
    frame = pd.DataFrame(
        {
            "fold": [0, 0, 1, 1],
            "y_true": [1.0, 2.0, 3.0, 4.0],
            "y_pred": [1.1, 1.8, 3.1, 3.9],
        }
    )
    fold_metrics, overall = evaluate_predictions(frame)
    assert len(fold_metrics) == 2
    assert len(overall) == 1


def test_core_models_fit_and_predict():
    X, y = toy_regression()
    models = [
        make_elastic_net(alpha=0.05, l1_ratio=0.5),
        make_kernel_ridge(alpha=1.0, gamma=0.1),
        make_random_forest(n_estimators=20, n_jobs=1),
        make_xgboost(n_estimators=20, n_jobs=1),
        make_lightgbm(n_estimators=20, n_jobs=1),
    ]

    for model in models:
        model.fit(X, y)
        pred = model.predict(X[:5])
        assert pred.shape == (5,)
        assert np.isfinite(pred).all()
