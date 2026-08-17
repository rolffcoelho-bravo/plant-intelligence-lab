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


def assert_submission_template_has_no_values(root: Path) -> None:
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
        raise b14a.OutcomeBoundaryViolation(
            "B14A cannot verify the submission template because no prediction-value column was found."
        )
    values = frame[yield_col]
    nonempty = values.notna() & values.astype(str).str.strip().ne("")
    if bool(nonempty.any()):
        raise b14a.OutcomeBoundaryViolation(
            "B14A submission template contains non-empty yield values; Stage A refuses to continue."
        )


def run(root: Path):
    root = root.resolve()
    b14a.assert_blind_tree(root / "data" / "raw" / "case_study_b14a_2024_safe")
    assert_submission_template_has_no_values(root)
    return b14a.run(root)


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
