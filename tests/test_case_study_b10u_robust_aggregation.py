import numpy as np
import pandas as pd

from plant_intelligence.models.maize_geometry_robust_aggregation import (
    AGGREGATE_MODELS,
    MODEL_ORDER,
    aggregate_geometry_predictions,
    paired_cluster_bootstrap,
    stopping_decision,
    validate_geometry_family,
)


def test_geometry_family_is_exact_frozen_b10r_grid():
    validate_geometry_family()


def test_mean_and_median_aggregation_are_symmetric_and_exact():
    matrix = np.vstack([
        np.arange(12, dtype=float),
        np.arange(12, dtype=float) * 2.0,
    ])
    mean12, median12 = aggregate_geometry_predictions(matrix)
    assert np.allclose(mean12, [5.5, 11.0])
    assert np.allclose(median12, [5.5, 11.0])


def _synthetic_predictions():
    rows = []
    observed = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    years = [2016, 2016, 2017, 2017, 2018, 2018]
    envs = ["2016-A", "2016-A", "2017-B", "2017-B", "2018-C", "2018-C"]
    # Aggregates are deliberately better than T1; frozen T2 has a catastrophic
    # first year so the stop-rule stability component can be tested separately.
    model_predictions = {
        "Frozen-T1": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
        "Frozen-T2": [3.0, 4.0, 2.6, 3.6, 4.6, 5.6],
        "T2-Mean12": [0.1, 1.1, 2.1, 3.1, 4.1, 5.1],
        "T2-Median12": [0.2, 1.2, 2.2, 3.2, 4.2, 5.2],
    }
    for i, y in enumerate(observed):
        for model in MODEL_ORDER:
            rows.append(
                {
                    "genotype": f"g{i}",
                    "environment": envs[i],
                    "observed": y,
                    "test_year": years[i],
                    "model": model,
                    "predicted": model_predictions[model][i],
                }
            )
    return pd.DataFrame(rows)


def _summaries(predictions):
    pooled = []
    years = []
    for model, part in predictions.groupby("model"):
        err = part.observed.to_numpy(float) - part.predicted.to_numpy(float)
        pooled.append({"model": model, "rmse": float(np.sqrt(np.mean(err**2)))})
    for (year, model), part in predictions.groupby(["test_year", "model"]):
        err = part.observed.to_numpy(float) - part.predicted.to_numpy(float)
        years.append({"test_year": year, "model": model, "rmse": float(np.sqrt(np.mean(err**2)))})
    return pd.DataFrame(pooled), pd.DataFrame(years)


def test_bootstrap_contains_both_cluster_views_and_all_aggregate_comparisons():
    out = paired_cluster_bootstrap(_synthetic_predictions(), reps=100)
    assert set(out.bootstrap_cluster) == {"environment", "test_year"}
    assert set(out.challenger) == set(AGGREGATE_MODELS)
    assert len(out) == 8
    vs_t1 = out[out.reference.eq("Frozen-T1")]
    assert (vs_t1.delta_rmse_challenger_minus_reference < 0).all()


def test_stopping_rule_can_admit_only_robust_and_stabilizing_aggregate():
    predictions = _synthetic_predictions()
    pooled, years = _summaries(predictions)
    bootstrap = paired_cluster_bootstrap(predictions, reps=200)
    decision = stopping_decision(pooled, years, bootstrap)
    # Synthetic data are intentionally unambiguous enough that both aggregates
    # beat T1 and reduce frozen-T2 worst-year/range.
    assert decision.robust_pooled_improvement_over_t1.all()
    assert decision.reduced_catastrophic_instability_vs_frozen_t2.all()
    assert decision.aggregate_admitted.all()
    assert set(decision.branch_decision) == {"KEEP_T2_AGGREGATION_BRANCH_OPEN"}


def test_stopping_rule_closes_branch_when_t1_is_not_robustly_beaten():
    predictions = _synthetic_predictions().copy()
    # Make both aggregates worse than T1 while leaving frozen T2 unchanged.
    mask = predictions.model.isin(AGGREGATE_MODELS)
    predictions.loc[mask, "predicted"] = predictions.loc[mask, "observed"] + 0.8
    pooled, years = _summaries(predictions)
    bootstrap = paired_cluster_bootstrap(predictions, reps=100)
    decision = stopping_decision(pooled, years, bootstrap)
    assert not decision.aggregate_admitted.any()
    assert set(decision.branch_decision) == {"CLOSE_T2_ADAPTIVE_BRANCH_USE_SUPPORTED_T1"}
    assert not decision.post_result_tuning_permitted.any()
