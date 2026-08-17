from pathlib import Path

import pandas as pd
import pytest

from plant_intelligence.uncertainty import maize_b14a_2024_source_compatibility as b14a


def test_blind_tree_rejects_observed_values(tmp_path: Path):
    root = tmp_path / "stage"
    root.mkdir()
    (root / "7_Testing_Observed_Values.csv").write_text("Env,Hybrid,Yield\n", encoding="utf-8")
    with pytest.raises(b14a.OutcomeBoundaryViolation):
        b14a.assert_blind_tree(root)


def test_blind_tree_rejects_trait_or_phenotype_aliases(tmp_path: Path):
    root = tmp_path / "stage"
    root.mkdir()
    (root / "phenotype_backup.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(b14a.OutcomeBoundaryViolation):
        b14a.assert_blind_tree(root)


def test_submission_template_defines_exact_cells():
    frame = pd.DataFrame(
        {
            "Hybrid": ["G2", "G1", "G1", None],
            "Env": ["E2_2024", "E1_2024", "E1_2024", "E1_2024"],
            "Yield": [0, 0, 0, 0],
        }
    )
    cells = b14a.submission_cells(frame)
    assert cells.to_dict("records") == [
        {"genotype": "G1", "environment": "E1_2024"},
        {"genotype": "G2", "environment": "E2_2024"},
    ]


def test_explicit_unique_planting_date_is_required():
    metadata = pd.DataFrame(
        {
            "Env": ["E1_2024", "E1_2024", "E2_2024", "E2_2024"],
            "Date_Planted": ["2024-05-01", "2024-05-01", "2024-05-03", "2024-05-04"],
            "Weather_Station_Latitude": [40.0, 40.0, 41.0, 41.0],
            "Weather_Station_Longitude": [-90.0, -90.0, -91.0, -91.0],
        }
    )
    audit = b14a.build_environment_metadata_audit(metadata, {"E1_2024", "E2_2024"}).set_index("environment")
    assert bool(audit.loc["E1_2024", "t1_metadata_feasible"]) is True
    assert audit.loc["E1_2024", "planting_date"] == "2024-05-01"
    assert bool(audit.loc["E2_2024", "t1_metadata_feasible"]) is False
    assert audit.loc["E2_2024", "t1_metadata_failure_reason"] == "MULTIPLE_DISTINCT_PLANTING_DATES"


def test_weather_station_date_is_never_a_planting_proxy():
    metadata = pd.DataFrame(
        {
            "Env": ["E1_2024"],
            "Date_weather_station_placed": ["2024-04-15"],
            "Weather_Station_Latitude": [40.0],
            "Weather_Station_Longitude": [-90.0],
        }
    )
    audit = b14a.build_environment_metadata_audit(metadata, {"E1_2024"})
    row = audit.iloc[0]
    assert row["explicit_planting_column"] == ""
    assert bool(row["t1_metadata_feasible"]) is False
    assert row["t1_metadata_failure_reason"] == "NO_EXPLICIT_PLANTING_OR_SOWING_COLUMN"
    assert bool(row["weather_station_placement_used_as_planting_proxy"]) is False


def test_missing_submission_environment_is_not_manufactured():
    metadata = pd.DataFrame(
        {
            "Env": ["E1_2024"],
            "Date_Planted": ["2024-05-01"],
            "Latitude": [40.0],
            "Longitude": [-90.0],
        }
    )
    audit = b14a.build_environment_metadata_audit(metadata, {"E1_2024", "E9_2024"}).set_index("environment")
    assert bool(audit.loc["E9_2024", "t1_metadata_feasible"]) is False
    assert audit.loc["E9_2024", "t1_metadata_failure_reason"] == "NO_TESTING_METADATA_ROW_FOR_SUBMISSION_ENVIRONMENT"


def test_candidate_hash_is_order_invariant():
    a = pd.DataFrame({"genotype": ["G2", "G1"], "environment": ["E2", "E1"]})
    b = a.iloc[::-1].reset_index(drop=True)
    assert b14a.canonical_hash(a) == b14a.canonical_hash(b)


def test_empty_candidate_hash_is_explicitly_empty():
    empty = pd.DataFrame(columns=["genotype", "environment"])
    assert b14a.canonical_hash(empty) == ""
