import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "reports" / "results" / "case_study_b_pub_b1_lock.json"
CLAIMS = ROOT / "reports" / "results" / "case_study_b_pub_b1_claim_ledger.csv"
HIERARCHY = ROOT / "reports" / "results" / "case_study_b_pub_b1_evidence_hierarchy.csv"
DOC = ROOT / "docs" / "case_study_b_pub_b1_publication_synthesis_lock.md"


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_pub_b1_lock_is_publication_only_and_parented_to_terminal_b18():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))

    assert lock["stage"] == "PUB-B1"
    assert lock["status"] == "PUB_B1_CASE_STUDY_B_PUBLICATION_SYNTHESIS_LOCKED"
    assert lock["parent_commit"] == "97582638e4926d649df85084b73ff94f9d0f976c"
    assert lock["parent_decision"] == "B18_FORECAST_TIME_INFORMATION_NOVELTY_REJECTED_NO_MODEL_DEVELOPMENT"
    assert lock["publication_frame"] == "SEAL_FIRST_BLINDED_EXTERNAL_VALIDATION_AND_FAILURE_ANALYSIS_NOT_NEW_PREDICTIVE_METHOD"
    assert lock["frozen_predictor"] == "G+E_T1"
    assert lock["frozen_horizon"] == "T1_30DAP"
    assert lock["evidence_frozen_through"] == "B18"
    assert lock["publication_only"] is True


def test_pub_b1_forbids_scientific_reopening_and_b19():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))

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
        "b19_authorized",
        "calendar_time_prospective_2024_wording_permitted",
        "new_predictive_method_claim_permitted",
        "general_seasonal_calibration_law_claim_permitted",
        "support_abstention_validation_claim_permitted",
    ]
    assert all(lock[field] is False for field in forbidden)
    assert lock["pub_b2_authorized"] is True
    assert lock["next_action"] == "PUB_B2_MANUSCRIPT_SCAFFOLD_FROM_FROZEN_CASE_STUDY_B_EVIDENCE_ONLY"


def test_pub_b1_claim_ledger_contains_required_publication_boundaries():
    rows = _rows(CLAIMS)
    ids = [row["claim_id"] for row in rows]
    assert len(ids) == len(set(ids))

    by_id = {row["claim_id"]: row for row in rows}
    assert by_id["PUBB1-C01"]["permitted"] == "True"
    assert by_id["PUBB1-C02"]["permitted"] == "False"
    assert by_id["PUBB1-C03"]["permitted"] == "False"
    assert by_id["PUBB1-C04"]["claim_class"] == "ALLOWED_WITH_DIAGNOSTIC_LABEL"
    assert by_id["PUBB1-C19"]["permitted"] == "False"
    assert by_id["PUBB1-C20"]["claim_class"] == "PRIMARY_NEGATIVE_NOVELTY_RESULT"
    assert by_id["PUBB1-C24"]["permitted"] == "False"
    assert by_id["PUBB1-C25"]["claim_class"] == "PRIMARY_PUBLICATION_FRAME"


def test_pub_b1_evidence_hierarchy_preserves_confirmatory_diagnostic_distinction():
    rows = _rows(HIERARCHY)
    by_stage = {row["stage"]: row for row in rows}

    assert by_stage["B12_PRIMARY"]["evidence_class"] == "ABORTED_CONFIRMATORY"
    assert by_stage["B12_AVAILABLE_CASE"]["evidence_class"] == "DIAGNOSTIC"
    assert by_stage["B14C"]["evidence_class"] == "COMPLETED_CONFIRMATORY_EXTERNAL_EVALUATION"
    assert by_stage["B16"]["evidence_class"] == "POSTOUTCOME_DIAGNOSTIC"
    assert by_stage["B18"]["evidence_class"] == "NEGATIVE_FORECAST_TIME_NOVELTY_AUDIT"
    assert by_stage["PUB_B1"]["terminal_status"] == "PUB_B1_CASE_STUDY_B_PUBLICATION_SYNTHESIS_LOCKED"


def test_pub_b1_document_carries_nonprospective_and_no_b19_warnings():
    text = DOC.read_text(encoding="utf-8")

    assert "seal-first blinded external-validation protocol relative to repository outcome access" in text
    assert "calendar-time prospective" in text
    assert "B19" in text
    assert "does **not** authorize B19" in text
    assert "not a new G×E estimator" in text
