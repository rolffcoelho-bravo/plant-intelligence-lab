from pathlib import Path

import pandas as pd

from plant_intelligence.data.contracts import (
    CANONICAL_PHENOTYPE_SUMMARY,
    LEGACY_PHENOTYPE_SUMMARY,
    PHENOTYPE_ACCESSIONS,
    validate_case_study_a_interim,
)


def test_case_study_a_contract_creates_compatibility_alias(tmp_path: Path):
    interim = tmp_path / "case_study_a"
    interim.mkdir()

    pd.DataFrame(
        {
            "accession_id": ["1", "2"],
            "phenotype_name": ["shoots 21d protocol a", "shoots 21d protocol a"],
            "phenotype_mean": [0.5, 1.0],
        }
    ).to_csv(interim / CANONICAL_PHENOTYPE_SUMMARY, index=False)

    pd.DataFrame({"accession_id": ["1", "2"]}).to_csv(
        interim / PHENOTYPE_ACCESSIONS, index=False
    )

    manifest = validate_case_study_a_interim(interim)

    assert manifest["status"] == "PASS"
    assert manifest["n_unique_accessions"] == 2
    assert (interim / LEGACY_PHENOTYPE_SUMMARY).exists()
    assert (interim / "artifact_contract.json").exists()
