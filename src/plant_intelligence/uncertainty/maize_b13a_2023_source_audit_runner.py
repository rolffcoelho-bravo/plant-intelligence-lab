"""Schema adapter for the official G2F 2023 field-season release.

The 2023 release separates field identity/coordinates from agronomic timing.
This adapter changes only source parsing: it does not alter the merged B13
statistical lock, genotype universe, candidate-universe rule, or phenotype
boundary.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from plant_intelligence.data.maize_prospective_environment import resolve_column
from plant_intelligence.uncertainty import maize_b13_2023_source_audit as b13a


def read_official_safe_table(path: Path) -> pd.DataFrame:
    """Parse an allow-listed G2F table without assuming one CSV dialect/encoding.

    This is a transport/schema normalization only. It never changes values,
    filters rows, or accesses any phenotype path.
    """

    attempts: list[str] = []
    for encoding in ("utf-8-sig", "utf-16", "latin-1"):
        specs: tuple[tuple[object, str], ...] = (
            (",", "comma"),
            ("\t", "tab"),
            (";", "semicolon"),
            ("|", "pipe"),
            (None, "auto"),
        )
        for sep, label in specs:
            try:
                kwargs: dict[str, object] = {"encoding": encoding}
                if sep is None:
                    kwargs.update({"sep": None, "engine": "python"})
                else:
                    kwargs.update({"sep": sep, "engine": "python"})
                frame = pd.read_csv(path, **kwargs)
                if len(frame.columns) >= 2:
                    return frame
                attempts.append(f"{encoding}/{label}: one-column parse")
            except Exception as exc:
                attempts.append(f"{encoding}/{label}: {type(exc).__name__}: {exc}")

    body = path.read_bytes()
    head = body[:160].hex()
    raise ValueError(
        f"B13A cannot parse allow-listed safe table {path.name}; "
        f"size={len(body)} bytes; first160_hex={head}; attempts="
        + " | ".join(attempts[-15:])
    )


def _required(frame: pd.DataFrame, candidates: tuple[str, ...], label: str) -> str:
    hit = resolve_column(frame, candidates)
    if hit is None:
        raise ValueError(f"B13A cannot resolve {label}; columns={list(frame.columns)}")
    return hit


def _canonical_environment(value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("Empty 2023 Experiment_Code.")
    normalized = text.replace("-", "_")
    if normalized.lower().endswith("_2023") or normalized.lower().endswith("2023"):
        return normalized
    return f"{normalized}_2023"


def build_environment_audit_2023(
    field_metadata: pd.DataFrame,
    agronomic: pd.DataFrame,
) -> pd.DataFrame:
    field_env_col = _required(
        field_metadata,
        (
            "Experiment_Code",
            "Experiment Code",
            "Env",
            "Environment",
            "environment",
        ),
        "2023 field experiment identifier",
    )
    agr_env_col = _required(
        agronomic,
        (
            "Experiment_Code",
            "Experiment Code",
            "Env",
            "Environment",
            "environment",
        ),
        "2023 agronomic experiment identifier",
    )
    plant_col = _required(
        agronomic,
        (
            "Date_Planted",
            "Date Planted",
            "Planting_Date",
            "Planting Date",
            "planting_date",
            "PlantingDate",
            "Sowing_Date",
            "Sowing Date",
        ),
        "2023 planting date",
    )
    lat_col = _required(
        field_metadata,
        (
            "Weather_Station_Latitude (in decimal numbers NOT DMS)",
            "Weather_Station_Latitude",
            "WeatherStationLatitude",
            "In-field_weather_station_latitude (in decimal)",
            "Latitude",
            "latitude",
            "Lat",
        ),
        "2023 issuance latitude",
    )
    lon_col = _required(
        field_metadata,
        (
            "Weather_Station_Longitude (in decimal numbers NOT DMS)",
            "Weather_Station_Longitude",
            "WeatherStationLongitude",
            "In-field_weather_station_longitude (in decimal)",
            "Longitude",
            "longitude",
            "Lon",
            "Long",
        ),
        "2023 issuance longitude",
    )
    city_col = resolve_column(field_metadata, ("City", "city"))
    pop_col = resolve_column(
        agronomic,
        (
            "Plant_Population",
            "Plant Population",
            "PlantPopulation",
            "plant_population",
            "Plant_Density",
            "Plants_per_ha",
        ),
    )

    agr = agronomic.copy()
    agr[agr_env_col] = agr[agr_env_col].astype(str).str.strip()
    rows: list[dict[str, object]] = []
    for raw_environment, field_part in field_metadata.groupby(field_env_col, sort=True, dropna=True):
        raw = str(raw_environment).strip()
        if not raw:
            continue
        environment = _canonical_environment(raw)
        agr_part = agr[agr[agr_env_col].eq(raw)]
        planting = pd.to_datetime(agr_part[plant_col], errors="coerce").dropna().sort_values()
        lat = pd.to_numeric(field_part[lat_col], errors="coerce").dropna()
        lon = pd.to_numeric(field_part[lon_col], errors="coerce").dropna()
        population = np.nan
        if pop_col is not None and not agr_part.empty:
            p = pd.to_numeric(agr_part[pop_col], errors="coerce").dropna()
            if not p.empty:
                population = float(p.median())
        city = ""
        if city_col is not None and field_part[city_col].notna().any():
            city = str(field_part[city_col].dropna().astype(str).mode().iloc[0])
        valid = bool(not planting.empty and not lat.empty and not lon.empty)
        rows.append(
            {
                "environment": environment,
                "source_experiment_code": raw,
                "target_year": b13a.TARGET_YEAR,
                "city": city,
                "planting_date": planting.iloc[len(planting) // 2].date().isoformat() if not planting.empty else "",
                "latitude": float(lat.median()) if not lat.empty else np.nan,
                "longitude": float(lon.median()) if not lon.empty else np.nan,
                "plant_population_proxy": population,
                "n_field_metadata_records": int(len(field_part)),
                "n_agronomic_records": int(len(agr_part)),
                "t1_metadata_feasible": valid,
                "weather_window_rule": "PLANTING_THROUGH_30_DAP_ONLY",
                "phenotype_used": False,
            }
        )
    audit = pd.DataFrame(rows)
    if audit.empty:
        raise ValueError("B13A found no 2023 experiments in safe field metadata.")
    if audit["environment"].duplicated().any():
        raise ValueError("Canonical 2023 environment identifiers are not unique.")
    return audit.sort_values("environment").reset_index(drop=True)


def run(root: Path):
    root = root.resolve()
    raw = root / "data/raw/case_study_b13a_2023_safe"
    agr_path = raw / "g2f_2023_agronomic_information.csv"

    original = b13a.build_environment_audit

    def adapter(metadata: pd.DataFrame) -> pd.DataFrame:
        if not agr_path.exists():
            raise ValueError("B13A safe agronomic file is unavailable after allow-listed acquisition.")
        agronomic = read_official_safe_table(agr_path)
        return build_environment_audit_2023(metadata, agronomic)

    b13a.build_environment_audit = adapter
    try:
        return b13a.run(root)
    finally:
        b13a.build_environment_audit = original


def main() -> None:
    parser = argparse.ArgumentParser(description="Run B13A against the official 2023 split field schema.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    print("Case Study B13A 2023 split-schema source audit complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
