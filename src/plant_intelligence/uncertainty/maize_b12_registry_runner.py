"""Blind B12A registry runner with conservative competition-header normalization.

Only source/header compatibility is handled here. No outcome, model, calibration,
interval, or support logic is changed.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import pandas as pd

from plant_intelligence.uncertainty import maize_b12_cyverse_source as source
from plant_intelligence.uncertainty import maize_external_temporal_validation as b12


def _norm(value: object) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def permissive_safe_schema(basename: str, body: bytes) -> bool:
    """Accept only the two allow-listed CSV schemas, allowing descriptive suffixes."""
    if basename not in source.SAFE_BASENAMES:
        return False
    try:
        frame = pd.read_csv(io.BytesIO(body), nrows=0)
    except Exception:
        return False
    columns = [_norm(column) for column in frame.columns]
    has_env = any(column in {"env", "environment"} for column in columns)
    if not has_env:
        return False
    if basename == "1_Submission_Template_2022.csv":
        return any(column in {"hybrid", "genotype"} for column in columns)
    has_lat = any(
        column.startswith("weatherstationlat")
        or column in {"latitude", "lat"}
        for column in columns
    )
    has_lon = any(
        column.startswith("weatherstationlong")
        or column in {"longitude", "lon", "long"}
        for column in columns
    )
    return has_lat and has_lon


def _rename_prefix(frame: pd.DataFrame, canonical: str, prefixes: tuple[str, ...]) -> pd.DataFrame:
    if canonical in frame.columns:
        return frame
    normalized_prefixes = tuple(_norm(prefix) for prefix in prefixes)
    matches = [
        column
        for column in frame.columns
        if any(_norm(column).startswith(prefix) for prefix in normalized_prefixes)
    ]
    if len(matches) == 1:
        return frame.rename(columns={matches[0]: canonical})
    return frame


def normalized_manifest(metadata: pd.DataFrame, submission: pd.DataFrame) -> pd.DataFrame:
    frame = metadata.copy()
    frame = _rename_prefix(
        frame,
        "Weather_Station_Latitude",
        ("Weather_Station_Latitude", "WeatherStationLatitude"),
    )
    frame = _rename_prefix(
        frame,
        "Weather_Station_Longitude",
        ("Weather_Station_Longitude", "WeatherStationLongitude"),
    )
    frame = _rename_prefix(
        frame,
        "Date_Planted",
        (
            "Date_Planted",
            "DatePlanted",
            "Planting_Date",
            "PlantingDate",
            "Sowing_Date",
            "SowingDate",
        ),
    )
    return ORIGINAL_MANIFEST(frame, submission)


ORIGINAL_MANIFEST = b12.competition_environment_manifest


def run(root: Path):
    source._schema_ok = permissive_safe_schema
    b12.competition_environment_manifest = normalized_manifest
    return source.run_stage_a(root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run blind B12A with current CyVerse header normalization.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B12A sealed prediction stage complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
