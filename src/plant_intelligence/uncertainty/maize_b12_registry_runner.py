"""Blind B12A registry runner with conservative competition-header normalization.

Only source/header compatibility and explicit unsupported-input states are handled
here. No outcome, model, calibration, interval, or support logic is changed.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import numpy as np
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
        column.startswith("weatherstationlat") or column in {"latitude", "lat"}
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


def _normalized_metadata(metadata: pd.DataFrame) -> pd.DataFrame:
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
    return frame


def normalized_manifest(metadata: pd.DataFrame, submission: pd.DataFrame) -> pd.DataFrame:
    """Build all requested 2022 environments without imputing missing T1 context."""
    frame = _normalized_metadata(metadata)
    env_col = b12._required(frame, ("Env", "environment", "Environment"), "environment")
    _, sub_env_col = b12.submission_columns(submission)
    requested = set(submission[sub_env_col].dropna().astype(str))

    plant_col = b12.resolve_column(
        frame,
        (
            "Date_Planted",
            "Planting_Date",
            "PlantingDate",
            "date_plant",
            "date_planted",
            "planting_date",
            "Sowing_Date",
        ),
    )
    lat_col = b12.resolve_column(
        frame,
        ("Weather_Station_Latitude", "WeatherStationLatitude", "Latitude", "latitude", "Lat"),
    )
    lon_col = b12.resolve_column(
        frame,
        (
            "Weather_Station_Longitude",
            "WeatherStationLongitude",
            "Longitude",
            "longitude",
            "Lon",
            "Long",
        ),
    )
    city_col = b12.resolve_column(frame, ("City", "city", "Location", "location"))
    pop_col = b12.resolve_column(
        frame,
        ("Plant_Population", "PlantPopulation", "plant_population", "Plant_Density"),
    )

    rows = []
    for environment in sorted(requested):
        part = frame[frame[env_col].astype(str).eq(str(environment))].copy()
        if part.empty:
            rows.append(
                {
                    "environment": str(environment),
                    "year": b12.TARGET_YEAR,
                    "city": "",
                    "planting_date": "",
                    "latitude": np.nan,
                    "longitude": np.nan,
                    "coordinate_source": "G2F_2022_testing_metadata",
                    "historical_year_city_match": "",
                    "plant_population_proxy": np.nan,
                    "n_plot_records": 0,
                }
            )
            continue

        planting = (
            pd.to_datetime(part[plant_col], errors="coerce").dropna().sort_values()
            if plant_col
            else pd.Series(dtype="datetime64[ns]")
        )
        lat = (
            pd.to_numeric(part[lat_col], errors="coerce").dropna()
            if lat_col
            else pd.Series(dtype=float)
        )
        lon = (
            pd.to_numeric(part[lon_col], errors="coerce").dropna()
            if lon_col
            else pd.Series(dtype=float)
        )
        population = np.nan
        if pop_col:
            p = pd.to_numeric(part[pop_col], errors="coerce").dropna()
            if not p.empty:
                population = float(p.median())
        city = ""
        if city_col and part[city_col].notna().any():
            city = str(part[city_col].dropna().astype(str).mode().iloc[0])

        rows.append(
            {
                "environment": str(environment),
                "year": b12.TARGET_YEAR,
                "city": city,
                "planting_date": (
                    planting.iloc[len(planting) // 2].date().isoformat()
                    if not planting.empty
                    else ""
                ),
                "latitude": float(lat.median()) if not lat.empty else np.nan,
                "longitude": float(lon.median()) if not lon.empty else np.nan,
                "coordinate_source": "G2F_2022_testing_metadata",
                "historical_year_city_match": "",
                "plant_population_proxy": population,
                "n_plot_records": int(len(part)),
            }
        )
    return pd.DataFrame(rows).sort_values("environment").reset_index(drop=True)


ORIGINAL_BUILD_STATES = b12.build_2022_t1_states


def build_states_preserving_unsupported(
    manifest: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    planting = manifest["planting_date"].fillna("").astype(str).str.strip()
    lat = pd.to_numeric(manifest["latitude"], errors="coerce")
    lon = pd.to_numeric(manifest["longitude"], errors="coerce")
    complete = planting.ne("") & np.isfinite(lat) & np.isfinite(lon)

    missing = manifest.loc[~complete, ["environment"]].copy()
    missing["environment_input_state"] = b12.UNSUPPORTED_ENVIRONMENT
    missing["reason"] = "missing planting date or coordinates in official 2022 testing metadata"

    supported_manifest = manifest.loc[complete].copy()
    if supported_manifest.empty:
        raise ValueError("B12 has no 2022 environment with complete issuance-time T1 metadata.")
    states, audit = ORIGINAL_BUILD_STATES(supported_manifest)
    audit = pd.concat([audit, missing], ignore_index=True, sort=False)
    return states, audit.sort_values("environment").reset_index(drop=True)


def run(root: Path):
    source._schema_ok = permissive_safe_schema
    b12.competition_environment_manifest = normalized_manifest
    b12.build_2022_t1_states = build_states_preserving_unsupported
    return source.run_stage_a(root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run blind B12A with current CyVerse header normalization."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B12A sealed prediction stage complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
