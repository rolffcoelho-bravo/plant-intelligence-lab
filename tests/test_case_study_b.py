from plant_intelligence.data.wheat_gxe import (
    EXPECTED_ENVIRONMENTS,
    build_cv2_sparse,
    build_cv_e,
    build_cv_g,
    build_cv_ge_scenarios,
    environment_metadata,
)


def test_environment_metadata_is_explicit_and_noninvented():
    meta = environment_metadata()
    assert tuple(meta["environment"]) == EXPECTED_ENVIRONMENTS
    assert (meta["environment_type"] == "target_set_of_environments").all()
    assert not meta["continuous_covariates_available"].any()


def test_cv_g_holds_each_genotype_out_once():
    ids = [f"g{i:03d}" for i in range(25)]
    folds = build_cv_g(ids, n_splits=5, seed=7)
    assert len(folds) == len(ids)
    assert folds["genotype_id"].nunique() == len(ids)
    assert set(folds["fold"]) == set(range(5))


def test_cv2_masks_one_environment_per_genotype_and_balances_environments():
    ids = [f"g{i:03d}" for i in range(40)]
    mask = build_cv2_sparse(ids, EXPECTED_ENVIRONMENTS)
    assert len(mask) == len(ids)
    assert mask["genotype_id"].nunique() == len(ids)
    counts = mask["test_environment"].value_counts()
    assert set(counts.index) == set(EXPECTED_ENVIRONMENTS)
    assert counts.max() - counts.min() <= 1


def test_cv_e_is_leave_one_environment_out():
    folds = build_cv_e(EXPECTED_ENVIRONMENTS)
    assert len(folds) == len(EXPECTED_ENVIRONMENTS)
    assert folds["environment"].is_unique
    assert set(folds["fold"]) == set(range(len(EXPECTED_ENVIRONMENTS)))


def test_cv_ge_is_strict_double_cold_start_manifest():
    ids = [f"g{i:03d}" for i in range(20)]
    cv_g = build_cv_g(ids, n_splits=5, seed=11)
    scenarios = build_cv_ge_scenarios(cv_g, EXPECTED_ENVIRONMENTS)
    assert len(scenarios) == 20
    assert (scenarios["admission"] == "stress_test_only").all()
    assert (scenarios["n_test_cells"] == scenarios["n_test_genotypes"]).all()
    assert (
        scenarios["n_train_cells"]
        == scenarios["n_train_genotypes"] * (len(EXPECTED_ENVIRONMENTS) - 1)
    ).all()
