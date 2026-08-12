import numpy as np

from plant_intelligence.models.wheat_gxe_ml import (
    MODEL_PCA_KERNEL,
    MODEL_RF,
    benchmark_table,
    build_estimator,
    candidate_grid,
    metrics,
)


def test_candidate_grids_are_fixed_and_nonempty():
    assert len(candidate_grid(MODEL_PCA_KERNEL)) == 4
    assert len(candidate_grid(MODEL_RF)) == 3


def test_core_challenger_estimators_fit_finite_predictions():
    rng = np.random.default_rng(11)
    x = rng.normal(size=(80, 25))
    y = 0.8 * x[:, 0] - 0.4 * x[:, 1] + rng.normal(scale=0.2, size=80)
    for model_name, params in (
        (MODEL_PCA_KERNEL, {"n_components": 20, "alpha": 1.0}),
        (MODEL_RF, {"max_features": "sqrt", "min_samples_leaf": 2}),
    ):
        model = build_estimator(model_name, params, seed=11)
        model.fit(x[:60], y[:60])
        pred = model.predict(x[60:])
        assert pred.shape == (20,)
        assert np.isfinite(pred).all()


def test_metrics_identify_perfect_predictions():
    y = np.asarray([-1.0, 0.0, 1.0, 2.0])
    out = metrics(y, y)
    assert np.isclose(out["rmse"], 0.0)
    assert np.isclose(out["mae"], 0.0)
    assert np.isclose(out["r2"], 1.0)
    assert np.isclose(out["rho"], 1.0)


def test_benchmark_table_requires_negative_ci_for_robust_win():
    import pandas as pd

    summary = pd.DataFrame(
        [
            {
                "regime": "CV-G",
                "model": "candidate",
                "n_predictions": 10,
                "n_genotypes": 10,
                "n_environments": 1,
                "rmse": 0.8,
                "mae": 0.6,
                "r2": 0.2,
                "rho": 0.4,
            }
        ]
    )
    envelope = pd.DataFrame([{"regime": "CV-G", "frozen_rmse_threshold": 0.9}])
    bootstrap = pd.DataFrame(
        [
            {
                "regime": "CV-G",
                "candidate_model": "candidate",
                "metric": "rmse",
                "bootstrap_ci_low": -0.2,
                "bootstrap_ci_high": -0.01,
                "bootstrap_probability_improvement": 0.99,
            }
        ]
    )
    out = benchmark_table(summary, envelope, bootstrap).iloc[0]
    assert bool(out["beats_frozen_point_estimate"])
    assert bool(out["robustly_beats_frozen"])
