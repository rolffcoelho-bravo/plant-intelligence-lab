"""Case Study B13A: blind 2023 source and compatibility audit.

B13A does not generate predictions and never acquires the 2023 phenotype file.
It verifies that the public G2F 2023 field-season release can support a later
sealed T1 prediction stage without changing the already-merged B13 statistical
lock.

The candidate genotype universe is inherited from the immutable B12 sealed
artifact. The candidate environment universe is derived only from issuance-safe
2023 field metadata. Their Cartesian product is fixed before any 2023 phenotype
key or value is read.
"""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

import numpy as np
import pandas as pd
import requests

from plant_intelligence.data.maize_prospective_environment import resolve_column
from plant_intelligence.uncertainty import maize_external_temporal_validation as b12
from plant_intelligence.uncertainty import maize_b13_forward_drift_calibration as b13

TARGET_YEAR = 2023
SOURCE_DOI = "10.25739/rzzy-3n27"
DATASET = "GenomesToFields_G2F_data_2023"
ROOT_PATH = f"iplant/projects/commons_repo/curated/{DATASET}"
CYVERSE_BASES = (
    f"https://data.cyverse.org/dav-anon/{ROOT_PATH}",
    f"https://data.cyverse.org/dav/{ROOT_PATH}",
)
SAFE_REMOTE_PATHS = {
    "field_metadata": "z._2023_supplemental_info/g2f_2023_field_metadata.csv",
    "agronomic_information": "z._2023_supplemental_info/g2f_2023_agronomic_information.csv",
    "weather_cleaned": "b._2023_weather_data/g2f_2023_weather_cleaned.csv",
    "soil": "c._2023_soil_data/g2f_2023_soil_data.csv",
}
FORBIDDEN_PATH_TOKEN = "a._2023_phenotypic_data"
FORBIDDEN_BASENAME = "g2f_2023_phenotypic_data.csv"
B12_PREDICTION_SHA256 = "fb8347da2a5ba9fff0d106fa9b7a13037818c8e0e0d1387527dbf090c3085220"
EXPECTED_B13_ADAPTIVE_LEVEL = 0.9512813317177465
EXPECTED_B12_SUPPORTED_GENOTYPES = 43
USER_AGENT = "plant-intelligence-lab/0.1 B13A blind-2023-source-audit"
READY = "B13A_2023_SOURCE_COMPATIBLE_READY_FOR_SEAL"
SOURCE_UNRESOLVED = "B13A_2023_SOURCE_UNRESOLVED"
T1_INSUFFICIENT = "B13A_2023_T1_CONTEXT_INSUFFICIENT"
ENCODER_MISMATCH = "B13A_HISTORICAL_ENCODER_MISMATCH"
OUTCOME_VIOLATION = "B13A_OUTCOME_BOUNDARY_VIOLATION"


class OutcomeBoundaryViolation(RuntimeError):
    pass


def _norm(value: object) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def assert_safe_remote_path(relative_path: str) -> None:
    text = str(relative_path).replace("\\", "/").lower()
    if FORBIDDEN_PATH_TOKEN.lower() in text:
        raise OutcomeBoundaryViolation("B13A refuses the 2023 phenotype directory.")
    if _norm(Path(text).name) == _norm(FORBIDDEN_BASENAME):
        raise OutcomeBoundaryViolation("B13A refuses the 2023 phenotype file.")
    allowed = {_norm(Path(v).name) for v in SAFE_REMOTE_PATHS.values()}
    if _norm(Path(text).name) not in allowed:
        raise OutcomeBoundaryViolation(f"B13A path is not allow-listed: {relative_path}")


def assert_blind_tree(root: Path) -> None:
    if not root.exists():
        return
    for item in root.rglob("*"):
        if not item.is_file():
            continue
        lower = str(item).replace("\\", "/").lower()
        if FORBIDDEN_PATH_TOKEN.lower() in lower or _norm(item.name) == _norm(FORBIDDEN_BASENAME):
            raise OutcomeBoundaryViolation(f"2023 phenotype artifact entered B13A Stage A: {item}")


def _schema_valid_csv(body: bytes) -> bool:
    try:
        frame = pd.read_csv(io.BytesIO(body), nrows=8, low_memory=False)
    except Exception:
        return False
    return bool(len(frame.columns) >= 2)


def _authenticated_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.replace("/dav-anon/", "/dav/", 1), parts.query, ""))


def download_safe_file(relative_path: str, destination: Path, timeout: int = 180) -> tuple[str, str, int]:
    assert_safe_remote_path(relative_path)
    attempts: list[str] = []
    for base in CYVERSE_BASES:
        url = f"{base.rstrip('/')}/{relative_path.lstrip('/')}"
        auth = ("anonymous", "") if "/dav/" in url and "/dav-anon/" not in url else None
        try:
            response = requests.get(
                url,
                auth=auth,
                headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*;q=0.5"},
                timeout=(30, timeout),
                allow_redirects=True,
            )
            response.raise_for_status()
            body = response.content
            if not body or not _schema_valid_csv(body):
                raise RuntimeError("response is not a schema-valid CSV")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
            return url, hashlib.sha256(body).hexdigest(), len(body)
        except Exception as exc:
            attempts.append(f"{url}: {type(exc).__name__}: {exc}")
    raise RuntimeError("B13A could not acquire safe 2023 source: " + " | ".join(attempts))


