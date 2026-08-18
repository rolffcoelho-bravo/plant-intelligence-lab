from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_readme_matches_release_identity() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lowered = readme.lower()

    assert "applied data science" in lowered
    assert "genomics" in lowered
    assert "case study a" in lowered
    assert "case study b" in lowered
    assert "docs/readme.md" in lowered
    assert "case study b pdf" not in lowered
    assert "pub-b3" not in lowered
    assert "manuscript scaffold" not in lowered


def test_public_documentation_map_exists() -> None:
    index = ROOT / "docs" / "README.md"
    assert index.exists()
    text = index.read_text(encoding="utf-8").lower()
    assert "data-science process" in text
    assert "external evaluation" in text
    assert "machine-readable evidence" in text


def test_publication_production_layer_is_removed() -> None:
    forbidden = [
        ROOT / "docs" / "case_study_b_pub_b1_publication_synthesis_lock.md",
        ROOT / "docs" / "case_study_b_pub_b2_manuscript_scaffold.md",
        ROOT / "reports" / "publication",
        ROOT / "src" / "plant_intelligence" / "publication",
        ROOT / "tests" / "test_case_study_b_pub_b1_publication_lock.py",
        ROOT / "tests" / "test_case_study_b_pub_b2.py",
        ROOT / "tests" / "test_case_study_b_pub_b2_determinism.py",
        ROOT / ".github" / "workflows" / "case-study-b-pub-b1-publication-lock.yml",
        ROOT / ".github" / "workflows" / "case-study-b-pub-b2-manuscript-scaffold.yml",
    ]
    for path in forbidden:
        assert not path.exists(), f"publication-production artifact remains: {path}"


def test_frozen_scientific_evidence_is_preserved() -> None:
    required = [
        ROOT / "reports" / "results" / "case_study_b_closure_lock.json",
        ROOT / "reports" / "results" / "case_study_b_closure_decision.csv",
        ROOT / "reports" / "results" / "case_study_b14b_2024_prediction_seal.json",
        ROOT / "reports" / "results" / "case_study_b14c_2024_primary_summary.csv",
        ROOT / "reports" / "results" / "case_study_b14c_2024_interval_summary.csv",
        ROOT / "reports" / "results" / "case_study_b16_2024_error_structure_summary.csv",
        ROOT / "reports" / "results" / "case_study_b18_decision.csv",
        ROOT / "reports" / "results" / "case_study_b_claim_boundary.csv",
        ROOT / "reports" / "results" / "case_study_b_evidence_hierarchy.csv",
    ]
    for path in required:
        assert path.exists(), f"required frozen evidence missing: {path}"


def test_obsolete_publication_result_names_are_removed() -> None:
    obsolete = [
        "case_study_b_publication_claim_ledger.csv",
        "case_study_b_pub_b1_claim_ledger.csv",
        "case_study_b_pub_b1_evidence_hierarchy.csv",
        "case_study_b_pub_b1_lock.json",
        "case_study_b_pub_b2_lock.json",
        "case_study_b_pub_b2_source_map.csv",
    ]
    results = ROOT / "reports" / "results"
    for name in obsolete:
        assert not (results / name).exists(), f"obsolete publication-stage artifact remains: {name}"
