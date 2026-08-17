"""Canonical B14A runner with an explicit submission-template outcome guard."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plant_intelligence.data.maize_prospective_environment import resolve_column
from plant_intelligence.uncertainty import maize_b14a_2024_source_compatibility as b14a

YIELD_COLUMN_CANDIDATES = (
    "Yield_Mg_ha",
    "Yield",
    "yield",
    "Observed",
    "observed",
    "grain_yield",
)


def submission_template_audit(root: Path) -> pd.DataFrame:
    path = (
        root
        / "data"
        / "raw"
        / "case_study_b14a_2024_safe"
        / b14a.SAFE_FILES["submission"]
    )
    frame = pd.read_csv(path, low_memory=False)
    yield_col = resolve_column(frame, YIELD_COLUMN_CANDIDATES)
    if yield_col is None:
        return pd.DataFrame(
            [
                {
                    "target_year": b14a.TARGET_YEAR,
                    "submission_basename": path.name,
                    "n_rows": int(len(frame)),
                    "prediction_value_column": "",
                    "n_nonempty_prediction_values": -1,
                    "submission_values_blank": False,
                    "observed_values_file_accessed": False,
                    "decision": b14a.OUTCOME_VIOLATION,
                    "reason": "SUBMISSION_TEMPLATE_HAS_NO_RESOLVABLE_PREDICTION_VALUE_COLUMN",
                }
            ]
        )
    values = frame[yield_col]
    nonempty = values.notna() & values.astype(str).str.strip().ne("")
    n_nonempty = int(nonempty.sum())
    return pd.DataFrame(
        [
            {
                "target_year": b14a.TARGET_YEAR,
                "submission_basename": path.name,
                "n_rows": int(len(frame)),
                "prediction_value_column": str(yield_col),
                "n_nonempty_prediction_values": n_nonempty,
                "submission_values_blank": bool(n_nonempty == 0),
                "observed_values_file_accessed": False,
                "decision": "B14A_SUBMISSION_TEMPLATE_BLANK" if n_nonempty == 0 else b14a.OUTCOME_VIOLATION,
                "reason": "" if n_nonempty == 0 else "SUBMISSION_TEMPLATE_CONTAINS_NONEMPTY_YIELD_VALUES",
            }
        ]
    )


def write_submission_template_audit(root: Path) -> Path:
    root = root.resolve()
    out = root / "reports" / "results" / "case_study_b14a_2024_submission_template_audit.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    submission_template_audit(root).to_csv(out, index=False)
    return out


def assert_submission_template_has_no_values(root: Path) -> None:
    audit = submission_template_audit(root)
    row = audit.iloc[0]
    if str(row["decision"]) != "B14A_SUBMISSION_TEMPLATE_BLANK":
        raise b14a.OutcomeBoundaryViolation(str(row["reason"]))


def run(root: Path):
    root = root.resolve()
    b14a.assert_blind_tree(root / "data" / "raw" / "case_study_b14a_2024_safe")
    write_submission_template_audit(root)
    assert_submission_template_has_no_values(root)
    paths = b14a.run(root)
    paths["submission_template_audit"] = (
        root / "reports" / "results" / "case_study_b14a_2024_submission_template_audit.csv"
    )
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run hardened blind B14A 2024 source audit.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    print("Case Study B14A hardened 2024 source compatibility audit complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
