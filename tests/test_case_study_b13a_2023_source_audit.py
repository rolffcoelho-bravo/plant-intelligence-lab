from pathlib import Path

import pandas as pd
import pytest

from plant_intelligence.uncertainty import maize_b13_2023_source_audit as b13a


def test_phenotype_directory_and_file_are_forbidden_before_request():
    with pytest.raises(b13a.OutcomeBoundaryViolation):
        b13a.assert_safe_remote_path(
            "a._2023_phenotypic_data/g2f_2023_phenotypic_data.csv"
        )
    with pytest.raises(b13a.OutcomeBoundaryViolation):
        b13a.assert_safe_remote_path("g2f_2023_phenotypic_data.csv")


def test_only_explicit_safe_basenames_are_allowlisted():
    for relative in b13a.SAFE_REMOTE_PATHS.values():
        b13a.assert_safe_remote_path(relative)
    with pytest.raises(b13a.OutcomeBoundaryViolation):
        b13a.assert_safe_remote_path("z._2023_supplemental_info/unregistered.csv")


def test_candidate_universe_is_cartesian_product_and_outcome_independent():
    genotypes = pd.DataFrame({"genotype": ["G2", "G1"]})
    environments = pd.DataFrame(
        {
            "environment": ["E2", "E1", "E_BAD"],
            "t1_metadata_feasible": [True, True, False],
        }
    )
    cells, digest = b13a.candidate_universe(genotypes, environments)
    assert len(cells) == 4
    assert set(map(tuple, cells[["genotype", "environment"]].to_numpy())) == {
        ("G1", "E1"),
        ("G2", "E1"),
        ("G1", "E2"),
        ("G2", "E2"),
    }
    assert len(digest) == 64
    assert "observed" not in cells.columns


def test_candidate_universe_hash_is_deterministic_under_input_order():
    g1 = pd.DataFrame({"genotype": ["B", "A"]})
    g2 = pd.DataFrame({"genotype": ["A", "B"]})
    e1 = pd.DataFrame({"environment": ["Y", "X"], "t1_metadata_feasible": [True, True]})
    e2 = pd.DataFrame({"environment": ["X", "Y"], "t1_metadata_feasible": [True, True]})
    _, h1 = b13a.candidate_universe(g1, e1)
    _, h2 = b13a.candidate_universe(g2, e2)
    assert h1 == h2


def test_safe_environment_audit_requires_issuance_fields_only():
    metadata = pd.DataFrame(
        {
            "Env": ["X_2023", "X_2023", "Y_2023"],
            "Planting_Date": ["2023-05-01", "2023-05-03", None],
            "Latitude": [40.0, 40.2, 41.0],
            "Longitude": [-90.0, -90.2, -91.0],
            "Plant_Population": [70000, 71000, 72000],
        }
    )
    audit = b13a.build_environment_audit(metadata)
    x = audit[audit["environment"].eq("X_2023")].iloc[0]
    y = audit[audit["environment"].eq("Y_2023")].iloc[0]
    assert bool(x["t1_metadata_feasible"])
    assert not bool(y["t1_metadata_feasible"])
    assert not bool(audit["phenotype_used"].any())


def test_blind_tree_rejects_phenotype_file(tmp_path: Path):
    safe = tmp_path / "safe"
    safe.mkdir()
    (safe / b13a.FORBIDDEN_BASENAME).write_text("x\n1\n", encoding="utf-8")
    with pytest.raises(b13a.OutcomeBoundaryViolation):
        b13a.assert_blind_tree(safe)


def test_expected_b13_lock_level_is_exactly_preserved():
    assert b13a.EXPECTED_B13_ADAPTIVE_LEVEL == pytest.approx(
        0.9512813317177465, abs=1e-15
    )
    assert b13a.TARGET_YEAR == 2023


def test_b13a_never_reopens_t2_or_changes_point_predictor_by_design():
    assert b13a.READY == "B13A_2023_SOURCE_COMPATIBLE_READY_FOR_SEAL"
    assert b13a.FORBIDDEN_PATH_TOKEN not in " ".join(b13a.SAFE_REMOTE_PATHS.values())
