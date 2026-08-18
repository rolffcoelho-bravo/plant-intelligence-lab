from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from plant_intelligence.publication.case_study_b_pub_b2 import build_publication_assets

ROOT = Path(__file__).resolve().parents[1]


def _load_json(rel: str):
    return json.loads((ROOT / rel).read_text())


def _assert_csv_float_roundtrip(got, expected) -> None:
    """Accept only machine-precision CSV round-trip differences."""
    assert float(got) == pytest.approx(float(expected), rel=1e-14, abs=1e-14)


def test_pub_b2_lock_inherits_pub_b1_and_forbids_scientific_reopening():
    b1 = _load_json("reports/results/case_study_b_pub_b1_lock.json")
    b2 = _load_json("reports/results/case_study_b_pub_b2_lock.json")

    assert b1["status"] == "PUB_B1_CASE_STUDY_B_PUBLICATION_SYNTHESIS_LOCKED"
    assert b1["pub_b2_authorized"] is True
    assert b2["parent_commit"] == "7bd267138d8481804de393a01870278bc1492619"
    assert b2["parent_status"] == b1["status"]
    assert b2["publication_only"] is True
    assert b2["publication_assets_generated_only_from_committed_frozen_artifacts"] is True

    forbidden = [
        "new_outcome_access_permitted",
        "new_prediction_generation_permitted",
        "model_fitting_permitted",
        "hyperparameter_search_permitted",
        "point_predictor_change_permitted",
        "b5_genotype_representation_change_permitted",
        "t1_clock_change_permitted",
        "t2_reopening_permitted",
        "interval_or_support_tuning_permitted",
        "reseal_permitted",
        "post_result_tuning_permitted",
        "outcome_dependent_cohort_repair_permitted",
        "calendar_time_prospective_2024_wording_permitted",
        "new_predictive_method_claim_permitted",
        "general_seasonal_calibration_law_claim_permitted",
        "support_abstention_validation_claim_permitted",
        "b19_authorized",
        "pub_b3_authorized",
    ]
    assert all(b2[key] is False for key in forbidden)
    assert b2["pub_b3_proposed"] is True


def test_pub_b2_source_map_points_only_to_existing_repository_artifacts():
    source_map = pd.read_csv(ROOT / "reports/results/case_study_b_pub_b2_source_map.csv")
    assert len(source_map) >= 25
    assert source_map["claim_id"].is_unique

    for col in ["authoritative_paths", "supporting_docs"]:
        for packed in source_map[col].dropna().astype(str):
            for rel in packed.split("|"):
                assert (ROOT / rel).exists(), f"Missing mapped source: {rel}"


def test_builder_materializes_all_locked_publication_assets(tmp_path):
    outputs = build_publication_assets(ROOT, tmp_path)
    expected = {
        "table_01_evidence_hierarchy",
        "table_02_external_validation_metrics",
        "table_03_2024_uncertainty_comparison",
        "table_04_2024_failure_structure",
        "figure_01_protocol_chronology",
        "figure_02_2024_external_point_prediction",
        "figure_03_2024_uncertainty_comparison",
        "figure_04_2024_failure_structure",
        "figure_manifest",
        "table_manifest",
        "assets_manifest",
    }
    assert expected.issubset(outputs)
    assert all(path.exists() and path.stat().st_size > 0 for path in outputs.values())
    assert all(outputs[k].suffix == ".svg" for k in expected if k.startswith("figure_0"))


def test_external_validation_publication_table_matches_authoritative_sources(tmp_path):
    outputs = build_publication_assets(ROOT, tmp_path)
    table = pd.read_csv(outputs["table_02_external_validation_metrics"])

    b12 = pd.read_csv(ROOT / "reports/results/case_study_b12_2022_available_case_summary.csv").iloc[0]
    b12cov = pd.read_csv(ROOT / "reports/results/case_study_b12_2022_available_case_coverage.csv")
    b12cov = b12cov.loc[b12cov["nominal"].eq(0.9)].iloc[0]
    b14 = pd.read_csv(ROOT / "reports/results/case_study_b14c_2024_primary_summary.csv").iloc[0]
    b14cov = pd.read_csv(ROOT / "reports/results/case_study_b14c_2024_interval_summary.csv")
    b14cov = b14cov.loc[b14cov["rule"].eq("FROZEN_B11_90")].iloc[0]

    row12 = table.loc[table["stage"].eq("B12_AVAILABLE_CASE")].iloc[0]
    assert bool(row12["confirmatory"]) is False
    assert int(row12["n"]) == int(b12["n_evaluated_available_cases"]) == 387
    _assert_csv_float_roundtrip(row12["rmse"], b12["rmse"])
    _assert_csv_float_roundtrip(row12["coverage_90"], b12cov["empirical_coverage"])
    _assert_csv_float_roundtrip(row12["environment_balanced_coverage_90"], b12cov["environment_balanced_coverage"])

    row14 = table.loc[table["stage"].eq("B14C")].iloc[0]
    assert bool(row14["confirmatory"]) is True
    assert int(row14["n"]) == int(b14["n_officially_observable"]) == 779
    _assert_csv_float_roundtrip(row14["rmse"], b14["rmse"])
    _assert_csv_float_roundtrip(row14["coverage_90"], b14cov["empirical_coverage"])
    _assert_csv_float_roundtrip(row14["environment_balanced_coverage_90"], b14cov["environment_balanced_coverage"])


def test_uncertainty_and_failure_tables_preserve_authoritative_values(tmp_path):
    outputs = build_publication_assets(ROOT, tmp_path)

    t3 = pd.read_csv(outputs["table_03_2024_uncertainty_comparison"])
    src3 = pd.read_csv(ROOT / "reports/results/case_study_b14c_2024_interval_summary.csv")
    pd.testing.assert_frame_equal(
        t3.drop(columns=["publication_decision"]),
        src3,
        check_dtype=False,
    )
    assert t3.loc[t3["rule"].eq("FROZEN_B11_90"), "publication_decision"].iloc[0] == "RETAIN_FROZEN_CONTROL"
    assert t3.loc[t3["rule"].eq("ONE_SIDED_CLUSTER_DRIFT_GUARD_90"), "publication_decision"].iloc[0] == "REJECT_PROMOTION"

    t4 = pd.read_csv(outputs["table_04_2024_failure_structure"]).iloc[0]
    src4 = pd.read_csv(ROOT / "reports/results/case_study_b16_2024_error_structure_summary.csv").iloc[0]
    _assert_csv_float_roundtrip(t4["environment_bias_sse_fraction"], src4["environment_bias_sse_fraction"])
    _assert_csv_float_roundtrip(t4["within_environment_sse_fraction"], src4["within_environment_sse_fraction"])
    _assert_csv_float_roundtrip(t4["median_predicted_to_observed_sd_ratio"], src4["median_predicted_to_observed_sd_ratio"])


def test_pub_b2_assets_manifest_hashes_every_frozen_input(tmp_path):
    outputs = build_publication_assets(ROOT, tmp_path)
    manifest = pd.read_csv(outputs["assets_manifest"])
    inputs = manifest.loc[manifest["kind"].eq("INPUT")]
    assert len(inputs) == 7
    assert inputs["sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert manifest.loc[manifest["kind"].eq("OUTPUT"), "sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
