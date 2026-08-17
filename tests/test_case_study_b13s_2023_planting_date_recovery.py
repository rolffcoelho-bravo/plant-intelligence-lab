from pathlib import Path

import pandas as pd
import pytest

from plant_intelligence.uncertainty import maize_b13s_2023_planting_date_recovery as b13s


def frozen_envs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "environment": ["COH1_2023", "IAH1_2023"],
            "source_experiment_code": ["COH1", "IAH1"],
        }
    )


def test_only_single_metadata_object_is_allowlisted():
    b13s.assert_safe_source_path(b13s.SOURCE_RELATIVE_PATH)
    with pytest.raises(b13s.OutcomeBoundaryViolation):
        b13s.assert_safe_source_path("Training_data/1_Training_Trait_Data_2014_2023.csv")
    with pytest.raises(b13s.OutcomeBoundaryViolation):
        b13s.assert_safe_source_path("Training_data/7_Testing_Observed_Values.csv")


def test_blind_tree_rejects_outcome_file(tmp_path: Path):
    (tmp_path / "1_Training_Trait_Data_2014_2023.csv").write_text("x\n1\n")
    with pytest.raises(b13s.OutcomeBoundaryViolation):
        b13s.assert_blind_tree(tmp_path)


def test_exact_explicit_dates_recover_without_proxy_logic():
    metadata = pd.DataFrame(
        {
            "Env": ["COH1_2023", "IAH1_2023"],
            "Year": [2023, 2023],
            "Planting_Date": ["2023-05-12", "2023-05-04"],
            "Anthesis_Date": ["2023-07-10", "2023-07-05"],
            "Harvest_Date": ["2023-10-01", "2023-09-28"],
        }
    )
    recovery, _, decision = b13s.audit_metadata(
        metadata, frozen_envs(), source_sha256="a" * 64
    )
    assert decision["decision"] == b13s.EXACT_RECOVERY
    assert decision["n_admissible_planting_dates"] == 2
    assert set(recovery["recovered_planting_date"]) == {"2023-05-12", "2023-05-04"}
    assert recovery["explicit_planting_semantics"].all()


def test_no_explicit_planting_column_is_clean_no_recovery_even_with_proxy_dates():
    metadata = pd.DataFrame(
        {
            "Env": ["COH1_2023", "IAH1_2023"],
            "Year": [2023, 2023],
            "Date_weather_station_placed": ["2023-05-01", "2023-05-02"],
            "Date_of_application": ["2023-05-03", "2023-05-04"],
            "Anthesis_Date": ["2023-07-10", "2023-07-05"],
        }
    )
    recovery, _, decision = b13s.audit_metadata(
        metadata, frozen_envs(), source_sha256="b" * 64
    )
    assert decision["decision"] == b13s.NO_RECOVERY
    assert decision["n_admissible_planting_dates"] == 0
    assert not recovery["admissible"].any()
    assert decision["source_planting_column"] == ""


def test_multiple_distinct_planting_dates_for_same_environment_is_ambiguous():
    metadata = pd.DataFrame(
        {
            "Env": ["COH1_2023", "COH1_2023", "IAH1_2023"],
            "Year": [2023, 2023, 2023],
            "Planting_Date": ["2023-05-12", "2023-05-13", "2023-05-04"],
        }
    )
    recovery, _, decision = b13s.audit_metadata(
        metadata, frozen_envs(), source_sha256="c" * 64
    )
    assert decision["decision"] == b13s.AMBIGUOUS_MAPPING
    coh = recovery[recovery["environment"].eq("COH1_2023")].iloc[0]
    assert not bool(coh["admissible"])
    assert coh["failure_reason"] == "MULTIPLE_DISTINCT_EXPLICIT_PLANTING_DATES_FOR_ENVIRONMENT"


def test_partial_recovery_does_not_impute_missing_environment():
    metadata = pd.DataFrame(
        {
            "Env": ["COH1_2023"],
            "Year": [2023],
            "Planting_Date": ["2023-05-12"],
        }
    )
    recovery, _, decision = b13s.audit_metadata(
        metadata, frozen_envs(), source_sha256="d" * 64
    )
    assert decision["decision"] == b13s.PARTIAL_RECOVERY
    assert decision["n_admissible_planting_dates"] == 1
    ia = recovery[recovery["environment"].eq("IAH1_2023")].iloc[0]
    assert ia["recovered_planting_date"] == ""
    assert not bool(ia["admissible"])


def test_design_never_changes_point_predictor_clock_or_t2():
    metadata = pd.DataFrame(
        {
            "Env": ["COH1_2023", "IAH1_2023"],
            "Year": [2023, 2023],
            "Planting_Date": ["2023-05-12", "2023-05-04"],
        }
    )
    _, _, decision = b13s.audit_metadata(
        metadata, frozen_envs(), source_sha256="e" * 64
    )
    assert decision["point_predictor_changed"] is False
    assert decision["t1_clock_changed"] is False
    assert decision["t2_branch_reopened"] is False
    assert decision["post_result_tuning_permitted"] is False
