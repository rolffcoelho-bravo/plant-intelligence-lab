"""Canonical B13A blind source audit for the official G2F 2023 release.

This runner treats a clean negative compatibility result as a completed audit.
It never substitutes weather-station placement or treatment-application dates
for planting date. If the allow-listed 2023 sources do not expose an explicit
planting date, the machine state is B13A_2023_T1_CONTEXT_INSUFFICIENT and no
candidate prediction cells are manufactured.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from plant_intelligence.data.maize_prospective_environment import resolve_column
from plant_intelligence.uncertainty import maize_b13_2023_source_audit as b13a
from plant_intelligence.uncertainty import maize_b13a_2023_source_audit_runner as schema
from plant_intelligence.uncertainty import maize_b13_forward_drift_calibration as b13

IRODS_ROOT = f"/iplant/home/shared/commons_repo/curated/{b13a.DATASET}"
PLANTING_CANDIDATES = (
    "Date_Planted",
    "Date Planted",
    "Planting_Date",
    "Planting Date",
    "planting_date",
    "PlantingDate",
    "Sowing_Date",
    "Sowing Date",
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


def _source_manifest(root: Path) -> tuple[dict[str, Path], pd.DataFrame]:
    raw = root / "data" / "raw" / "case_study_b13a_2023_safe"
    b13a.assert_blind_tree(raw)
    paths: dict[str, Path] = {}
    rows: list[dict[str, object]] = []
    for logical, relative in b13a.SAFE_REMOTE_PATHS.items():
        b13a.assert_safe_remote_path(relative)
        path = raw / Path(relative).name
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"B13A pre-staged safe source is unavailable: {path}")
        # Parse each allow-listed object as a real table before accepting it.
        schema.read_official_safe_table(path)
        body = path.read_bytes()
        paths[logical] = path
        rows.append(
            {
                "logical_name": logical,
                "relative_path": relative,
                "resolved_url": f"irods://data.cyverse.org:1247{IRODS_ROOT}/{relative.lstrip('/')}",
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
                "outcome_file": False,
                "accessed_pre_seal": True,
            }
        )
    b13a.assert_blind_tree(raw)
    return paths, pd.DataFrame(rows)


def build_safe_environment_audit(field_metadata: pd.DataFrame) -> pd.DataFrame:
    env_col = _required(
        field_metadata,
        ("Experiment_Code", "Experiment Code", "Env", "Environment", "environment"),
        "2023 field experiment identifier",
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
    planting_col = resolve_column(field_metadata, PLANTING_CANDIDATES)

    rows: list[dict[str, object]] = []
    for raw_environment, part in field_metadata.groupby(env_col, sort=True, dropna=True):
        raw = str(raw_environment).strip()
        if not raw:
            continue
        lat = pd.to_numeric(part[lat_col], errors="coerce").dropna()
        lon = pd.to_numeric(part[lon_col], errors="coerce").dropna()
        planting = pd.Series([], dtype="datetime64[ns]")
        if planting_col is not None:
            planting = pd.to_datetime(part[planting_col], errors="coerce").dropna().sort_values()
        city = ""
        if city_col is not None and part[city_col].notna().any():
            city = str(part[city_col].dropna().astype(str).mode().iloc[0])
        planting_available = bool(not planting.empty)
        coords_available = bool(not lat.empty and not lon.empty)
        feasible = planting_available and coords_available
        reason = ""
        if not planting_available:
            reason = "PLANTING_DATE_NOT_AVAILABLE_IN_ALLOWLISTED_2023_FIELD_METADATA"
        elif not coords_available:
            reason = "ISSUANCE_COORDINATES_NOT_AVAILABLE"
        rows.append(
            {
                "environment": _canonical_environment(raw),
                "source_experiment_code": raw,
                "target_year": b13a.TARGET_YEAR,
                "city": city,
                "planting_date": planting.iloc[len(planting) // 2].date().isoformat() if planting_available else "",
                "planting_date_source": str(planting_col) if planting_col is not None else "NOT_AVAILABLE",
                "latitude": float(lat.median()) if not lat.empty else np.nan,
                "longitude": float(lon.median()) if not lon.empty else np.nan,
                "n_field_metadata_records": int(len(part)),
                "t1_metadata_feasible": feasible,
                "t1_metadata_failure_reason": reason,
                "weather_station_placement_used_as_planting_proxy": False,
                "treatment_application_date_used_as_planting_proxy": False,
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


def _empty_candidate_universe() -> tuple[pd.DataFrame, str]:
    frame = pd.DataFrame(columns=["genotype", "environment"])
    return frame, ""


def run(root: Path) -> dict[str, Path]:
    root = root.resolve()
    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)

    b13a.verify_b13_lock(results / "case_study_b13_preoutcome_lock.csv")
    genotypes = b13a.frozen_supported_genotypes(
        results / "case_study_b12_2022_sealed_predictions.csv",
        results / "case_study_b12_2022_prediction_seal.json",
    )
    paths, source_manifest = _source_manifest(root)

    field_metadata = schema.read_official_safe_table(paths["field_metadata"])
    # Parse the agronomic table as part of the source audit, but do not interpret
    # Date_of_application as planting time. Its published schema is treatment history.
    agronomic = schema.read_official_safe_table(paths["agronomic_information"])
    application_date_col = resolve_column(
        agronomic,
        ("Date_of_application", "Date of application", "Application_Date"),
    )
    explicit_agronomic_planting_col = resolve_column(agronomic, PLANTING_CANDIDATES)

    environments = build_safe_environment_audit(field_metadata)

    # This audit is independent of 2023 outcome availability and should still pass
    # even when the external source cannot supply a valid T1 issuance clock.
    b13a.audit_historical_encoder(root)

    feasible = environments[environments["t1_metadata_feasible"].astype(bool)].copy()
    if feasible.empty:
        cells, universe_sha = _empty_candidate_universe()
        decision = b13a.T1_INSUFFICIENT
        reason = "NO_EXPLICIT_PLANTING_DATE_IN_ALLOWLISTED_2023_PREOUTCOME_SOURCES"
    else:
        cells, universe_sha = b13a.candidate_universe(genotypes, environments)
        decision = b13a.READY
        reason = ""

    source_out = results / "case_study_b13a_2023_source_manifest.csv"
    env_out = results / "case_study_b13a_2023_environment_audit.csv"
    geno_out = results / "case_study_b13a_2023_genotype_audit.csv"
    universe_out = results / "case_study_b13a_2023_candidate_universe.csv"
    decision_out = results / "case_study_b13a_2023_lock_decision.csv"

    source_manifest.to_csv(source_out, index=False)
    environments.to_csv(env_out, index=False)
    genotypes.to_csv(geno_out, index=False)
    cells.to_csv(universe_out, index=False)
    pd.DataFrame(
        [
            {
                "target_year": b13a.TARGET_YEAR,
                "source_doi": b13a.SOURCE_DOI,
                "b13_adaptive_quantile_level": b13a.EXPECTED_B13_ADAPTIVE_LEVEL,
                "primary_estimand": b13.PRIMARY_ESTIMAND,
                "n_frozen_supported_genotypes": int(len(genotypes)),
                "n_safe_metadata_environments": int(len(environments)),
                "n_t1_metadata_feasible_environments": int(len(feasible)),
                "n_candidate_cells": int(len(cells)),
                "candidate_universe_sha256": universe_sha,
                "field_metadata_explicit_planting_column": (
                    str(resolve_column(field_metadata, PLANTING_CANDIDATES))
                    if resolve_column(field_metadata, PLANTING_CANDIDATES) is not None
                    else ""
                ),
                "agronomic_explicit_planting_column": (
                    str(explicit_agronomic_planting_col)
                    if explicit_agronomic_planting_col is not None
                    else ""
                ),
                "agronomic_application_date_column_present": bool(application_date_col is not None),
                "application_date_used_as_planting_proxy": False,
                "weather_station_placement_used_as_planting_proxy": False,
                "historical_t1_encoder_exactly_reproduced": True,
                "phenotype_directory_accessed": False,
                "phenotype_file_accessed": False,
                "candidate_universe_uses_2023_observed_keys": False,
                "point_predictor_changed": False,
                "t2_branch_reopened": False,
                "post_result_tuning_permitted": False,
                "decision": decision,
                "reason": reason,
            }
        ]
    ).to_csv(decision_out, index=False)

    b13a.assert_blind_tree(root / "data/raw/case_study_b13a_2023_safe")
    return {
        "source_manifest": source_out,
        "environment_audit": env_out,
        "genotype_audit": geno_out,
        "candidate_universe": universe_out,
        "decision": decision_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run canonical blind B13A 2023 source compatibility audit."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    print("Case Study B13A canonical source audit complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