def acquire_safe_inputs(root: Path) -> tuple[dict[str, Path], pd.DataFrame]:
    raw = root / "data" / "raw" / "case_study_b13a_2023_safe"
    raw.mkdir(parents=True, exist_ok=True)
    assert_blind_tree(raw)
    paths: dict[str, Path] = {}
    rows: list[dict[str, object]] = []
    for logical, relative in SAFE_REMOTE_PATHS.items():
        assert_safe_remote_path(relative)
        destination = raw / Path(relative).name
        url, digest, size = download_safe_file(relative, destination)
        paths[logical] = destination
        rows.append(
            {
                "logical_name": logical,
                "relative_path": relative,
                "resolved_url": url,
                "sha256": digest,
                "size_bytes": size,
                "outcome_file": False,
                "accessed_pre_seal": True,
            }
        )
    assert_blind_tree(raw)
    return paths, pd.DataFrame(rows)


def _required(frame: pd.DataFrame, candidates: Iterable[str], label: str) -> str:
    hit = resolve_column(frame, tuple(candidates))
    if hit is None:
        raise ValueError(f"B13A cannot resolve {label}; columns={list(frame.columns)}")
    return hit


def build_environment_audit(metadata: pd.DataFrame) -> pd.DataFrame:
    env_col = _required(
        metadata,
        ("Env", "Environment", "environment", "Env_ID", "Environment_ID", "Field-Location", "Field_Location"),
        "environment identifier",
    )
    plant_col = _required(
        metadata,
        ("Planting_Date", "planting_date", "Date_Planted", "date_planted", "PlantingDate", "Date Planted"),
        "planting date",
    )
    lat_col = _required(
        metadata,
        ("Latitude", "latitude", "Lat", "Field_Latitude", "Weather_Station_Latitude", "WeatherStationLatitude"),
        "latitude",
    )
    lon_col = _required(
        metadata,
        ("Longitude", "longitude", "Lon", "Long", "Field_Longitude", "Weather_Station_Longitude", "WeatherStationLongitude"),
        "longitude",
    )
    year_col = resolve_column(metadata, ("Year", "year", "Season", "season"))
    population_col = resolve_column(
        metadata,
        ("Plant_Population", "PlantPopulation", "plant_population", "Plant_Density", "Plants_per_ha"),
    )

    frame = metadata.copy()
    if year_col is not None:
        years = pd.to_numeric(frame[year_col], errors="coerce")
        if years.notna().any():
            frame = frame[years.eq(TARGET_YEAR)].copy()
    rows: list[dict[str, object]] = []
    for environment, part in frame.groupby(env_col, sort=True, dropna=True):
        planting = pd.to_datetime(part[plant_col], errors="coerce").dropna().sort_values()
        lat = pd.to_numeric(part[lat_col], errors="coerce").dropna()
        lon = pd.to_numeric(part[lon_col], errors="coerce").dropna()
        population = np.nan
        if population_col is not None:
            p = pd.to_numeric(part[population_col], errors="coerce").dropna()
            if not p.empty:
                population = float(p.median())
        valid = bool(not planting.empty and not lat.empty and not lon.empty)
        rows.append(
            {
                "environment": str(environment),
                "target_year": TARGET_YEAR,
                "planting_date": planting.iloc[len(planting) // 2].date().isoformat() if not planting.empty else "",
                "latitude": float(lat.median()) if not lat.empty else np.nan,
                "longitude": float(lon.median()) if not lon.empty else np.nan,
                "plant_population_proxy": population,
                "n_metadata_records": int(len(part)),
                "t1_metadata_feasible": valid,
                "weather_window_rule": "PLANTING_THROUGH_30_DAP_ONLY",
                "phenotype_used": False,
            }
        )
    audit = pd.DataFrame(rows)
    if audit.empty:
        raise ValueError("B13A found no 2023 environments in safe field metadata.")
    return audit.sort_values("environment").reset_index(drop=True)


def frozen_supported_genotypes(prediction_path: Path, seal_path: Path) -> pd.DataFrame:
    seal = b12.verify_prediction_seal(prediction_path, seal_path)
    if str(seal.get("prediction_sha256")) != B12_PREDICTION_SHA256:
        raise ValueError("B13A B12 prediction seal is not the immutable published seal.")
    frame = pd.read_csv(prediction_path, usecols=["genotype"])
    values = sorted(frame["genotype"].dropna().astype(str).unique().tolist())
    if len(values) != EXPECTED_B12_SUPPORTED_GENOTYPES:
        raise ValueError(
            f"B13A expected {EXPECTED_B12_SUPPORTED_GENOTYPES} frozen-genome hybrids, found {len(values)}."
        )
    return pd.DataFrame(
        {
            "genotype": values,
            "genotype_support_state": "SUPPORTED_FROZEN_B5_GENOME_INHERITED_FROM_B12",
            "source_prediction_sha256": B12_PREDICTION_SHA256,
            "phenotype_used": False,
        }
    )


def verify_b13_lock(lock_path: Path) -> pd.DataFrame:
    lock = pd.read_csv(lock_path)
    if len(lock) != 1:
        raise ValueError("B13 pre-outcome lock must contain exactly one row.")
    row = lock.iloc[0]
    checks = (
        int(row["target_year"]) == TARGET_YEAR,
        str(row["control_rule"]) == b13.CONTROL,
        str(row["adaptive_rule"]) == b13.ADAPTIVE,
        np.isclose(float(row["adaptive_quantile_level"]), EXPECTED_B13_ADAPTIVE_LEVEL, rtol=0, atol=1e-15),
        str(row["primary_estimand"]) == b13.PRIMARY_ESTIMAND,
        str(row["stage_state"]) == "B13_PREOUTCOME_CALIBRATION_RULE_LOCKED",
        str(row["selection_uses_outcome_value"]).strip().lower() == "false",
        str(row["point_predictor_changed"]).strip().lower() == "false",
        str(row["t2_branch_reopened"]).strip().lower() == "false",
        str(row["post_result_tuning_permitted"]).strip().lower() == "false",
    )
    if not all(checks):
        raise ValueError("B13A detected a change in the merged B13 pre-outcome statistical lock.")
    return lock


def candidate_universe(genotypes: pd.DataFrame, environments: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    supported = environments[environments["t1_metadata_feasible"].astype(bool)].copy()
    if supported.empty:
        raise ValueError("B13A has no environment with issuance-safe T1 metadata.")
    cells = pd.MultiIndex.from_product(
        [genotypes["genotype"].astype(str), supported["environment"].astype(str)],
        names=["genotype", "environment"],
    ).to_frame(index=False)
    cells = cells.sort_values(["environment", "genotype"], kind="mergesort").reset_index(drop=True)
    payload = cells.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return cells, hashlib.sha256(payload).hexdigest()


def audit_historical_encoder(root: Path) -> None:
    states = pd.read_csv(root / "reports/results/case_study_b9_safe_environment_states.csv", low_memory=False)
    manifest = pd.read_csv(root / "reports/results/case_study_b9_environment_manifest.csv", low_memory=False)
    b12.audit_historical_t1_encoding(states, manifest)


def run(root: Path) -> dict[str, Path]:
    root = root.resolve()
    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)
    lock_path = results / "case_study_b13_preoutcome_lock.csv"
    verify_b13_lock(lock_path)

    prediction_path = results / "case_study_b12_2022_sealed_predictions.csv"
    seal_path = results / "case_study_b12_2022_prediction_seal.json"
    genotypes = frozen_supported_genotypes(prediction_path, seal_path)

    state = READY
    reason = ""
    try:
        paths, source_manifest = acquire_safe_inputs(root)
    except OutcomeBoundaryViolation as exc:
        state, reason = OUTCOME_VIOLATION, str(exc)
        raise
    except Exception as exc:
        state, reason = SOURCE_UNRESOLVED, str(exc)
        raise

    metadata = pd.read_csv(paths["field_metadata"], low_memory=False)
    environments = build_environment_audit(metadata)
    if not environments["t1_metadata_feasible"].astype(bool).any():
        state = T1_INSUFFICIENT
        raise ValueError("B13A safe 2023 metadata cannot support any T1 issuance context.")

    try:
        audit_historical_encoder(root)
    except Exception as exc:
        state, reason = ENCODER_MISMATCH, str(exc)
        raise

    cells, universe_sha = candidate_universe(genotypes, environments)
    supported_envs = environments[environments["t1_metadata_feasible"].astype(bool)]

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
                "target_year": TARGET_YEAR,
                "source_doi": SOURCE_DOI,
                "b13_adaptive_quantile_level": EXPECTED_B13_ADAPTIVE_LEVEL,
                "primary_estimand": b13.PRIMARY_ESTIMAND,
                "n_frozen_supported_genotypes": int(len(genotypes)),
                "n_safe_metadata_environments": int(len(environments)),
                "n_t1_metadata_feasible_environments": int(len(supported_envs)),
                "n_candidate_cells": int(len(cells)),
                "candidate_universe_sha256": universe_sha,
                "historical_t1_encoder_exactly_reproduced": True,
                "phenotype_directory_accessed": False,
                "phenotype_file_accessed": False,
                "candidate_universe_uses_2023_observed_keys": False,
                "point_predictor_changed": False,
                "t2_branch_reopened": False,
                "post_result_tuning_permitted": False,
                "decision": state,
                "reason": reason,
            }
        ]
    ).to_csv(decision_out, index=False)
    assert_blind_tree(root / "data/raw/case_study_b13a_2023_safe")
    return {
        "source_manifest": source_out,
        "environment_audit": env_out,
        "genotype_audit": geno_out,
        "candidate_universe": universe_out,
        "decision": decision_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run blind B13A 2023 source compatibility audit.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    print("Case Study B13A source audit complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
