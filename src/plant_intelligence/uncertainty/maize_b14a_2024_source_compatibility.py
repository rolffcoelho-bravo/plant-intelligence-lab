"""Case Study B14A: blind 2024 source and frozen-representation compatibility audit.

B14A never reads 2024 observed yield and never generates predictions. It tests
whether the official 2024 G2F submission universe has a non-empty subset that is
jointly supported by the frozen B5 genotype matrix and the frozen B10/B11/B12
T1_30DAP environmental information state.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from plant_intelligence.data.maize_prospective_environment import (
    POWER_PARAMETERS,
    aggregate_weather,
    query_ssurgo_point,
    resolve_column,
)
from plant_intelligence.models.maize_environment_transfer import prepare_cells
from plant_intelligence.models.maize_environment_transfer_robustness import load_materialized
from plant_intelligence.models.maize_forecast_time_prediction import WEATHER_COLUMNS
from plant_intelligence.uncertainty import maize_external_temporal_validation as b12
from plant_intelligence.uncertainty.maize_forward_uncertainty import HORIZON

TARGET_YEAR = 2024
SOURCE_DOI = "10.25739/78mn-4394"
DATASET = "GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2025"
IRODS_ROOT = f"/iplant/home/shared/commons_repo/curated/{DATASET}/Testing_data"
SAFE_FILES = {
    "submission": "1_Submission_Template_2024.csv",
    "metadata": "2_Testing_Meta_Data_2024.csv",
}
FORBIDDEN_BASENAME = "7_Testing_Observed_Values.csv"
FORBIDDEN_TOKENS = ("observed", "answer", "trait", "phenotyp")
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
USER_AGENT = "plant-intelligence-lab/0.1 B14A blind-2024-source-audit"

READY = "B14A_2024_READY_FOR_PREOUTCOME_SEAL"
T1_INSUFFICIENT = "B14A_2024_T1_CONTEXT_INSUFFICIENT"
NO_GENOMIC_OVERLAP = "B14A_2024_NO_FROZEN_GENOMIC_OVERLAP"
NO_JOINT = "B14A_2024_NO_JOINTLY_SUPPORTED_CELLS"
ENCODER_MISMATCH = "B14A_HISTORICAL_ENCODER_MISMATCH"
OUTCOME_VIOLATION = "B14A_OUTCOME_BOUNDARY_VIOLATION"
SOURCE_UNRESOLVED = "B14A_2024_SOURCE_UNRESOLVED"

PLANTING_CANDIDATES = (
    "Date_Planted",
    "Date Planted",
    "Planting_Date",
    "Planting Date",
    "PlantingDate",
    "planting_date",
    "date_planted",
    "Sowing_Date",
    "Sowing Date",
    "sowing_date",
)
ENVIRONMENT_CANDIDATES = ("Env", "Environment", "environment", "Experiment_Code")
GENOTYPE_CANDIDATES = ("Hybrid", "hybrid", "Genotype", "genotype")
LATITUDE_CANDIDATES = (
    "Weather_Station_Latitude",
    "WeatherStationLatitude",
    "Weather_Station_Latitude (in decimal numbers NOT DMS)",
    "Latitude",
    "latitude",
    "Lat",
)
LONGITUDE_CANDIDATES = (
    "Weather_Station_Longitude",
    "WeatherStationLongitude",
    "Weather_Station_Longitude (in decimal numbers NOT DMS)",
    "Longitude",
    "longitude",
    "Lon",
    "Long",
)


class OutcomeBoundaryViolation(RuntimeError):
    pass


def _norm(value: object) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_blind_tree(root: Path) -> None:
    if not root.exists():
        return
    forbidden_exact = _norm(FORBIDDEN_BASENAME)
    for item in root.rglob("*"):
        if not item.is_file():
            continue
        name = item.name.lower()
        if _norm(item.name) == forbidden_exact or any(token in name for token in FORBIDDEN_TOKENS):
            raise OutcomeBoundaryViolation(f"B14A forbidden outcome-bearing artifact entered Stage A: {item}")


def _required(frame: pd.DataFrame, candidates: tuple[str, ...], label: str) -> str:
    hit = resolve_column(frame, candidates)
    if hit is None:
        raise ValueError(f"B14A cannot resolve {label}; columns={list(frame.columns)}")
    return hit


def read_safe_sources(root: Path) -> tuple[dict[str, Path], pd.DataFrame, pd.DataFrame]:
    raw = root / "data" / "raw" / "case_study_b14a_2024_safe"
    assert_blind_tree(raw)
    paths: dict[str, Path] = {}
    manifest_rows: list[dict[str, object]] = []
    schema_rows: list[dict[str, object]] = []
    allowed_names = set(SAFE_FILES.values())
    present = {p.name for p in raw.iterdir() if p.is_file()} if raw.exists() else set()
    unexpected = sorted(present - allowed_names)
    if unexpected:
        raise OutcomeBoundaryViolation(f"B14A staging tree contains non-allow-listed files: {unexpected}")
    for logical, basename in SAFE_FILES.items():
        path = raw / basename
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(f"B14A required safe source is unavailable: {path}")
        frame = pd.read_csv(path, nrows=8, low_memory=False)
        if len(frame.columns) < 2:
            raise ValueError(f"B14A source is not a valid table: {path}")
        paths[logical] = path
        manifest_rows.append(
            {
                "logical_name": logical,
                "source_doi": SOURCE_DOI,
                "irods_path": f"{IRODS_ROOT}/{basename}",
                "basename": basename,
                "sha256": sha256_file(path),
                "size_bytes": int(path.stat().st_size),
                "outcome_file": False,
                "accessed_pre_seal": True,
            }
        )
        for idx, col in enumerate(frame.columns):
            normalized = _norm(col)
            schema_rows.append(
                {
                    "logical_name": logical,
                    "column_index": idx,
                    "column_name": str(col),
                    "normalized_column_name": normalized,
                    "explicit_planting_or_sowing_semantics": bool(
                        normalized in {_norm(x) for x in PLANTING_CANDIDATES}
                    ),
                }
            )
    assert_blind_tree(raw)
    return paths, pd.DataFrame(manifest_rows), pd.DataFrame(schema_rows)


def submission_cells(submission: pd.DataFrame) -> pd.DataFrame:
    g_col = _required(submission, GENOTYPE_CANDIDATES, "submission genotype")
    e_col = _required(submission, ENVIRONMENT_CANDIDATES, "submission environment")
    cells = submission[[g_col, e_col]].copy()
    cells.columns = ["genotype", "environment"]
    cells = cells.dropna().drop_duplicates().reset_index(drop=True)
    cells["genotype"] = cells["genotype"].astype(str).str.strip()
    cells["environment"] = cells["environment"].astype(str).str.strip()
    cells = cells[(cells["genotype"] != "") & (cells["environment"] != "")]
    return cells.sort_values(["environment", "genotype"], kind="mergesort").reset_index(drop=True)


def frozen_b5_genotypes(root: Path) -> set[str]:
    pheno, geno, ecov = load_materialized(root)
    _, geno, _, cols = prepare_cells(pheno, geno, ecov)
    values = set(geno[cols["geno_id"]].dropna().astype(str).str.strip())
    values.discard("")
    if not values:
        raise ValueError("B14A frozen B5 genotype matrix is empty.")
    return values


def build_environment_metadata_audit(metadata: pd.DataFrame, requested_envs: set[str]) -> pd.DataFrame:
    env_col = _required(metadata, ENVIRONMENT_CANDIDATES, "testing metadata environment")
    plant_col = resolve_column(metadata, PLANTING_CANDIDATES)
    lat_col = resolve_column(metadata, LATITUDE_CANDIDATES)
    lon_col = resolve_column(metadata, LONGITUDE_CANDIDATES)
    city_col = resolve_column(metadata, ("City", "city", "Location", "location"))
    pop_col = resolve_column(
        metadata,
        ("Plant_Population", "PlantPopulation", "plant_population", "Plant_Density", "Plants_per_ha"),
    )

    rows: list[dict[str, object]] = []
    for environment in sorted(requested_envs):
        part = metadata[metadata[env_col].astype(str).str.strip().eq(environment)].copy()
        dates = pd.Series([], dtype="datetime64[ns]")
        raw_dates: list[str] = []
        if plant_col is not None and not part.empty:
            raw_dates = sorted(set(part[plant_col].dropna().astype(str).str.strip()))
            dates = pd.to_datetime(part[plant_col], errors="coerce").dropna().dt.normalize().drop_duplicates().sort_values()
        lat = pd.Series([], dtype=float)
        lon = pd.Series([], dtype=float)
        if lat_col is not None and not part.empty:
            lat = pd.to_numeric(part[lat_col], errors="coerce").dropna()
        if lon_col is not None and not part.empty:
            lon = pd.to_numeric(part[lon_col], errors="coerce").dropna()
        planting_exact = len(dates) == 1
        coords_available = bool(not lat.empty and not lon.empty)
        metadata_feasible = bool(not part.empty and planting_exact and coords_available)
        if part.empty:
            reason = "NO_TESTING_METADATA_ROW_FOR_SUBMISSION_ENVIRONMENT"
        elif plant_col is None:
            reason = "NO_EXPLICIT_PLANTING_OR_SOWING_COLUMN"
        elif len(dates) == 0:
            reason = "NO_PARSEABLE_EXPLICIT_PLANTING_DATE"
        elif len(dates) > 1:
            reason = "MULTIPLE_DISTINCT_PLANTING_DATES"
        elif not coords_available:
            reason = "ISSUANCE_COORDINATES_NOT_AVAILABLE"
        else:
            reason = ""
        city = ""
        if city_col is not None and not part.empty and part[city_col].notna().any():
            city = str(part[city_col].dropna().astype(str).mode().iloc[0])
        population = np.nan
        if pop_col is not None and not part.empty:
            p = pd.to_numeric(part[pop_col], errors="coerce").dropna()
            if not p.empty:
                population = float(p.median())
        rows.append(
            {
                "environment": environment,
                "target_year": TARGET_YEAR,
                "metadata_environment_column": env_col,
                "explicit_planting_column": plant_col or "",
                "raw_planting_values": "|".join(raw_dates),
                "n_distinct_parseable_planting_dates": int(len(dates)),
                "planting_date": dates.iloc[0].date().isoformat() if planting_exact else "",
                "latitude": float(lat.median()) if not lat.empty else np.nan,
                "longitude": float(lon.median()) if not lon.empty else np.nan,
                "city": city,
                "plant_population_proxy": population,
                "n_metadata_records": int(len(part)),
                "t1_metadata_feasible": metadata_feasible,
                "t1_metadata_failure_reason": reason,
                "weather_station_placement_used_as_planting_proxy": False,
                "treatment_date_used_as_planting_proxy": False,
                "observed_phenology_used": False,
                "outcome_used": False,
            }
        )
    return pd.DataFrame(rows).sort_values("environment", kind="mergesort").reset_index(drop=True)


def _power_through_t1(latitude: float, longitude: float, planting_date: str) -> pd.DataFrame:
    planting = pd.Timestamp(planting_date)
    issuance = planting + pd.Timedelta(days=30)
    response = requests.get(
        POWER_URL,
        params={
            "parameters": ",".join(POWER_PARAMETERS),
            "community": "AG",
            "longitude": f"{longitude:.5f}",
            "latitude": f"{latitude:.5f}",
            "start": planting.strftime("%Y%m%d"),
            "end": issuance.strftime("%Y%m%d"),
            "format": "JSON",
            "time-standard": "LST",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=(30, 180),
    )
    response.raise_for_status()
    parameters = response.json()["properties"]["parameter"]
    dates = sorted({d for values in parameters.values() for d in values})
    frame = pd.DataFrame(index=pd.to_datetime(dates, format="%Y%m%d"))
    for parameter in POWER_PARAMETERS:
        values = parameters.get(parameter, {})
        frame[parameter] = pd.to_numeric(
            pd.Series({pd.to_datetime(k, format="%Y%m%d"): v for k, v in values.items()}),
            errors="coerce",
        ).reindex(frame.index)
    frame = frame.replace({-999.0: np.nan, -999: np.nan}).sort_index()
    if frame.empty or frame.index.min() < planting or frame.index.max() > issuance:
        raise ValueError("B14A POWER request violated the frozen T1 window.")
    return frame


def reconstruct_t1_states(environment_audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    states: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    feasible = environment_audit[environment_audit["t1_metadata_feasible"].astype(bool)].copy()
    for env in feasible.itertuples(index=False):
        try:
            weather = _power_through_t1(float(env.latitude), float(env.longitude), str(env.planting_date))
            soil = query_ssurgo_point(float(env.latitude), float(env.longitude))
            if not bool(soil.get("ssurgo_available", False)):
                raise ValueError("SSURGO unavailable")
            wx = aggregate_weather(weather)
            if any(not np.isfinite(float(wx[c])) for c in WEATHER_COLUMNS):
                raise ValueError("T1 weather incomplete")
            planting = pd.Timestamp(env.planting_date)
            issuance = planting + pd.Timedelta(days=30)
            states.append(
                {
                    "environment": str(env.environment),
                    "year": TARGET_YEAR,
                    "city": str(env.city),
                    "horizon": HORIZON,
                    "issuance_date": issuance.date().isoformat(),
                    "planting_date": planting.date().isoformat(),
                    "uses_current_year_realized_weather": True,
                    "max_current_year_weather_date_used": weather.index.max().date().isoformat(),
                    "uses_future_weather": False,
                    "uses_observed_phenology": False,
                    "historical_weather_years_used": 0,
                    "plant_population_proxy": env.plant_population_proxy,
                    "ssurgo_available": True,
                    "ssurgo_mukey": str(soil.get("mukey", "")),
                    "ssurgo_mapunit": str(soil.get("muname", "")),
                    "ssurgo_component": str(soil.get("compname", "")),
                    **wx,
                }
            )
            rows.append({"environment": env.environment, "t1_reconstruction_state": "SUPPORTED_T1_CONTEXT", "reason": ""})
        except Exception as exc:
            rows.append({"environment": env.environment, "t1_reconstruction_state": "UNSUPPORTED_T1_CONTEXT", "reason": str(exc)})
    return pd.DataFrame(states), pd.DataFrame(rows)


def canonical_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    canonical = frame.sort_values(["environment", "genotype"], kind="mergesort").reset_index(drop=True)
    buffer = io.StringIO()
    canonical.to_csv(buffer, index=False, lineterminator="\n")
    return hashlib.sha256(buffer.getvalue().encode("utf-8")).hexdigest()


def run(root: Path) -> dict[str, Path]:
    root = root.resolve()
    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)
    raw = root / "data" / "raw" / "case_study_b14a_2024_safe"
    assert_blind_tree(raw)

    b13s = pd.read_csv(results / "case_study_b13s_2023_lock_decision.csv")
    if len(b13s) != 1 or str(b13s.iloc[0]["decision"]) != "B13S_2023_NO_ADMISSIBLE_PLANTING_DATE_RECOVERY":
        raise ValueError("B14A requires the merged B13-S 2023 closure state.")
    if str(b13s.iloc[0]["outcome_files_accessed"]).strip().lower() != "false":
        raise OutcomeBoundaryViolation("B14A refuses a B13-S state with outcome access.")

    paths, source_manifest, source_schema = read_safe_sources(root)
    submission = pd.read_csv(paths["submission"], low_memory=False)
    metadata = pd.read_csv(paths["metadata"], low_memory=False)
    cells = submission_cells(submission)
    requested_envs = set(cells["environment"].astype(str))

    frozen_genotypes = frozen_b5_genotypes(root)
    supported_submission_genotypes = sorted(set(cells["genotype"]).intersection(frozen_genotypes))
    genotype_audit = pd.DataFrame(
        {
            "genotype": sorted(set(cells["genotype"])),
        }
    )
    genotype_audit["genotype_support_state"] = np.where(
        genotype_audit["genotype"].isin(frozen_genotypes),
        "SUPPORTED_FROZEN_B5_GENOME",
        "UNSUPPORTED_GENOTYPE_NOT_IN_FROZEN_B5_GENOME",
    )

    environments = build_environment_metadata_audit(metadata, requested_envs)

    historical_encoder_exact = True
    encoder_error = ""
    try:
        states_hist = pd.read_csv(results / "case_study_b9_safe_environment_states.csv", low_memory=False)
        manifest_hist = pd.read_csv(results / "case_study_b9_environment_manifest.csv", low_memory=False)
        b12.audit_historical_t1_encoding(states_hist, manifest_hist)
    except Exception as exc:
        historical_encoder_exact = False
        encoder_error = str(exc)

    t1_states, t1_reconstruction = reconstruct_t1_states(environments)
    reconstructed_envs = set(t1_states["environment"].astype(str)) if not t1_states.empty else set()

    combined_t1_constructed = False
    combined_t1_error = ""
    if historical_encoder_exact and reconstructed_envs:
        try:
            test_manifest = environments[environments["environment"].isin(reconstructed_envs)].copy()
            b12.build_combined_t1_matrix(states_hist, manifest_hist, t1_states, test_manifest)
            combined_t1_constructed = True
        except Exception as exc:
            combined_t1_error = str(exc)

    supported = cells.copy()
    supported["genotype_support_state"] = np.where(
        supported["genotype"].isin(frozen_genotypes),
        "SUPPORTED_FROZEN_B5_GENOME",
        "UNSUPPORTED_GENOTYPE_NOT_IN_FROZEN_B5_GENOME",
    )
    supported["environment_input_state"] = np.where(
        supported["environment"].isin(reconstructed_envs),
        "SUPPORTED_T1_CONTEXT",
        "UNSUPPORTED_T1_CONTEXT",
    )
    candidate = supported[
        supported["genotype_support_state"].eq("SUPPORTED_FROZEN_B5_GENOME")
        & supported["environment_input_state"].eq("SUPPORTED_T1_CONTEXT")
    ][["genotype", "environment"]].copy()
    candidate = candidate.sort_values(["environment", "genotype"], kind="mergesort").reset_index(drop=True)
    universe_sha = canonical_hash(candidate)

    if not historical_encoder_exact:
        decision, reason = ENCODER_MISMATCH, encoder_error
    elif len(supported_submission_genotypes) == 0:
        decision, reason = NO_GENOMIC_OVERLAP, "NO_2024_SUBMISSION_HYBRID_HAS_AN_EXACT_VECTOR_IN_THE_FROZEN_B5_GENOTYPE_MATRIX"
    elif len(reconstructed_envs) == 0:
        decision, reason = T1_INSUFFICIENT, "NO_2024_SUBMISSION_ENVIRONMENT_HAS_A_COMPLETE_FROZEN_T1_CONTEXT"
    elif not combined_t1_constructed:
        decision, reason = ENCODER_MISMATCH, combined_t1_error or "COMBINED_T1_MATRIX_COULD_NOT_BE_CONSTRUCTED"
    elif candidate.empty:
        decision, reason = NO_JOINT, "GENOMIC_AND_T1_SUPPORT_EXIST_SEPARATELY_BUT_NO_OFFICIAL_SUBMISSION_CELL_HAS_BOTH"
    else:
        decision, reason = READY, ""

    source_out = results / "case_study_b14a_2024_source_manifest.csv"
    schema_out = results / "case_study_b14a_2024_source_schema.csv"
    env_out = results / "case_study_b14a_2024_environment_audit.csv"
    t1_out = results / "case_study_b14a_2024_t1_reconstruction_audit.csv"
    geno_out = results / "case_study_b14a_2024_genotype_audit.csv"
    support_out = results / "case_study_b14a_2024_submission_support_audit.csv"
    universe_out = results / "case_study_b14a_2024_candidate_universe.csv"
    decision_out = results / "case_study_b14a_2024_lock_decision.csv"
    seal_out = results / "case_study_b14a_2024_source_seal.json"

    source_manifest.to_csv(source_out, index=False)
    source_schema.to_csv(schema_out, index=False)
    environments.to_csv(env_out, index=False)
    t1_reconstruction.to_csv(t1_out, index=False)
    genotype_audit.to_csv(geno_out, index=False)
    supported.to_csv(support_out, index=False)
    candidate.to_csv(universe_out, index=False)

    source_seal = {
        "stage": "B14A_2024_PREOUTCOME_SOURCE_COMPATIBILITY_AUDIT",
        "target_year": TARGET_YEAR,
        "source_doi": SOURCE_DOI,
        "source_dataset": DATASET,
        "allowed_files": SAFE_FILES,
        "forbidden_observed_file": FORBIDDEN_BASENAME,
        "source_sha256": {row["logical_name"]: row["sha256"] for row in source_manifest.to_dict("records")},
        "observed_values_accessed": False,
        "prediction_generated": False,
        "b5_genotype_representation_changed": False,
        "t1_clock_changed": False,
        "t2_branch_reopened": False,
    }
    seal_out.write_text(json.dumps(source_seal, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    decision_frame = pd.DataFrame(
        [
            {
                "target_year": TARGET_YEAR,
                "source_doi": SOURCE_DOI,
                "n_submission_cells": int(len(cells)),
                "n_submission_genotypes": int(cells["genotype"].nunique()),
                "n_submission_environments": int(cells["environment"].nunique()),
                "n_frozen_b5_genotypes": int(len(frozen_genotypes)),
                "n_supported_submission_genotypes": int(len(supported_submission_genotypes)),
                "n_metadata_environments_requested": int(len(environments)),
                "n_t1_metadata_feasible_environments": int(environments["t1_metadata_feasible"].astype(bool).sum()),
                "n_t1_reconstructed_environments": int(len(reconstructed_envs)),
                "n_candidate_cells": int(len(candidate)),
                "n_candidate_genotypes": int(candidate["genotype"].nunique()) if len(candidate) else 0,
                "n_candidate_environments": int(candidate["environment"].nunique()) if len(candidate) else 0,
                "candidate_universe_sha256": universe_sha,
                "explicit_planting_column": str(resolve_column(metadata, PLANTING_CANDIDATES) or ""),
                "historical_t1_encoder_exactly_reproduced": historical_encoder_exact,
                "combined_t1_matrix_constructed": combined_t1_constructed,
                "official_testing_weather_file_accessed": False,
                "official_testing_soil_file_accessed": False,
                "observed_values_accessed": False,
                "prediction_generated": False,
                "point_predictor_changed": False,
                "b5_genotype_representation_changed": False,
                "new_2425_snp_representation_imported": False,
                "t1_clock_changed": False,
                "t2_branch_reopened": False,
                "post_result_tuning_permitted": False,
                "decision": decision,
                "reason": reason,
            }
        ]
    )
    decision_frame.to_csv(decision_out, index=False)
    assert_blind_tree(raw)
    return {
        "source_manifest": source_out,
        "source_schema": schema_out,
        "environment_audit": env_out,
        "t1_reconstruction_audit": t1_out,
        "genotype_audit": geno_out,
        "submission_support_audit": support_out,
        "candidate_universe": universe_out,
        "decision": decision_out,
        "source_seal": seal_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run blind B14A 2024 source compatibility audit.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    print("Case Study B14A 2024 source compatibility audit complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
