from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plant_intelligence.uncertainty import maize_b14b_2024_sealed_prediction as b14b


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "reports" / "results"


def test_merged_b14a_gate_is_exactly_the_frozen_798_cell_universe():
    gate = b14b.verify_b14a_gate(RESULTS)
    row = gate.iloc[0]
    assert row["decision"] == b14b.EXPECTED_B14A_DECISION
    assert int(row["n_candidate_cells"]) == 798
    assert row["candidate_universe_sha256"] == b14b.EXPECTED_CANDIDATE_SHA256


def test_candidate_universe_hash_and_counts_are_immutable():
    cells = b14b.verify_candidate_universe(
        RESULTS / "case_study_b14a_2024_candidate_universe.csv"
    )
    assert len(cells) == 798
    assert cells["genotype"].nunique() == 92
    assert cells["environment"].nunique() == 19


def test_b13_level_is_carried_forward_without_2023_feedback():
    lock = b14b.verify_b13_carry_forward(RESULTS)
    assert np.isclose(
        float(lock.iloc[0]["adaptive_quantile_level"]),
        0.9512813317177465,
        rtol=0,
        atol=1e-15,
    )
    assert b14b.NO_2023_FEEDBACK == (
        "NO_2023_FEEDBACK_AVAILABLE_CARRY_FORWARD_2022_DRIFT_STATE"
    )


def test_adaptive_half_width_cannot_be_narrower_than_control():
    calibration = pd.DataFrame(
        {
            "environment": [f"E{i % 6}" for i in range(240)],
            "support_group": ["WITHIN_TRAINING_NN_ENVELOPE"] * 240,
            "absolute_error": np.linspace(0.01, 4.0, 240),
        }
    )
    control, adaptive, source = b14b.calibration_half_widths(
        calibration, "WITHIN_TRAINING_NN_ENVELOPE"
    )
    assert adaptive >= control
    assert source == "SUPPORT_GROUP_CHRONOLOGICAL_2016_2021"


def test_sparse_support_group_uses_global_fallback():
    calibration = pd.DataFrame(
        {
            "environment": [f"E{i % 8}" for i in range(240)],
            "support_group": ["WITHIN_TRAINING_NN_ENVELOPE"] * 230
            + ["EDGE_OR_OUTSIDE_TRAINING_NN_ENVELOPE"] * 10,
            "absolute_error": np.linspace(0.02, 5.0, 240),
        }
    )
    control, adaptive, source = b14b.calibration_half_widths(
        calibration, "EDGE_OR_OUTSIDE_TRAINING_NN_ENVELOPE"
    )
    assert adaptive >= control
    assert source == "GLOBAL_CHRONOLOGICAL_2016_2021_FALLBACK"


def test_prediction_bytes_are_order_invariant():
    frame = pd.DataFrame(
        {
            "genotype": ["G2", "G1"],
            "environment": ["E2", "E1"],
            "predicted": [2.0, 1.0],
            "control_lower_90": [1.0, 0.0],
            "control_upper_90": [3.0, 2.0],
            "adaptive_lower_90": [0.5, -0.5],
            "adaptive_upper_90": [3.5, 2.5],
            "support_group": ["WITHIN_TRAINING_NN_ENVELOPE"] * 2,
            "reliability_state": ["RETAIN_SUPPORTED"] * 2,
            "calibration_feedback_state": [b14b.NO_2023_FEEDBACK] * 2,
        }
    )
    assert b14b.canonical_prediction_bytes(frame) == b14b.canonical_prediction_bytes(
        frame.iloc[::-1].reset_index(drop=True)
    )


def test_tampered_candidate_universe_is_rejected(tmp_path: Path):
    cells = pd.read_csv(RESULTS / "case_study_b14a_2024_candidate_universe.csv")
    cells.loc[0, "genotype"] = "TAMPERED"
    path = tmp_path / "candidate.csv"
    cells.to_csv(path, index=False)
    with pytest.raises(b14b.B14BSealViolation):
        b14b.verify_candidate_universe(path)
