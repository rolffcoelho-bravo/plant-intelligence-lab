import numpy as np
import pandas as pd

from plant_intelligence.data.maize_environment_transfer import (
    audit_source,
    build_transfer_manifests,
)


def _synthetic():
    genotypes = [f"G{i:02d}" for i in range(10)]
    environments = [f"201{i}_LOC" for i in range(5)]
    pheno = pd.DataFrame(
        [
            {"genotype": g, "year_loc": e, "yield": float(i + j)}
            for i, g in enumerate(genotypes)
            for j, e in enumerate(environments)
        ]
    )
    geno = pd.DataFrame({"id": genotypes, "M1": np.arange(10) % 3, "M2": np.arange(10) % 2})
    ecov = pd.DataFrame(
        {"TEMP": np.arange(5, dtype=float), "RAIN": np.arange(5, dtype=float) * 10.0},
        index=environments,
    )
    return pheno, geno, ecov


def test_audit_resolves_core_modalities():
    pheno, geno, ecov = _synthetic()
    summary, ec_audit, columns = audit_source(pheno, geno, ecov)
    row = summary.iloc[0]
    assert row["n_phenotype_records"] == 50
    assert row["n_phenotype_genotypes"] == 10
    assert row["n_markers"] == 2
    assert row["n_phenotype_environments"] == 5
    assert row["n_environment_covariates_nonconstant"] == 2
    assert row["phenotype_environment_ecov_overlap"] == 5
    assert row["phenotype_genotype_genomic_overlap"] == 10
    assert columns["environment"] == "year_loc"
    assert ec_audit["is_nonconstant_numeric"].all()


def test_transfer_manifests_hold_out_complete_units():
    pheno, geno, ecov = _synthetic()
    _, _, columns = audit_source(pheno, geno, ecov)
    env, genetic, crossed = build_transfer_manifests(pheno, columns)
    assert env["environment"].nunique() == 5
    assert env["environment_fold"].nunique() == 5
    assert genetic["genotype"].nunique() == 10
    assert genetic["genotype_fold"].nunique() == 5
    assert len(crossed) == 25
    assert crossed["scenario"].nunique() == 25
