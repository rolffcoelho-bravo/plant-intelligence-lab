import json
from pathlib import Path

import pandas as pd
import pytest

from plant_intelligence.uncertainty.maize_external_temporal_validation import (
    FORBIDDEN_ANSWER_BASENAME,
    SEAL_SCHEMA,
    SUPPORTED_ENVIRONMENT,
    SUPPORTED_GENOTYPE,
    UNSUPPORTED_ENVIRONMENT,
    UNSUPPORTED_GENOTYPE,
    SealViolation,
    assert_blind_stage,
    build_supported_test_cells,
    canonical_prediction_bytes,
    competition_environment_manifest,
    verify_prediction_seal,
    write_prediction_seal,
)


def test_blind_stage_rejects_official_answer_file(tmp_path: Path):
    answer = tmp_path / FORBIDDEN_ANSWER_BASENAME
    answer.write_text("Hybrid,Env,Yield_Mg_ha\nx,e,1.0\n", encoding="utf-8")
    with pytest.raises(SealViolation):
        assert_blind_stage([tmp_path])


def test_competition_manifest_uses_input_only_columns():
    metadata = pd.DataFrame(
        {
            "Env": ["E1_2022", "E1_2022", "E2_2022"],
            "City": ["A", "A", "B"],
            "Date_Planted": ["2022-05-01", "2022-05-03", "2022-04-20"],
            "Weather_Station_Latitude": [40.0, 40.2, 41.0],
            "Weather_Station_Longitude": [-90.0, -90.2, -91.0],
            "Plant_Population": [70000, 72000, 68000],
        }
    )
    submission = pd.DataFrame(
        {
            "Hybrid": ["H1", "H2"],
            "Env": ["E1_2022", "E2_2022"],
            "Yield_Mg_ha": [None, None],
        }
    )
    result = competition_environment_manifest(metadata, submission)
    assert result["environment"].tolist() == ["E1_2022", "E2_2022"]
    assert result["year"].eq(2022).all()
    assert result["planting_date"].str.startswith("2022-").all()


def test_supported_subset_never_manufactures_missing_genomic_vectors():
    submission = pd.DataFrame(
        {
            "Hybrid": ["H1", "H2", "H3"],
            "Env": ["E1", "E1", "E2"],
        }
    )
    eligible, audit = build_supported_test_cells(
        submission,
        frozen_genotypes={"H1", "H3"},
        supported_environments={"E1"},
    )
    assert eligible[["genotype", "environment"]].values.tolist() == [["H1", "E1"]]
    states = set(zip(audit["genotype_support_state"], audit["environment_input_state"]))
    assert (SUPPORTED_GENOTYPE, SUPPORTED_ENVIRONMENT) in states
    assert (UNSUPPORTED_GENOTYPE, SUPPORTED_ENVIRONMENT) in states
    assert (SUPPORTED_GENOTYPE, UNSUPPORTED_ENVIRONMENT) in states


def _prediction_frame():
    return pd.DataFrame(
        {
            "genotype": ["H2", "H1"],
            "environment": ["E2", "E1"],
            "predicted": [2.0, 1.0],
            "reliability_state": ["RETAIN_SUPPORTED", "RETAIN_SUPPORTED"],
            "genotype_support_state": [SUPPORTED_GENOTYPE, SUPPORTED_GENOTYPE],
            "lower_90": [1.0, 0.0],
            "upper_90": [3.0, 2.0],
        }
    )


def test_prediction_seal_is_deterministic_and_detects_tampering(tmp_path: Path):
    prediction_path = tmp_path / "predictions.csv"
    seal_path = tmp_path / "seal.json"
    frame = _prediction_frame()
    first = canonical_prediction_bytes(frame)
    second = canonical_prediction_bytes(frame.iloc[::-1].reset_index(drop=True))
    assert first == second

    seal = write_prediction_seal(
        frame,
        prediction_path,
        seal_path,
        {"source_doi": "10.25739/tq5e-ak26"},
    )
    assert seal["schema"] == SEAL_SCHEMA
    verify_prediction_seal(prediction_path, seal_path)

    prediction_path.write_text(
        prediction_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SealViolation):
        verify_prediction_seal(prediction_path, seal_path)


def test_seal_records_no_outcome_access(tmp_path: Path):
    prediction_path = tmp_path / "predictions.csv"
    seal_path = tmp_path / "seal.json"
    write_prediction_seal(
        _prediction_frame(),
        prediction_path,
        seal_path,
        {},
    )
    payload = json.loads(seal_path.read_text(encoding="utf-8"))
    assert payload["observed_outcomes_accessed"] is False
    assert payload["t2_branch_reopened"] is False
    assert payload["post_result_tuning_permitted"] is False
