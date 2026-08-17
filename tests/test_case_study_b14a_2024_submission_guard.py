from pathlib import Path

import pandas as pd
import pytest

from plant_intelligence.uncertainty import maize_b14a_2024_guarded_runner as guarded
from plant_intelligence.uncertainty import maize_b14a_2024_source_compatibility as b14a


def _write_submission(root: Path, values):
    raw = root / "data" / "raw" / "case_study_b14a_2024_safe"
    raw.mkdir(parents=True)
    pd.DataFrame(
        {
            "Env": ["E1_2024", "E2_2024"],
            "Hybrid": ["G1", "G2"],
            "Yield_Mg_ha": values,
        }
    ).to_csv(raw / b14a.SAFE_FILES["submission"], index=False)


def test_blank_submission_prediction_column_is_admissible(tmp_path: Path):
    _write_submission(tmp_path, [None, None])
    guarded.assert_submission_template_has_no_values(tmp_path)


def test_nonempty_submission_prediction_column_aborts_stage_a(tmp_path: Path):
    _write_submission(tmp_path, [None, 7.25])
    with pytest.raises(b14a.OutcomeBoundaryViolation):
        guarded.assert_submission_template_has_no_values(tmp_path)


def test_missing_prediction_column_cannot_be_silently_accepted(tmp_path: Path):
    raw = tmp_path / "data" / "raw" / "case_study_b14a_2024_safe"
    raw.mkdir(parents=True)
    pd.DataFrame({"Env": ["E1_2024"], "Hybrid": ["G1"]}).to_csv(
        raw / b14a.SAFE_FILES["submission"], index=False
    )
    with pytest.raises(b14a.OutcomeBoundaryViolation):
        guarded.assert_submission_template_has_no_values(tmp_path)
