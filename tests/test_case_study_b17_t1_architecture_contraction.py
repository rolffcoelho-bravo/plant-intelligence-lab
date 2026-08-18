import numpy as np
import pandas as pd

from plant_intelligence.diagnostics.maize_b17_t1_architecture_contraction import (
    DECISION,
    additive_prediction,
    interaction_prediction,
    operator_equivalence_table,
    pairwise_invariance_audit,
    ridge_spectral_filters,
)


def _sealed_like(add_interaction: bool = False) -> pd.DataFrame:
    genotypes = ["G1", "G2", "G3", "G4"]
    g = np.array([-1.5, -0.5, 0.5, 2.0])
    rows = []
    for env, e in (("E1", 0.25), ("E2", 1.50), ("E3", -0.75)):
        if add_interaction:
            p = interaction_prediction(g, np.full_like(g, e), 0.8, 1.2, 0.6, intercept=4.0)
        else:
            p = interaction_prediction(g, np.full_like(g, e), 0.8, 1.2, 0.0, intercept=4.0)
        for genotype, pred in zip(genotypes, p):
            rows.append({"genotype": genotype, "environment": env, "predicted": pred})
    return pd.DataFrame(rows)


def test_additive_g_plus_e_pairwise_contrasts_are_environment_invariant():
    genomic = np.array([[0.0, 1.0], [1.0, -1.0], [2.0, 0.5]])
    beta_g = np.array([1.5, -0.4])
    beta_e = np.array([0.7, -1.2])
    e1 = np.tile(np.array([[0.2, 0.8]]), (3, 1))
    e2 = np.tile(np.array([[1.4, -0.3]]), (3, 1))
    p1 = additive_prediction(genomic, e1, beta_g, beta_e, intercept=2.0)
    p2 = additive_prediction(genomic, e2, beta_g, beta_e, intercept=2.0)
    for i in range(3):
        for j in range(i + 1, 3):
            assert np.isclose(p1[i] - p1[j], p2[i] - p2[j], atol=1e-12, rtol=0.0)


def test_pairwise_invariance_audit_accepts_additive_and_detects_interaction():
    additive = _sealed_like(add_interaction=False)
    audit, summary = pairwise_invariance_audit(additive, tolerance=1e-12)
    assert len(audit) == 3
    assert summary.all_environment_pair_contrasts_invariant_within_seal_precision
    assert summary.max_abs_pairwise_contrast_deviation < 1e-12

    interacting = _sealed_like(add_interaction=True)
    _, interaction_summary = pairwise_invariance_audit(interacting, tolerance=1e-12)
    assert not interaction_summary.all_environment_pair_contrasts_invariant_within_seal_precision
    assert interaction_summary.max_abs_pairwise_contrast_deviation > 0.0


def test_ridge_spectral_filter_is_standard_bounded_attenuation():
    singular = np.array([0.0, 1.0, np.sqrt(10.0), 10.0])
    table = ridge_spectral_filters(singular, alpha=10.0)
    fitted = table["fitted_value_filter_sigma2_over_sigma2_plus_alpha"].to_numpy(float)
    expected = singular**2 / (singular**2 + 10.0)
    assert np.allclose(fitted, expected, atol=0.0, rtol=0.0)
    assert np.all((fitted >= 0.0) & (fitted < 1.0))
    assert np.isclose(fitted[2], 0.5)
    assert table["standard_ridge_prior_art_object"].all()


def test_operator_equivalence_kills_all_candidate_novelty_classes():
    table = operator_equivalence_table()
    assert len(table) == 5
    assert not table["method_novelty_survives"].any()
    target = table.loc[
        table["candidate_object"].eq("CONTRACTION_RELATIVE_TO_UNSEEN_TRUE_ENVIRONMENT_SPECIFIC_RESPONSE")
    ].iloc[0]
    assert target["outcome_free_computable"] == False
    assert "NOT_DISTRIBUTION_FREE_POINT_IDENTIFIED" in target["mathematical_status"]


def test_b17_t1_terminal_decision_is_novelty_rejection():
    assert DECISION == "B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_REJECTED_TERMINATE_B17"
