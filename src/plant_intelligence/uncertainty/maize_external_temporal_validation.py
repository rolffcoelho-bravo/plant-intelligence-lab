"""Case Study B12: sealed 2022 external temporal validation.

B12 keeps the B10/B11 T1 reference frozen and separates prediction issuance from
outcome revelation.

Stage A:
- acquires only 2022 input metadata/submission files;
- reconstructs T1 weather only through 30 days after planting;
- uses the exact frozen B5 genotype matrix and predicts only hybrids already
  represented by an exact marker vector in that matrix;
- calibrates intervals from B10/B11 forward residuals dated 2016-2021 only;
- writes a deterministic prediction artifact and SHA-256 seal.

Stage B:
- verifies the Stage-A seal before reading the official 2022 answer file;
- evaluates the sealed predictions without refitting, retuning, changing an
  interval, changing the support threshold, or reopening the closed T2 branch.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
from typing import Iterable

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
from plant_intelligence.models.maize_environment_transfer_robustness import (
    cell_features,
    environment_map,
    genomic_map,
    load_materialized,
    metrics,
    predict,
)
from plant_intelligence.models.maize_forecast_time_prediction import (
    FROZEN_CONFIG,
    WEATHER_COLUMNS,
    build_environment_state_matrices,
)
from plant_intelligence.models.maize_forward_support_diagnostics import support_geometry
from plant_intelligence.uncertainty.maize_forward_uncertainty import (
    ABSTAIN,
    HORIZON,
    MIN_SUPPORT_GROUP_ENVIRONMENTS,
    MODEL,
    NOMINAL_LEVELS,
    RETAIN,
    SUPPORT_EDGE,
    SUPPORT_WITHIN,
    _cluster_coverage_ci,
    build_forward_t1_predictions,
    build_t1_support_table,
    finite_sample_quantile,
    support_group,
)

TARGET_YEAR = 2022
SOURCE_DOI = "10.25739/tq5e-ak26"
CYVERSE_DATASET = "GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2023"
CYVERSE_BASES = (
    f"https://data.cyverse.org/dav-anon/iplant/commons/cyverse_curated/{CYVERSE_DATASET}",
    f"https://data.cyverse.org/dav-anon/iplant/home/shared/commons_repo/curated/{CYVERSE_DATASET}",
)
SAFE_REMOTE_PATHS = {
    "submission": "Testing_Data/1_Submission_Template_2022.csv",
    "metadata": "Testing_Data/2_Testing_Meta_Data_2022.csv",
}
ANSWER_REMOTE_PATHS = (
    "Test_Set_Observed_Values_ANSWER.csv",
    "Testing_Data/Test_Set_Observed_Values_ANSWER.csv",
)
FORBIDDEN_ANSWER_BASENAME = "Test_Set_Observed_Values_ANSWER.csv"
SUPPORTED_GENOTYPE = "SUPPORTED_FROZEN_B5_GENOME"
UNSUPPORTED_GENOTYPE = "UNSUPPORTED_GENOTYPE_NOT_IN_FROZEN_B5_GENOME"
SUPPORTED_ENVIRONMENT = "SUPPORTED_T1_CONTEXT"
UNSUPPORTED_ENVIRONMENT = "UNSUPPORTED_T1_CONTEXT"
SEAL_SCHEMA = "plant-intelligence-lab/b12-prediction-seal/v1"
USER_AGENT = "plant-intelligence-lab/0.1 sealed-external-validation"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


class SealViolation(RuntimeError):
    pass


def _normalized(value: object) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def _sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_blind_stage(paths: Iterable[Path]) -> None:
    forbidden = _normalized(FORBIDDEN_ANSWER_BASENAME)
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        items = [root] if root.is_file() else root.rglob("*")
        for item in items:
            if item.is_file() and _normalized(item.name) == forbidden:
                raise SealViolation(f"B12 Stage A refuses observed outcomes at {item}")


def _download_first_available(
    relative_paths: Iterable[str], destination: Path, timeout: int = 180
) -> tuple[str, str, int]:
    errors: list[str] = []
    for relative_path in relative_paths:
        for base in CYVERSE_BASES:
            url = f"{base.rstrip('/')}/{relative_path.lstrip('/')}"
            try:
                response = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=(30, timeout),
                )
                response.raise_for_status()
                body = response.content
                if not body:
                    raise RuntimeError("empty response")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(body)
                return url, _sha256_bytes(body), len(body)
            except Exception as exc:
                errors.append(f"{url}: {exc}")
    raise RuntimeError("B12 public-data download failed: " + " | ".join(errors))


def acquire_stage_a_inputs(root: Path) -> dict[str, Path]:
    raw = root / "data" / "raw" / "case_study_b12_2022_sealed"
    raw.mkdir(parents=True, exist_ok=True)
    assert_blind_stage([raw])
    provenance = []
    paths: dict[str, Path] = {}
    for logical, relative in SAFE_REMOTE_PATHS.items():
        if _normalized(Path(relative).name) == _normalized(FORBIDDEN_ANSWER_BASENAME):
            raise SealViolation("B12 Stage-A allowlist contains the observed-answer file.")
        path = raw / Path(relative).name
        url, digest, size = _download_first_available((relative,), path)
        paths[logical] = path
        provenance.append(
            {
                "logical_name": logical,
                "relative_path": relative,
                "url": url,
                "sha256": digest,
                "size_bytes": size,
            }
        )
    assert_blind_stage([raw])
    (raw / "stage_a_provenance.json").write_text(
        json.dumps(
            {
                "stage": "B12A_SEALED_INPUT_ACQUISITION",
                "source_doi": SOURCE_DOI,
                "target_year": TARGET_YEAR,
                "observed_outcomes_accessed": False,
                "files": provenance,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return paths


def acquire_stage_b_answer(root: Path) -> Path:
    raw = root / "data" / "raw" / "case_study_b12_2022_reveal"
    path = raw / FORBIDDEN_ANSWER_BASENAME
    _download_first_available(ANSWER_REMOTE_PATHS, path)
    return path


def _required(frame: pd.DataFrame, candidates: tuple[str, ...], label: str) -> str:
    hit = resolve_column(frame, candidates)
    if hit is None:
        raise ValueError(f"B12 cannot resolve {label}; columns={list(frame.columns)}")
    return hit


def submission_columns(frame: pd.DataFrame) -> tuple[str, str]:
    return (
        _required(frame, ("Hybrid", "hybrid", "Genotype", "genotype"), "submission genotype"),
        _required(frame, ("Env", "environment", "Environment"), "submission environment"),
    )


def competition_environment_manifest(
    metadata: pd.DataFrame, submission: pd.DataFrame
) -> pd.DataFrame:
    env_col = _required(metadata, ("Env", "environment", "Environment"), "environment")
    plant_col = _required(
        metadata,
        (
            "Date_Planted",
            "Planting_Date",
            "PlantingDate",
            "date_plant",
            "date_planted",
            "planting_date",
            "Sowing_Date",
        ),
        "planting date",
    )
    lat_col = _required(
        metadata,
        (
            "Weather_Station_Latitude",
            "WeatherStationLatitude",
            "Latitude",
            "latitude",
            "Lat",
        ),
        "weather-station latitude",
    )
    lon_col = _required(
        metadata,
        (
            "Weather_Station_Longitude",
            "WeatherStationLongitude",
            "Longitude",
            "longitude",
            "Lon",
            "Long",
        ),
        "weather-station longitude",
    )
    city_col = resolve_column(metadata, ("City", "city", "Location", "location"))
    pop_col = resolve_column(
        metadata,
        ("Plant_Population", "PlantPopulation", "plant_population", "Plant_Density"),
    )
    _, sub_env_col = submission_columns(submission)
    requested = set(submission[sub_env_col].dropna().astype(str))
    rows = []
    for environment, part in metadata.groupby(env_col, sort=True):
        environment = str(environment)
        if environment not in requested:
            continue
        planting = pd.to_datetime(part[plant_col], errors="coerce").dropna().sort_values()
        lat = pd.to_numeric(part[lat_col], errors="coerce").dropna()
        lon = pd.to_numeric(part[lon_col], errors="coerce").dropna()
        if planting.empty or lat.empty or lon.empty:
            raise ValueError(f"B12 missing planting/coordinates for {environment}")
        population = float("nan")
        if pop_col:
            p = pd.to_numeric(part[pop_col], errors="coerce").dropna()
            if not p.empty:
                population = float(p.median())
        city = ""
        if city_col and part[city_col].notna().any():
            city = str(part[city_col].dropna().astype(str).mode().iloc[0])
        rows.append(
            {
                "environment": environment,
                "year": TARGET_YEAR,
                "city": city,
                "planting_date": planting.iloc[len(planting) // 2].date().isoformat(),
                "latitude": float(lat.median()),
                "longitude": float(lon.median()),
                "coordinate_source": "G2F_2022_testing_metadata",
                "historical_year_city_match": "",
                "plant_population_proxy": population,
                "n_plot_records": int(len(part)),
            }
        )
    manifest = pd.DataFrame(rows)
    covered = set(manifest["environment"].astype(str)) if len(manifest) else set()
    missing = sorted(requested - covered)
    if missing:
        raise ValueError(f"B12 testing metadata misses environments: {missing[:10]}")
    return manifest.sort_values("environment").reset_index(drop=True)


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
        raise SealViolation("B12 POWER request violated the T1 issuance window.")
    return frame


def build_2022_t1_states(
    manifest: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    audit = []
    for env in manifest.itertuples(index=False):
        try:
            weather = _power_through_t1(
                float(env.latitude), float(env.longitude), str(env.planting_date)
            )
            soil = query_ssurgo_point(float(env.latitude), float(env.longitude))
            if not bool(soil.get("ssurgo_available", False)):
                raise ValueError("SSURGO unavailable")
            wx = aggregate_weather(weather)
            if any(not np.isfinite(float(wx[c])) for c in WEATHER_COLUMNS):
                raise ValueError("T1 weather incomplete")
            planting = pd.Timestamp(env.planting_date)
            issuance = planting + pd.Timedelta(days=30)
            rows.append(
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
            audit.append(
                {
                    "environment": env.environment,
                    "environment_input_state": SUPPORTED_ENVIRONMENT,
                    "reason": "",
                }
            )
        except SealViolation:
            raise
        except Exception as exc:
            audit.append(
                {
                    "environment": env.environment,
                    "environment_input_state": UNSUPPORTED_ENVIRONMENT,
                    "reason": str(exc),
                }
            )
    states = pd.DataFrame(rows)
    audit_frame = pd.DataFrame(audit)
    if states.empty:
        raise ValueError("B12 has no 2022 environment with complete frozen T1 context.")
    return states, audit_frame


def build_combined_t1_matrix(
    historical_states: pd.DataFrame,
    historical_manifest: pd.DataFrame,
    test_states: pd.DataFrame,
    test_manifest: pd.DataFrame,
) -> pd.DataFrame:
    hist = historical_states[historical_states["horizon"].astype(str).eq(HORIZON)].copy()
    states = pd.concat([hist, test_states], ignore_index=True, sort=False)
    env = pd.concat([historical_manifest, test_manifest], ignore_index=True, sort=False)
    env["environment"] = env["environment"].astype(str)
    if env["environment"].duplicated().any():
        raise ValueError("B12 combined environment manifest contains duplicates.")
    env = env.set_index("environment").sort_index()
    state = states.copy()
    state["environment"] = state["environment"].astype(str)
    state = state.set_index("environment").reindex(env.index)
    if state["ssurgo_mukey"].isna().any():
        raise ValueError("B12 requires SSURGO identity for every included environment.")

    planting = pd.to_datetime(env["planting_date"], errors="raise")
    doy = planting.dt.dayofyear.astype(float)
    soil = pd.get_dummies(
        state["ssurgo_mukey"].astype(str), prefix="soil_mukey", dtype=float
    )
    population = pd.to_numeric(
        env.get("plant_population_proxy", pd.Series(index=env.index, dtype=float)),
        errors="coerce",
    )
    common = pd.DataFrame(index=env.index)
    common["latitude"] = pd.to_numeric(env["latitude"], errors="raise")
    common["longitude"] = pd.to_numeric(env["longitude"], errors="raise")
    common["planting_doy_sin"] = np.sin(2.0 * np.pi * doy / 365.25)
    common["planting_doy_cos"] = np.cos(2.0 * np.pi * doy / 365.25)
    common["plant_population_proxy"] = population.fillna(0.0)
    common["plant_population_missing"] = population.isna().astype(float)
    common = pd.concat([common, soil], axis=1)
    matrix = pd.concat(
        [state[list(WEATHER_COLUMNS)].apply(pd.to_numeric, errors="raise"), common],
        axis=1,
    ).astype(float)
    if matrix.isna().any().any():
        raise ValueError("B12 combined T1 matrix contains missing values.")
    return matrix


def audit_historical_t1_encoding(
    states: pd.DataFrame, manifest: pd.DataFrame
) -> None:
    frozen, _ = build_environment_state_matrices(states, manifest)
    reference = frozen[HORIZON]
    candidate = build_combined_t1_matrix(
        states,
        manifest,
        states.iloc[0:0].copy(),
        manifest.iloc[0:0].copy(),
    )
    if list(candidate.index) != list(reference.index):
        raise ValueError("B12 T1 encoder changed historical environment order.")
    if list(candidate.columns) != list(reference.columns):
        raise ValueError("B12 T1 encoder changed historical feature structure.")
    if not np.array_equal(candidate.to_numpy(float), reference.to_numpy(float)):
        raise ValueError("B12 T1 encoder does not exactly reproduce frozen B10 values.")


def build_supported_test_cells(
    submission: pd.DataFrame,
    frozen_genotypes: set[str],
    supported_environments: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    g_col, e_col = submission_columns(submission)
    cells = submission[[g_col, e_col]].copy()
    cells.columns = ["genotype", "environment"]
    cells = cells.dropna().drop_duplicates().reset_index(drop=True)
    cells["genotype"] = cells["genotype"].astype(str)
    cells["environment"] = cells["environment"].astype(str)
    cells["genotype_support_state"] = np.where(
        cells["genotype"].isin(frozen_genotypes),
        SUPPORTED_GENOTYPE,
        UNSUPPORTED_GENOTYPE,
    )
    cells["environment_input_state"] = np.where(
        cells["environment"].isin(supported_environments),
        SUPPORTED_ENVIRONMENT,
        UNSUPPORTED_ENVIRONMENT,
    )
    audit = (
        cells.groupby(["genotype_support_state", "environment_input_state"])
        .agg(
            n_cells=("genotype", "size"),
            n_genotypes=("genotype", "nunique"),
            n_environments=("environment", "nunique"),
        )
        .reset_index()
    )
    eligible = cells[
        cells["genotype_support_state"].eq(SUPPORTED_GENOTYPE)
        & cells["environment_input_state"].eq(SUPPORTED_ENVIRONMENT)
    ].copy()
    return eligible, audit


def historical_calibration_table(
    root: Path,
    states: pd.DataFrame,
    env_manifest: pd.DataFrame,
    forward: pd.DataFrame,
) -> pd.DataFrame:
    predictions = build_forward_t1_predictions(root, states, env_manifest, forward)
    support = build_t1_support_table(states, env_manifest, forward)
    cells = predictions.merge(
        support[["environment", "test_year", "train_year_max", "support_group"]],
        on=["environment", "test_year", "train_year_max"],
        validate="many_to_one",
    )
    if cells["support_group"].isna().any():
        raise ValueError("B12 cannot reconstruct B11 support groups.")
    if int(cells["test_year"].max()) >= TARGET_YEAR:
        raise SealViolation("B12 calibration includes target/future-year outcomes.")
    return cells


def _quantiles(
    calibration: pd.DataFrame, support_state: str
) -> dict[int, tuple[float, str]]:
    result = {}
    group = calibration[calibration["support_group"].astype(str).eq(support_state)]
    enough = int(group["environment"].nunique()) >= 5 and len(group) >= 200
    for level in NOMINAL_LEVELS:
        key = int(round(100 * level))
        global_q = finite_sample_quantile(calibration["absolute_error"], level)
        if enough:
            result[key] = (
                finite_sample_quantile(group["absolute_error"], level),
                "SUPPORT_GROUP_CHRONOLOGICAL_2016_2021",
            )
        else:
            result[key] = (
                float(global_q),
                "GLOBAL_CHRONOLOGICAL_2016_2021_FALLBACK",
            )
    return result


def _predict_supported(
    root: Path, test_cells: pd.DataFrame, t1_matrix: pd.DataFrame
) -> tuple[pd.DataFrame, set[str]]:
    pheno, geno, ecov = load_materialized(root)
    train, geno, _, cols = prepare_cells(pheno, geno, ecov)
    train["genotype"] = train["genotype"].astype(str)
    train["environment"] = train["environment"].astype(str)
    train_envs = set(train["environment"])
    gmap = genomic_map(
        geno, cols["geno_id"], set(train["genotype"]), rank=FROZEN_CONFIG.g_rank
    )
    erank = min(FROZEN_CONFIG.e_rank, max(1, len(train_envs) - 1))
    emap = environment_map(
        t1_matrix,
        train_envs,
        erank,
        FROZEN_CONFIG.gamma_multiplier,
    )
    tg, te = cell_features(train, gmap, emap)
    vg, ve = cell_features(test_cells, gmap, emap)
    prediction = predict(
        "G+E",
        tg,
        te,
        train["observed"].to_numpy(float),
        vg,
        ve,
        FROZEN_CONFIG.alpha,
    )
    out = test_cells.copy()
    out["predicted"] = np.asarray(prediction, dtype=float)
    return out, train_envs


def _attach_support_and_intervals(
    predictions: pd.DataFrame,
    t1_matrix: pd.DataFrame,
    train_envs: set[str],
    calibration: pd.DataFrame,
) -> pd.DataFrame:
    support, _ = support_geometry(
        t1_matrix,
        train_envs,
        set(predictions["environment"].astype(str)),
        gamma_multiplier=FROZEN_CONFIG.gamma_multiplier,
        retained_rank=FROZEN_CONFIG.e_rank,
        prefix="full",
    )
    support["support_group"] = support["full_nearest_percentile"].map(support_group)
    support["reliability_state"] = np.where(
        support["support_group"].eq(SUPPORT_EDGE), ABSTAIN, RETAIN
    )
    keep = [
        "environment",
        "full_nearest_distance",
        "full_nearest_percentile",
        "full_max_training_kernel_similarity",
        "support_group",
        "reliability_state",
    ]
    out = predictions.merge(support[keep], on="environment", validate="many_to_one")
    for state in (SUPPORT_WITHIN, SUPPORT_EDGE):
        q = _quantiles(calibration, state)
        mask = out["support_group"].astype(str).eq(state)
        for key, (half_width, source) in q.items():
            out.loc[mask, f"interval_half_width_{key}"] = half_width
            out.loc[mask, f"interval_source_{key}"] = source
            out.loc[mask, f"lower_{key}"] = out.loc[mask, "predicted"] - half_width
            out.loc[mask, f"upper_{key}"] = out.loc[mask, "predicted"] + half_width
    out["test_year"] = TARGET_YEAR
    out["model"] = MODEL
    out["horizon"] = HORIZON
    out["support_boundary_uses_outcome"] = False
    return out


def canonical_prediction_bytes(frame: pd.DataFrame) -> bytes:
    required = {
        "genotype",
        "environment",
        "predicted",
        "reliability_state",
        "genotype_support_state",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"B12 seal frame missing columns: {sorted(missing)}")
    canonical = frame.sort_values(["environment", "genotype"]).reset_index(drop=True)
    buffer = io.StringIO()
    canonical.to_csv(
        buffer,
        index=False,
        lineterminator="\n",
        float_format="%.12g",
    )
    return buffer.getvalue().encode("utf-8")


def write_prediction_seal(
    frame: pd.DataFrame,
    prediction_path: Path,
    seal_path: Path,
    metadata: dict[str, object],
) -> dict[str, object]:
    body = canonical_prediction_bytes(frame)
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    prediction_path.write_bytes(body)
    seal = {
        "schema": SEAL_SCHEMA,
        "target_year": TARGET_YEAR,
        "prediction_file": prediction_path.name,
        "prediction_sha256": _sha256_bytes(body),
        "n_predictions": int(len(frame)),
        "n_environments": int(frame["environment"].nunique()),
        "n_genotypes": int(frame["genotype"].nunique()),
        "observed_outcomes_accessed": False,
        "t2_branch_reopened": False,
        "predictive_hyperparameters_changed": False,
        "post_result_tuning_permitted": False,
        **metadata,
    }
    seal_path.write_text(
        json.dumps(seal, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return seal


def verify_prediction_seal(
    prediction_path: Path, seal_path: Path
) -> dict[str, object]:
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("schema") != SEAL_SCHEMA:
        raise SealViolation("B12 prediction seal schema mismatch.")
    if sha256_file(prediction_path) != seal.get("prediction_sha256"):
        raise SealViolation("B12 prediction artifact does not match the frozen SHA-256.")
    if bool(seal.get("observed_outcomes_accessed", True)):
        raise SealViolation("B12 Stage-A seal reports outcome access.")
    return seal


def run_stage_a(root: Path) -> dict[str, Path]:
    results = root / "reports" / "results"
    raw = root / "data" / "raw" / "case_study_b12_2022_sealed"
    assert_blind_stage([raw])

    b11 = pd.read_csv(results / "case_study_b11_branch_decision.csv")
    if not b11["branch_decision"].astype(str).eq(
        "ADMIT_FORWARD_INTERVALS_KEEP_SUPPORT_ABSTENTION_DIAGNOSTIC"
    ).all():
        raise ValueError("B12 requires the admitted B11 interval layer.")
    if b11["t2_branch_reopened"].astype(bool).any():
        raise SealViolation("B12 refuses a repository state that reopens T2.")

    states = pd.read_csv(results / "case_study_b9_safe_environment_states.csv")
    env_manifest = pd.read_csv(results / "case_study_b9_environment_manifest.csv")
    forward = pd.read_csv(results / "case_study_b9_forward_year_folds.csv")
    audit_historical_t1_encoding(states, env_manifest)

    safe = acquire_stage_a_inputs(root)
    submission = pd.read_csv(safe["submission"], low_memory=False)
    metadata = pd.read_csv(safe["metadata"], low_memory=False)
    test_manifest_all = competition_environment_manifest(metadata, submission)
    test_states, environment_audit = build_2022_t1_states(test_manifest_all)
    supported_envs = set(test_states["environment"].astype(str))
    test_manifest = test_manifest_all[
        test_manifest_all["environment"].astype(str).isin(supported_envs)
    ].copy()
    t1_matrix = build_combined_t1_matrix(
        states, env_manifest, test_states, test_manifest
    )

    pheno, geno, ecov = load_materialized(root)
    _, geno, _, cols = prepare_cells(pheno, geno, ecov)
    frozen_genotypes = set(geno[cols["geno_id"]].astype(str))
    eligible, support_audit = build_supported_test_cells(
        submission, frozen_genotypes, supported_envs
    )
    if eligible.empty:
        raise ValueError(
            "B12 has zero cells jointly supported by frozen genotype vectors and T1 context."
        )

    predictions, train_envs = _predict_supported(root, eligible, t1_matrix)
    calibration = historical_calibration_table(root, states, env_manifest, forward)
    predictions = _attach_support_and_intervals(
        predictions, t1_matrix, train_envs, calibration
    )

    input_audit = pd.DataFrame(
        [
            {
                "source_doi": SOURCE_DOI,
                "target_year": TARGET_YEAR,
                "n_submission_cells": int(len(submission)),
                "n_submission_environments": int(
                    submission[submission_columns(submission)[1]].nunique()
                ),
                "n_supported_prediction_cells": int(len(predictions)),
                "n_supported_genotypes": int(predictions["genotype"].nunique()),
                "n_supported_environments": int(predictions["environment"].nunique()),
                "n_calibration_years": int(calibration["test_year"].nunique()),
                "calibration_year_min": int(calibration["test_year"].min()),
                "calibration_year_max": int(calibration["test_year"].max()),
                "answer_file_accessed": False,
                "weather_after_30dap_requested": False,
                "predictive_hyperparameters_changed": False,
                "t2_branch_reopened": False,
                "post_result_tuning_permitted": False,
            }
        ]
    )

    paths = {
        "predictions": results / "case_study_b12_2022_sealed_predictions.csv",
        "seal": results / "case_study_b12_2022_prediction_seal.json",
        "input_audit": results / "case_study_b12_2022_input_audit.csv",
        "environment_audit": results / "case_study_b12_2022_environment_input_audit.csv",
        "support_audit": results / "case_study_b12_2022_support_audit.csv",
        "decision": results / "case_study_b12a_seal_decision.csv",
    }
    results.mkdir(parents=True, exist_ok=True)
    input_audit.to_csv(paths["input_audit"], index=False)
    environment_audit.to_csv(paths["environment_audit"], index=False)
    support_audit.to_csv(paths["support_audit"], index=False)
    seal = write_prediction_seal(
        predictions,
        paths["predictions"],
        paths["seal"],
        {
            "source_doi": SOURCE_DOI,
            "supported_predictor": MODEL,
            "evaluated_horizon": HORIZON,
            "calibration_years": "2016-2021",
            "genotype_support_rule": SUPPORTED_GENOTYPE,
            "environment_support_rule": "B11_FROZEN_TRAINING_NN_ENVELOPE",
        },
    )
    pd.DataFrame(
        [
            {
                "stage": "B12A",
                "decision": "SEALED_2022_PREDICTIONS_READY_FOR_REVEAL",
                "prediction_sha256": seal["prediction_sha256"],
                "n_predictions": seal["n_predictions"],
                "n_environments": seal["n_environments"],
                "n_genotypes": seal["n_genotypes"],
                "observed_outcomes_accessed": False,
                "t2_branch_reopened": False,
                "post_result_tuning_permitted": False,
            }
        ]
    ).to_csv(paths["decision"], index=False)
    assert_blind_stage([raw])
    return paths


def _answer_columns(answer: pd.DataFrame) -> tuple[str, str, str]:
    return (
        _required(answer, ("Hybrid", "hybrid", "Genotype", "genotype"), "answer genotype"),
        _required(answer, ("Env", "environment", "Environment"), "answer environment"),
        _required(
            answer,
            ("Yield_Mg_ha", "yield", "Yield", "grain_yield", "Observed"),
            "answer yield",
        ),
    )


def evaluate_reveal(
    prediction_path: Path,
    seal_path: Path,
    answer_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    seal = verify_prediction_seal(prediction_path, seal_path)
    if _normalized(answer_path.name) != _normalized(FORBIDDEN_ANSWER_BASENAME):
        raise ValueError("B12 reveal requires the official observed-answer basename.")

    predictions = pd.read_csv(prediction_path)
    answer = pd.read_csv(answer_path, low_memory=False)
    g_col, e_col, y_col = _answer_columns(answer)
    observed = answer[[g_col, e_col, y_col]].copy()
    observed.columns = ["genotype", "environment", "observed"]
    observed["genotype"] = observed["genotype"].astype(str)
    observed["environment"] = observed["environment"].astype(str)
    observed["observed"] = pd.to_numeric(observed["observed"], errors="coerce")
    observed = observed.dropna(subset=["observed"]).drop_duplicates(
        ["genotype", "environment"]
    )

    evaluated = predictions.merge(
        observed,
        on=["genotype", "environment"],
        how="left",
        validate="one_to_one",
    )
    if evaluated["observed"].isna().any():
        raise ValueError("The official answer misses one or more sealed B12 cells.")

    coverage_rows = []
    for level in NOMINAL_LEVELS:
        key = int(round(100 * level))
        covered_col = f"_covered_{key}"
        evaluated[covered_col] = (
            (evaluated["observed"] >= evaluated[f"lower_{key}"])
            & (evaluated["observed"] <= evaluated[f"upper_{key}"])
        )
        low, high = _cluster_coverage_ci(evaluated, covered_col)
        env_cov = evaluated.groupby("environment")[covered_col].mean()
        coverage_rows.append(
            {
                "nominal": float(level),
                "n": int(len(evaluated)),
                "n_environments": int(evaluated["environment"].nunique()),
                "empirical_coverage": float(evaluated[covered_col].mean()),
                "environment_balanced_coverage": float(env_cov.mean()),
                "environment_cluster_ci95_low": low,
                "environment_cluster_ci95_high": high,
                "mean_interval_width": float(
                    (evaluated[f"upper_{key}"] - evaluated[f"lower_{key}"]).mean()
                ),
                "absolute_coverage_gap": abs(
                    float(evaluated[covered_col].mean()) - float(level)
                ),
            }
        )
    coverage = pd.DataFrame(coverage_rows)

    reliability_rows = []
    for state in ("ALL_EVALUATED", RETAIN, ABSTAIN):
        part = (
            evaluated
            if state == "ALL_EVALUATED"
            else evaluated[evaluated["reliability_state"].astype(str).eq(state)]
        )
        if part.empty:
            continue
        reliability_rows.append(
            {
                "state": state,
                "n": int(len(part)),
                "n_environments": int(part["environment"].nunique()),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    reliability = pd.DataFrame(reliability_rows)

    c90 = coverage[np.isclose(coverage["nominal"], 0.90)].iloc[0]
    interval_supported = bool(
        abs(float(c90["empirical_coverage"]) - 0.90) <= 0.03
        and float(c90["environment_cluster_ci95_low"])
        <= 0.90
        <= float(c90["environment_cluster_ci95_high"])
    )
    all_row = reliability[reliability["state"].eq("ALL_EVALUATED")].iloc[0]
    retained = reliability[reliability["state"].eq(RETAIN)]
    abstained = reliability[reliability["state"].eq(ABSTAIN)]
    abstained_envs = int(abstained["n_environments"].iloc[0]) if len(abstained) else 0
    retained_rmse = float(retained["rmse"].iloc[0]) if len(retained) else np.nan
    abstained_rmse = float(abstained["rmse"].iloc[0]) if len(abstained) else np.nan
    support_supported = bool(
        abstained_envs >= MIN_SUPPORT_GROUP_ENVIRONMENTS
        and np.isfinite(retained_rmse)
        and np.isfinite(abstained_rmse)
        and retained_rmse < float(all_row["rmse"])
        and abstained_rmse > retained_rmse
    )
    if not interval_supported:
        decision = "B12_2022_CALIBRATION_TRANSPORT_FAILURE"
    elif support_supported:
        decision = "B12_2022_EXTERNAL_INTERVALS_AND_SUPPORT_ABSTENTION_PASS"
    else:
        decision = "B12_2022_EXTERNAL_INTERVALS_PASS_SUPPORT_ABSTENTION_DIAGNOSTIC"

    summary = pd.DataFrame(
        [
            {
                "target_year": TARGET_YEAR,
                "prediction_sha256": seal["prediction_sha256"],
                "answer_sha256": sha256_file(answer_path),
                "n_evaluated": int(len(evaluated)),
                "n_environments": int(evaluated["environment"].nunique()),
                "n_genotypes": int(evaluated["genotype"].nunique()),
                **metrics(evaluated["observed"], evaluated["predicted"]),
                "coverage_90": float(c90["empirical_coverage"]),
                "coverage_90_env_ci_low": float(
                    c90["environment_cluster_ci95_low"]
                ),
                "coverage_90_env_ci_high": float(
                    c90["environment_cluster_ci95_high"]
                ),
                "interval_external_validation_supported": interval_supported,
                "abstained_environments": abstained_envs,
                "support_abstention_external_validation_supported": support_supported,
                "predictive_model_refit_after_reveal": False,
                "interval_retuned_after_reveal": False,
                "support_threshold_retuned_after_reveal": False,
                "t2_branch_reopened": False,
                "post_result_tuning_permitted": False,
                "decision": decision,
            }
        ]
    )
    return summary, coverage, reliability


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Case Study B12 sealed 2022 external temporal validation."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--stage", choices=("seal", "reveal"), required=True)
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--download-answer", action="store_true")
    args = parser.parse_args()
    root = args.output_root.resolve()

    if args.stage == "seal":
        paths = run_stage_a(root)
        print("Case Study B12A sealed prediction stage complete")
        for key, path in paths.items():
            print(f"{key}: {path}")
        return

    results = root / "reports" / "results"
    answer = args.answer_file
    if answer is None and args.download_answer:
        answer = acquire_stage_b_answer(root)
    if answer is None:
        raise SystemExit("B12 reveal requires --answer-file or --download-answer.")
    summary, coverage, reliability = evaluate_reveal(
        results / "case_study_b12_2022_sealed_predictions.csv",
        results / "case_study_b12_2022_prediction_seal.json",
        answer,
    )
    summary.to_csv(
        results / "case_study_b12_2022_external_validation_summary.csv",
        index=False,
    )
    coverage.to_csv(
        results / "case_study_b12_2022_external_coverage.csv",
        index=False,
    )
    reliability.to_csv(
        results / "case_study_b12_2022_external_reliability.csv",
        index=False,
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
