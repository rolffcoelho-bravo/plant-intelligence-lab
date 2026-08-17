"""Case Study B13: sequential calibration-drift adaptation with a sealed 2023 test.

B13 keeps the B10/B11 point predictor frozen and uses the already-revealed 2022
B12 outcomes only to update forecast uncertainty.  The target 2023 outcomes are
forbidden during Stage A.

Two interval systems are sealed for the same 2023 predictions:

1. B11_FROZEN:
   the B11/B12 strictly chronological interval half-widths calibrated from
   2016-2021 forward residuals.
2. B13_RECENCY_ENVELOPE:
   max(B11_FROZEN half-width, finite-sample quantile of the observable sealed
   2022 B12 absolute residuals) at each nominal level.

The recency envelope is deterministic, may only preserve or widen an interval,
does not refit the predictor, and is frozen before any 2023 yield is read.

Stage A obtains only the harmonized 2014-2023 metadata distributed with the
G2F 2024 competition, filters it to 2023, reconstructs T1-safe environment
states, predicts an outcome-free Cartesian roster of frozen B5 genotypes by
supported 2023 environments, and seals both interval systems plus the drift
policy.

Stage B verifies both prediction and drift-policy hashes before acquiring the
harmonized 2014-2023 trait file.  Evaluation uses the exact sealed keys having
at least one finite 2023 yield in that file.  Key inclusion may depend on
outcome availability but never on outcome magnitude; finite plot yields are
predeclared to be aggregated by arithmetic mean within exact genotype-
environment key.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

import numpy as np
import pandas as pd
import requests

from plant_intelligence.data.maize_prospective_environment import (
    POWER_PARAMETERS,
    aggregate_weather,
    query_ssurgo_point,
)
from plant_intelligence.models.maize_environment_transfer import prepare_cells
from plant_intelligence.models.maize_environment_transfer_robustness import (
    load_materialized,
    metrics,
)
from plant_intelligence.models.maize_forecast_time_prediction import (
    FROZEN_CONFIG,
    WEATHER_COLUMNS,
)
from plant_intelligence.models.maize_forward_support_diagnostics import support_geometry
from plant_intelligence.uncertainty import maize_b12_cyverse_source as b12_source
from plant_intelligence.uncertainty import maize_b12_reveal_runner as b12_reveal
from plant_intelligence.uncertainty import maize_external_temporal_validation as b12
from plant_intelligence.uncertainty.maize_b12_available_case_diagnostic import (
    _load_official_answer,
)
from plant_intelligence.uncertainty.maize_forward_uncertainty import (
    ABSTAIN,
    HORIZON,
    MODEL,
    NOMINAL_LEVELS,
    RETAIN,
    SUPPORT_EDGE,
    SUPPORT_WITHIN,
    _cluster_coverage_ci,
    finite_sample_quantile,
    support_group,
)

TARGET_YEAR = 2023
SOURCE_DOI = "10.25739/78mn-4394"
FIELD_SEASON_DOI = "10.25739/rzzy-3n27"
CKAN_PACKAGE_URL = (
    "https://dc.cyverse.org/api/3/action/package_show"
    "?id=genomes_to_fields_2024_maize_genotype_by_environment_prediction_competition"
)
CYVERSE_DATASET = "GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2025"
TRAINING_FOLDER = "Training_data"
METADATA_BASENAME = "2_Training_Meta_Data_2014_2023.csv"
TARGET_TRAIT_BASENAME = "1_Training_Trait_Data_2014_2023.csv"
SUPPLEMENTAL_ROOT = "https://data.cyverse.org/dav/iplant/home/shared/commons_repo/curated/GenomesToFields_G2F_data_2023/z._2023_supplemental_info"
USER_AGENT = "plant-intelligence-lab/0.1 B13 sequential-drift-calibration"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

SEAL_SCHEMA = "plant-intelligence-lab/b13-prediction-seal/v1"
POLICY_SCHEMA = "plant-intelligence-lab/b13-drift-policy/v1"
BASELINE_METHOD = "B11_FROZEN"
ADAPTIVE_METHOD = "B13_RECENCY_ENVELOPE"
EVALUATION_POLICY = "PREDECLARED_2023_FINITE_YIELD_KEY_INTERSECTION"
ROSTER_POLICY = "FROZEN_B5_GENOTYPES_X_SUPPORTED_2023_ENVIRONMENTS"
AGGREGATION_POLICY = "ARITHMETIC_MEAN_OF_FINITE_PLOT_YIELDS_BY_EXACT_KEY"
MIN_EVALUATION_CELLS = 100
MIN_EVALUATION_ENVIRONMENTS = 5

SUPPORTED_GENOTYPE = "SUPPORTED_FROZEN_B5_GENOME"
SUPPORTED_ENVIRONMENT = "SUPPORTED_T1_CONTEXT"
UNSUPPORTED_ENVIRONMENT = "UNSUPPORTED_T1_CONTEXT"


class B13ProtocolViolation(RuntimeError):
    """Raised when a B13 chronology or seal boundary is violated."""


def _norm(value: object) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def _sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_column(
    frame: pd.DataFrame,
    candidates: Iterable[str],
    label: str,
    contains: Iterable[tuple[str, ...]] = (),
) -> str:
    normalized = {_norm(column): str(column) for column in frame.columns}
    for candidate in candidates:
        hit = normalized.get(_norm(candidate))
        if hit is not None:
            return hit
    for tokens in contains:
        token_norm = tuple(_norm(token) for token in tokens)
        for column in frame.columns:
            value = _norm(column)
            if all(token in value for token in token_norm):
                return str(column)
    raise ValueError(f"B13 cannot resolve {label}; columns={list(frame.columns)}")


def _optional_column(
    frame: pd.DataFrame,
    candidates: Iterable[str],
    contains: Iterable[tuple[str, ...]] = (),
) -> str | None:
    try:
        return _find_column(frame, candidates, "optional column", contains)
    except ValueError:
        return None


def assert_target_blind(paths: Iterable[Path]) -> None:
    forbidden = _norm(TARGET_TRAIT_BASENAME)
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        items = [root] if root.is_file() else root.rglob("*")
        for item in items:
            if item.is_file() and _norm(item.name) == forbidden:
                raise B13ProtocolViolation(
                    f"B13 Stage A refuses target 2023 outcomes at {item}"
                )


def _registry_payload(timeout: int = 60) -> dict[str, object]:
    response = requests.get(
        CKAN_PACKAGE_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=(20, timeout),
    )
    response.raise_for_status()
    payload = response.json()
    if not bool(payload.get("success")) or not isinstance(payload.get("result"), dict):
        raise RuntimeError("B13 CyVerse CKAN package_show returned no dataset result.")
    return payload


def _authenticated_url(url: str) -> str:
    parts = urlsplit(str(url))
    path = parts.path.replace("/dav-anon/", "/dav/", 1)
    return urlunsplit(("https", parts.netloc, path, parts.query, ""))


def _source_candidates(payload: dict[str, object], basename: str) -> list[tuple[str, bool]]:
    """Return candidate URLs with whether anonymous-WebDAV auth is required."""

    roots: list[str] = []

    def add_root(value: str) -> None:
        if value and value.rstrip("/") not in roots:
            roots.append(value.rstrip("/"))

    for value in b12_source._all_strings(payload.get("result", {})):
        irods = b12_source._irods_path_from_string(value)
        if irods:
            lower = irods.lower()
            token = f"/{TRAINING_FOLDER.lower()}"
            if token in lower:
                index = lower.find(token) + len(token)
                add_root("https://data.cyverse.org/dav-anon" + irods[:index])
            else:
                add_root(
                    "https://data.cyverse.org/dav-anon"
                    + irods.rstrip("/")
                    + f"/{TRAINING_FOLDER}"
                )
        clean = b12_source._clean_http_url(value)
        if clean:
            parts = urlsplit(clean)
            lower = parts.path.lower()
            token = f"/{TRAINING_FOLDER.lower()}"
            if token in lower:
                index = lower.find(token) + len(token)
                add_root(
                    urlunsplit(("https", parts.netloc, parts.path[:index], "", ""))
                )

    historical_roots = (
        f"/iplant/home/shared/commons_repo/curated/{CYVERSE_DATASET}/{TRAINING_FOLDER}",
        f"/iplant/commons/cyverse_curated/{CYVERSE_DATASET}/{TRAINING_FOLDER}",
    )
    for root in historical_roots:
        add_root("https://data.cyverse.org/dav-anon" + root)

    candidates: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for root in roots:
        anon = f"{root.rstrip('/')}/{basename}"
        auth = _authenticated_url(anon)
        for url, needs_auth in ((auth, True), (anon, False)):
            if url not in seen:
                seen.add(url)
                candidates.append((url, needs_auth))
    return candidates


def _schema_ok(basename: str, body: bytes) -> bool:
    try:
        frame = pd.read_csv(io.BytesIO(body), nrows=12, low_memory=False)
    except Exception:
        return False
    if frame.empty and len(frame.columns) <= 1:
        return False

    def has(candidates: Iterable[str], contains: Iterable[tuple[str, ...]] = ()) -> bool:
        try:
            _find_column(frame, candidates, "schema", contains)
            return True
        except ValueError:
            return False

    env_ok = has(("Env", "Environment", "environment"), (("env",),))
    if basename == METADATA_BASENAME:
        year_ok = has(("Year", "year"), (("year",),))
        lat_ok = has(
            ("Weather_Station_Latitude", "Latitude", "Lat"),
            (("lat",),),
        )
        lon_ok = has(
            ("Weather_Station_Longitude", "Longitude", "Lon", "Long"),
            (("lon",), ("long",)),
        )
        return env_ok and year_ok and lat_ok and lon_ok

    if basename == TARGET_TRAIT_BASENAME:
        genotype_ok = has(
            ("Hybrid", "Genotype", "hybrid", "genotype"),
            (("hybrid",), ("genotype",)),
        )
        yield_ok = has(
            (
                "Yield_Mg_ha",
                "Yield",
                "yield",
                "grain_yield",
                "Grain_Yield",
                "Observed",
            ),
            (("yield",),),
        )
        return env_ok and genotype_ok and yield_ok
    return False


def download_competition_file(
    basename: str,
    destination: Path,
    *,
    allow_target_outcome: bool,
    timeout: int = 180,
) -> tuple[Path, dict[str, object]]:
    if basename == TARGET_TRAIT_BASENAME and not allow_target_outcome:
        raise B13ProtocolViolation(
            "B13 Stage A cannot acquire the 2014-2023 trait file containing 2023 outcomes."
        )
    if basename not in {METADATA_BASENAME, TARGET_TRAIT_BASENAME}:
        raise ValueError(f"B13 source resolver refuses unknown file {basename!r}.")

    payload = _registry_payload()
    attempts: list[dict[str, object]] = []
    for url, needs_auth in _source_candidates(payload, basename):
        try:
            kwargs: dict[str, object] = {
                "headers": {
                    "User-Agent": USER_AGENT,
                    "Accept": "text/csv,*/*;q=0.5",
                },
                "timeout": (30, timeout),
                "allow_redirects": False if needs_auth else True,
            }
            if needs_auth:
                kwargs["auth"] = ("anonymous", "")
            response = requests.get(url, **kwargs)
            attempts.append(
                {
                    "url": url,
                    "status": int(response.status_code),
                    "content_type": response.headers.get("content-type", ""),
                    "size": len(response.content),
                    "redirect": bool(response.is_redirect),
                    "html_like": b12_source._is_html_response(response),
                }
            )
            response.raise_for_status()
            if response.is_redirect or not response.content:
                continue
            if b12_source._is_html_response(response):
                continue
            if not _schema_ok(basename, response.content):
                try:
                    header = pd.read_csv(
                        io.BytesIO(response.content),
                        nrows=0,
                        low_memory=False,
                    )
                    attempts[-1]["parsed_columns"] = list(map(str, header.columns))
                except Exception as header_exc:
                    attempts[-1]["header_error"] = (
                        f"{type(header_exc).__name__}: {header_exc}"
                    )
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
            return destination, {
                "source_url": str(response.url),
                "sha256": _sha256_bytes(response.content),
                "size_bytes": int(len(response.content)),
                "source_doi": SOURCE_DOI,
                "field_season_doi": FIELD_SEASON_DOI,
            }
        except Exception as exc:
            attempts.append(
                {"url": url, "error": f"{type(exc).__name__}: {exc}"}
            )
    raise RuntimeError(
        f"B13 could not acquire schema-valid {basename}: "
        + json.dumps(attempts[-30:], indent=2)
    )


def acquire_target_metadata(root: Path) -> tuple[Path, dict[str, object]]:
    raw = root / "data" / "raw" / "case_study_b13_2023_sealed"
    raw.mkdir(parents=True, exist_ok=True)
    assert_target_blind([raw])
    return download_competition_file(
        METADATA_BASENAME,
        raw / METADATA_BASENAME,
        allow_target_outcome=False,
    )


def acquire_target_trait(root: Path) -> tuple[Path, dict[str, object]]:
    raw = root / "data" / "raw" / "case_study_b13_2023_reveal"
    return download_competition_file(
        TARGET_TRAIT_BASENAME,
        raw / TARGET_TRAIT_BASENAME,
        allow_target_outcome=True,
    )


def _target_year_mask(frame: pd.DataFrame, env_col: str) -> pd.Series:
    year_col = _optional_column(
        frame,
        ("Year", "year", "Harvest_Year", "Season"),
        (("year",),),
    )
    if year_col is not None:
        year = pd.to_numeric(frame[year_col], errors="coerce")
        if year.notna().any():
            return year.eq(TARGET_YEAR)
    return frame[env_col].astype(str).str.contains(str(TARGET_YEAR), regex=False)


def discover_2023_planting_dates(
    timeout: int = 180,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Resolve exact 2023 planting dates from outcome-free supplemental data.

    The resolver is hard-scoped to ``z._2023_supplemental_info`` in the public
    2023 field-season release. It never traverses or requests the sibling
    phenotypic directory.
    """
    if "a._2023_phenotypic_data" in SUPPLEMENTAL_ROOT.lower():
        raise B13ProtocolViolation("B13 supplemental root points at phenotypic data.")

    prop = None
    resolved_propfind_url = ""
    propfind_attempts: list[dict[str, object]] = []
    propfind_candidates = [
        SUPPLEMENTAL_ROOT.rstrip("/") + "/",
        SUPPLEMENTAL_ROOT.replace("/dav/", "/dav-anon/").rstrip("/") + "/",
    ]
    for candidate in propfind_candidates:
        current = candidate
        for _ in range(5):
            needs_auth = "/dav/" in current
            response = requests.request(
                "PROPFIND",
                current,
                auth=("anonymous", "") if needs_auth else None,
                headers={"User-Agent": USER_AGENT, "Depth": "3"},
                timeout=(30, timeout),
                allow_redirects=False,
            )
            propfind_attempts.append(
                {
                    "url": current,
                    "status": int(response.status_code),
                    "location": response.headers.get("location", ""),
                    "content_type": response.headers.get("content-type", ""),
                    "size": int(len(response.content)),
                }
            )
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    break
                current = urljoin(current, location)
                if "a._2023_phenotypic_data" in current.lower():
                    raise B13ProtocolViolation(
                        "B13 supplemental redirect crossed into phenotypic data."
                    )
                continue
            if response.status_code == 207:
                prop = response
                resolved_propfind_url = current
            break
        if prop is not None:
            break

    if prop is None:
        raise RuntimeError(
            "B13 could not list the outcome-free 2023 supplemental directory "
            "with PROPFIND after preserving redirects. Safe diagnostics: "
            + json.dumps(propfind_attempts, indent=2)
        )
    if b"<html" in prop.content[:2000].lower():
        raise RuntimeError(
            "B13 supplemental PROPFIND returned HTML instead of WebDAV XML: "
            + json.dumps(propfind_attempts, indent=2)
        )

    tree = ET.fromstring(prop.content)
    hrefs: list[str] = []
    for node in tree.iter():
        if node.tag.endswith("href") and node.text:
            href = str(node.text)
            low = href.lower()
            if "a._2023_phenotypic_data" in low:
                raise B13ProtocolViolation(
                    "B13 supplemental listing unexpectedly crossed into phenotypic data."
                )
            if href not in hrefs:
                hrefs.append(href)

    probes: list[dict[str, object]] = []
    for href in hrefs:
        low = href.lower()
        if not low.endswith((".csv", ".txt", ".tsv")):
            continue
        url = href if href.startswith("http") else "https://data.cyverse.org" + href
        url = url.replace("/dav-anon/", "/dav/")
        try:
            response = requests.get(
                url,
                auth=("anonymous", ""),
                headers={"User-Agent": USER_AGENT, "Accept": "text/csv,text/plain,*/*;q=0.2"},
                timeout=(30, timeout),
                allow_redirects=True,
            )
            response.raise_for_status()
            if not response.content or b"<html" in response.content[:2000].lower():
                probes.append(
                    {
                        "url": url,
                        "status": int(response.status_code),
                        "content_type": response.headers.get("content-type", ""),
                        "html_like": True,
                    }
                )
                continue

            sep = "\t" if low.endswith(".tsv") else ","
            header = pd.read_csv(
                io.BytesIO(response.content),
                nrows=0,
                sep=sep,
                low_memory=False,
            )
            columns = list(map(str, header.columns))
            probes.append({"url": url, "columns": columns})

            env_col = _optional_column(
                header,
                ("Env", "Environment", "environment"),
                (("env",),),
            )
            plant_col = _optional_column(
                header,
                (
                    "Date_Planted",
                    "Planting_Date",
                    "PlantingDate",
                    "date_plant",
                    "date_planted",
                    "planting_date",
                    "Sowing_Date",
                    "Planting date",
                ),
                (("plant", "date"), ("sow", "date")),
            )
            if env_col is None or plant_col is None:
                continue

            frame = pd.read_csv(
                io.BytesIO(response.content),
                sep=sep,
                low_memory=False,
            )
            target = frame.loc[_target_year_mask(frame, env_col)].copy()
            if target.empty:
                continue
            target["environment"] = target[env_col].astype(str).str.strip()
            target["planting_date"] = pd.to_datetime(
                target[plant_col], errors="coerce"
            )
            target = target.dropna(subset=["environment", "planting_date"])
            if target.empty:
                continue

            rows: list[dict[str, object]] = []
            for environment, part in target.groupby("environment", sort=True):
                values = part["planting_date"].dropna().sort_values()
                if values.empty:
                    continue
                date = values.iloc[len(values) // 2]
                rows.append(
                    {
                        "environment": str(environment),
                        "planting_date": pd.Timestamp(date).date().isoformat(),
                        "n_supplemental_records": int(len(part)),
                    }
                )
            planting = pd.DataFrame(rows)
            if planting.empty:
                continue
            return planting, {
                "source_url": str(response.url),
                "sha256": _sha256_bytes(response.content),
                "size_bytes": int(len(response.content)),
                "source_doi": FIELD_SEASON_DOI,
                "source_scope": "z._2023_supplemental_info",
                "supplemental_propfind_url": resolved_propfind_url,
                "phenotypic_data_accessed": False,
            }
        except Exception as exc:
            probes.append(
                {"url": url, "error": f"{type(exc).__name__}: {exc}"}
            )

    raise RuntimeError(
        "B13 found no exact environment-level planting-date file inside the "
        "outcome-free 2023 supplemental directory. Safe probe diagnostics: "
        + json.dumps(probes[-60:], indent=2)
    )


def target_environment_manifest(
    metadata: pd.DataFrame,
    planting_dates: pd.DataFrame,
) -> pd.DataFrame:
    env_col = _find_column(
        metadata,
        ("Env", "Environment", "environment"),
        "metadata environment",
        (("env",),),
    )
    lat_col = _find_column(
        metadata,
        ("Weather_Station_Latitude", "Latitude", "latitude", "Lat"),
        "metadata latitude",
        (("lat",),),
    )
    lon_col = _find_column(
        metadata,
        ("Weather_Station_Longitude", "Longitude", "longitude", "Lon", "Long"),
        "metadata longitude",
        (("lon",), ("long",)),
    )
    city_col = _optional_column(
        metadata,
        ("City", "city", "Location", "location", "Site", "site"),
        (("city",), ("location",)),
    )
    pop_col = _optional_column(
        metadata,
        ("Plant_Population", "PlantPopulation", "plant_population", "Plant_Density"),
        (("plant", "population"), ("plant", "density")),
    )

    target = metadata.loc[_target_year_mask(metadata, env_col)].copy()
    if target.empty:
        raise ValueError("B13 metadata contains no 2023 environment records.")

    dates = planting_dates.copy()
    if not {"environment", "planting_date"}.issubset(dates.columns):
        raise ValueError("B13 supplemental planting-date table has the wrong schema.")
    dates["environment"] = dates["environment"].astype(str).str.strip()
    if dates["environment"].duplicated().any():
        raise ValueError("B13 supplemental planting-date table is not unique by environment.")
    date_map = dates.set_index("environment")["planting_date"].astype(str).to_dict()

    rows: list[dict[str, object]] = []
    for environment, part in target.groupby(env_col, sort=True):
        environment = str(environment).strip()
        planting_raw = date_map.get(environment)
        planting = pd.to_datetime(planting_raw, errors="coerce")
        lat = pd.to_numeric(part[lat_col], errors="coerce").dropna()
        lon = pd.to_numeric(part[lon_col], errors="coerce").dropna()
        if pd.isna(planting) or lat.empty or lon.empty:
            continue

        population = np.nan
        if pop_col is not None:
            values = pd.to_numeric(part[pop_col], errors="coerce").dropna()
            if not values.empty:
                population = float(values.median())

        city = ""
        if city_col is not None and part[city_col].notna().any():
            values = part[city_col].dropna().astype(str)
            if not values.empty:
                city = str(values.mode().iloc[0])

        rows.append(
            {
                "environment": environment,
                "year": TARGET_YEAR,
                "city": city,
                "planting_date": pd.Timestamp(planting).date().isoformat(),
                "latitude": float(lat.median()),
                "longitude": float(lon.median()),
                "coordinate_source": "G2F_2024_competition_training_metadata_2014_2023",
                "planting_date_source": "G2F_2023_outcome_free_supplemental_info",
                "historical_year_city_match": "",
                "plant_population_proxy": population,
                "n_metadata_records": int(len(part)),
            }
        )

    manifest = pd.DataFrame(rows)
    if manifest.empty:
        raise ValueError(
            "B13 has no exact 2023 environment with both safe coordinates and "
            "an outcome-free supplemental planting date."
        )
    if manifest["environment"].duplicated().any():
        raise ValueError("B13 2023 environment manifest contains duplicate IDs.")
    return manifest.sort_values("environment").reset_index(drop=True)


def _power_through_t1(
    latitude: float,
    longitude: float,
    planting_date: str,
) -> pd.DataFrame:
    planting = pd.Timestamp(planting_date)
    issuance = planting + pd.Timedelta(days=30)
    response = requests.get(
        POWER_URL,
        params={
            "parameters": ",".join(POWER_PARAMETERS),
            "community": "AG",
            "longitude": f"{float(longitude):.5f}",
            "latitude": f"{float(latitude):.5f}",
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
            pd.Series(
                {
                    pd.to_datetime(key, format="%Y%m%d"): value
                    for key, value in values.items()
                }
            ),
            errors="coerce",
        ).reindex(frame.index)
    frame = frame.replace({-999.0: np.nan, -999: np.nan}).sort_index()
    if frame.empty:
        raise ValueError("NASA POWER returned no T1 weather.")
    if frame.index.min() < planting or frame.index.max() > issuance:
        raise B13ProtocolViolation("B13 POWER request violated the T1 issuance window.")
    return frame


def build_2023_t1_states(
    manifest: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    audit: list[dict[str, object]] = []
    for env in manifest.itertuples(index=False):
        try:
            weather = _power_through_t1(
                float(env.latitude),
                float(env.longitude),
                str(env.planting_date),
            )
            soil = query_ssurgo_point(float(env.latitude), float(env.longitude))
            if not bool(soil.get("ssurgo_available", False)):
                raise ValueError("SSURGO unavailable")
            wx = aggregate_weather(weather)
            if any(not np.isfinite(float(wx[column])) for column in WEATHER_COLUMNS):
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
                    "environment": str(env.environment),
                    "environment_input_state": SUPPORTED_ENVIRONMENT,
                    "reason": "",
                }
            )
        except B13ProtocolViolation:
            raise
        except Exception as exc:
            audit.append(
                {
                    "environment": str(env.environment),
                    "environment_input_state": UNSUPPORTED_ENVIRONMENT,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
    states = pd.DataFrame(rows)
    if states.empty:
        raise ValueError("B13 has no 2023 environment with complete frozen T1 context.")
    return states, pd.DataFrame(audit)


def build_outcome_free_roster(
    frozen_genotypes: Iterable[str],
    supported_environments: Iterable[str],
) -> pd.DataFrame:
    genotypes = sorted(set(map(str, frozen_genotypes)))
    environments = sorted(set(map(str, supported_environments)))
    if not genotypes or not environments:
        raise ValueError("B13 roster requires frozen genotypes and supported environments.")
    index = pd.MultiIndex.from_product(
        [genotypes, environments],
        names=["genotype", "environment"],
    )
    roster = index.to_frame(index=False)
    roster["genotype_support_state"] = SUPPORTED_GENOTYPE
    roster["environment_input_state"] = SUPPORTED_ENVIRONMENT
    roster["roster_policy"] = ROSTER_POLICY
    roster["target_outcomes_used_to_construct_roster"] = False
    return roster


def historical_2022_residuals(
    root: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    results = root / "reports" / "results"
    prediction_path = results / "case_study_b12_2022_sealed_predictions.csv"
    seal_path = results / "case_study_b12_2022_prediction_seal.json"
    status_path = results / "case_study_b12_2022_primary_status.csv"

    status = pd.read_csv(status_path)
    if not status["primary_status"].astype(str).eq(
        "B12_PRIMARY_INCOMPLETE_OFFICIAL_OUTCOME_MATCH"
    ).all():
        raise B13ProtocolViolation("B13 requires the locked B12 primary status.")
    if status["t2_branch_reopened"].astype(str).str.lower().eq("true").any():
        raise B13ProtocolViolation("B13 refuses a B12 state that reopened T2.")

    answer_destination = (
        root
        / "data"
        / "raw"
        / "case_study_b13_historical_2022"
        / b12.FORBIDDEN_ANSWER_BASENAME
    )
    answer_path, provenance = b12_reveal.acquire_answer_after_seal(
        prediction_path,
        seal_path,
        answer_destination,
    )
    predictions = pd.read_csv(prediction_path, low_memory=False)
    predictions["genotype"] = predictions["genotype"].astype(str)
    predictions["environment"] = predictions["environment"].astype(str)

    observed = _load_official_answer(answer_path)
    keys = observed[["genotype", "environment"]].drop_duplicates().copy()
    keys["official_answer_key_present"] = True
    cohort = predictions.merge(
        keys,
        on=["genotype", "environment"],
        how="left",
        validate="one_to_one",
    )
    cohort["official_answer_key_present"] = (
        cohort["official_answer_key_present"].fillna(False).astype(bool)
    )
    cohort = cohort.merge(
        observed,
        on=["genotype", "environment"],
        how="left",
        validate="one_to_one",
    )
    available = cohort[cohort["official_answer_key_present"]].copy()
    if available["observed"].isna().any():
        raise B13ProtocolViolation(
            "B13 refuses to delete a 2022 answer-present key based on outcome magnitude."
        )

    expected = int(status["n_officially_observable"].astype(int).iloc[0])
    if len(available) != expected:
        raise B13ProtocolViolation(
            f"B13 reconstructed {len(available)} B12 available cases, expected {expected}."
        )
    available["absolute_error"] = np.abs(
        available["observed"].to_numpy(float)
        - available["predicted"].to_numpy(float)
    )
    provenance = {
        **provenance,
        "n_available_2022_cells": int(len(available)),
        "n_available_2022_environments": int(available["environment"].nunique()),
        "selection_rule": "SEALED_KEY_PRESENT_IN_OFFICIAL_ANSWER_KEY",
        "selection_uses_outcome_value": False,
    }
    return available, provenance


def construct_drift_policy(
    historical: pd.DataFrame,
    recent_2022: pd.DataFrame,
) -> pd.DataFrame:
    if historical.empty or recent_2022.empty:
        raise ValueError("B13 drift policy requires historical and 2022 residuals.")
    if "absolute_error" not in historical or "absolute_error" not in recent_2022:
        raise ValueError("B13 drift policy requires absolute_error.")
    if not np.isfinite(recent_2022["absolute_error"].to_numpy(float)).all():
        raise ValueError("B13 2022 residuals contain non-finite values.")

    rows: list[dict[str, object]] = []
    for state in (SUPPORT_WITHIN, SUPPORT_EDGE):
        baseline = b12._quantiles(historical, state)
        for level in NOMINAL_LEVELS:
            key = int(round(100 * level))
            baseline_width, baseline_source = baseline[key]
            recent_width = finite_sample_quantile(
                recent_2022["absolute_error"],
                level,
            )
            adaptive_width = max(float(baseline_width), float(recent_width))
            rows.append(
                {
                    "schema": POLICY_SCHEMA,
                    "target_year": TARGET_YEAR,
                    "support_group": state,
                    "nominal": float(level),
                    "baseline_method": BASELINE_METHOD,
                    "adaptive_method": ADAPTIVE_METHOD,
                    "baseline_half_width": float(baseline_width),
                    "baseline_source": str(baseline_source),
                    "recent_2022_global_half_width": float(recent_width),
                    "adaptive_half_width": float(adaptive_width),
                    "adaptive_rule": "MAX_BASELINE_AND_2022_GLOBAL_FINITE_SAMPLE_QUANTILE",
                    "adaptive_never_narrows": bool(
                        adaptive_width + 1e-12 >= float(baseline_width)
                    ),
                    "historical_calibration_year_min": int(
                        historical["test_year"].min()
                    )
                    if "test_year" in historical
                    else 2016,
                    "historical_calibration_year_max": int(
                        historical["test_year"].max()
                    )
                    if "test_year" in historical
                    else 2021,
                    "recent_update_year": 2022,
                    "recent_update_n_cells": int(len(recent_2022)),
                    "recent_update_n_environments": int(
                        recent_2022["environment"].nunique()
                    )
                    if "environment" in recent_2022
                    else np.nan,
                    "target_outcomes_accessed": False,
                    "predictive_model_refit": False,
                    "t2_branch_reopened": False,
                    "post_target_tuning_permitted": False,
                }
            )
    policy = pd.DataFrame(rows)
    if not policy["adaptive_never_narrows"].all():
        raise AssertionError("B13 recency envelope narrowed a B11 interval.")
    return policy


def _policy_lookup(
    policy: pd.DataFrame,
    support_state: str,
    nominal: float,
) -> pd.Series:
    hit = policy[
        policy["support_group"].astype(str).eq(str(support_state))
        & np.isclose(policy["nominal"].astype(float), float(nominal))
    ]
    if len(hit) != 1:
        raise ValueError(
            f"B13 drift policy is not unique for {support_state}, {nominal}."
        )
    return hit.iloc[0]


def attach_support_and_dual_intervals(
    predictions: pd.DataFrame,
    t1_matrix: pd.DataFrame,
    train_envs: set[str],
    policy: pd.DataFrame,
) -> pd.DataFrame:
    support, _ = support_geometry(
        t1_matrix,
        train_envs,
        set(predictions["environment"].astype(str)),
        gamma_multiplier=FROZEN_CONFIG.gamma_multiplier,
        retained_rank=FROZEN_CONFIG.e_rank,
        prefix="full",
    )
    if "full_nearest_distance" not in support and "full_nearest_z" in support:
        support = support.copy()
        support["full_nearest_distance"] = support["full_nearest_z"]
    support["support_group"] = support["full_nearest_percentile"].map(support_group)
    support["reliability_state"] = np.where(
        support["support_group"].eq(SUPPORT_EDGE),
        ABSTAIN,
        RETAIN,
    )
    keep = [
        "environment",
        "full_nearest_percentile",
        "full_max_training_kernel_similarity",
        "support_group",
        "reliability_state",
    ]
    if "full_nearest_distance" in support:
        keep.insert(1, "full_nearest_distance")
    out = predictions.merge(support[keep], on="environment", validate="many_to_one")

    for state in (SUPPORT_WITHIN, SUPPORT_EDGE):
        mask = out["support_group"].astype(str).eq(state)
        for level in NOMINAL_LEVELS:
            key = int(round(100 * level))
            row = _policy_lookup(policy, state, level)
            baseline = float(row["baseline_half_width"])
            adaptive = float(row["adaptive_half_width"])
            out.loc[mask, f"b11_half_width_{key}"] = baseline
            out.loc[mask, f"b11_lower_{key}"] = (
                out.loc[mask, "predicted"] - baseline
            )
            out.loc[mask, f"b11_upper_{key}"] = (
                out.loc[mask, "predicted"] + baseline
            )
            out.loc[mask, f"b13_half_width_{key}"] = adaptive
            out.loc[mask, f"b13_lower_{key}"] = (
                out.loc[mask, "predicted"] - adaptive
            )
            out.loc[mask, f"b13_upper_{key}"] = (
                out.loc[mask, "predicted"] + adaptive
            )

    out["test_year"] = TARGET_YEAR
    out["model"] = MODEL
    out["horizon"] = HORIZON
    out["evaluation_policy"] = EVALUATION_POLICY
    out["selection_uses_outcome_availability"] = True
    out["selection_uses_outcome_magnitude"] = False
    out["predictive_model_refit_for_b13"] = False
    out["t2_branch_reopened"] = False
    return out


def canonical_prediction_bytes(frame: pd.DataFrame) -> bytes:
    required = {
        "genotype",
        "environment",
        "predicted",
        "reliability_state",
        "b11_lower_90",
        "b11_upper_90",
        "b13_lower_90",
        "b13_upper_90",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"B13 seal frame missing columns: {sorted(missing)}")
    canonical = frame.sort_values(
        ["environment", "genotype"],
        kind="mergesort",
    ).reset_index(drop=True)
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
    policy_path: Path,
    metadata: dict[str, object],
) -> dict[str, object]:
    body = canonical_prediction_bytes(frame)
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    prediction_path.write_bytes(body)
    policy_sha = sha256_file(policy_path)
    seal = {
        "schema": SEAL_SCHEMA,
        "target_year": TARGET_YEAR,
        "prediction_file": prediction_path.name,
        "prediction_sha256": _sha256_bytes(body),
        "drift_policy_file": policy_path.name,
        "drift_policy_sha256": policy_sha,
        "n_predictions": int(len(frame)),
        "n_environments": int(frame["environment"].nunique()),
        "n_genotypes": int(frame["genotype"].nunique()),
        "target_outcomes_accessed": False,
        "historical_2022_outcomes_used_for_uncertainty_update": True,
        "predictive_model_refit_for_b13": False,
        "predictive_hyperparameters_changed": False,
        "support_threshold_retuned": False,
        "t2_branch_reopened": False,
        "post_target_tuning_permitted": False,
        "evaluation_policy_predeclared": EVALUATION_POLICY,
        "evaluation_selection_uses_outcome_availability": True,
        "evaluation_selection_uses_outcome_magnitude": False,
        "trait_aggregation_predeclared": AGGREGATION_POLICY,
        "minimum_evaluation_cells": MIN_EVALUATION_CELLS,
        "minimum_evaluation_environments": MIN_EVALUATION_ENVIRONMENTS,
        **metadata,
    }
    seal_path.write_text(
        json.dumps(seal, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return seal


def verify_prediction_seal(
    prediction_path: Path,
    seal_path: Path,
    policy_path: Path,
) -> dict[str, object]:
    seal = json.loads(Path(seal_path).read_text(encoding="utf-8"))
    if seal.get("schema") != SEAL_SCHEMA:
        raise B13ProtocolViolation("B13 prediction seal schema mismatch.")
    if sha256_file(prediction_path) != seal.get("prediction_sha256"):
        raise B13ProtocolViolation("B13 prediction artifact does not match SHA-256.")
    if sha256_file(policy_path) != seal.get("drift_policy_sha256"):
        raise B13ProtocolViolation("B13 drift policy does not match frozen SHA-256.")
    if bool(seal.get("target_outcomes_accessed", True)):
        raise B13ProtocolViolation("B13 Stage-A seal reports 2023 outcome access.")
    if bool(seal.get("predictive_model_refit_for_b13", True)):
        raise B13ProtocolViolation("B13 seal reports point-predictor refit.")
    if bool(seal.get("t2_branch_reopened", True)):
        raise B13ProtocolViolation("B13 seal reports T2 reopening.")
    return seal


def run_stage_a(root: Path) -> dict[str, Path]:
    results = root / "reports" / "results"
    raw = root / "data" / "raw" / "case_study_b13_2023_sealed"
    assert_target_blind([raw])

    b11 = pd.read_csv(results / "case_study_b11_branch_decision.csv")
    if not b11["branch_decision"].astype(str).eq(
        "ADMIT_FORWARD_INTERVALS_KEEP_SUPPORT_ABSTENTION_DIAGNOSTIC"
    ).all():
        raise B13ProtocolViolation("B13 requires the admitted B11 interval layer.")
    if b11["t2_branch_reopened"].astype(str).str.lower().eq("true").any():
        raise B13ProtocolViolation("B13 refuses a B11 state that reopened T2.")

    b12_status = pd.read_csv(results / "case_study_b12_2022_primary_status.csv")
    if not b12_status["primary_status"].astype(str).eq(
        "B12_PRIMARY_INCOMPLETE_OFFICIAL_OUTCOME_MATCH"
    ).all():
        raise B13ProtocolViolation("B13 requires the frozen B12 2022 status.")
    if b12_status["post_result_tuning_permitted"].astype(str).str.lower().eq("true").any():
        raise B13ProtocolViolation("B13 refuses post-result B12 tuning.")

    states = pd.read_csv(results / "case_study_b9_safe_environment_states.csv")
    historical_manifest = pd.read_csv(results / "case_study_b9_environment_manifest.csv")
    forward = pd.read_csv(results / "case_study_b9_forward_year_folds.csv")
    b12.audit_historical_t1_encoding(states, historical_manifest)

    metadata_path, metadata_provenance = acquire_target_metadata(root)
    assert_target_blind([raw])
    metadata = pd.read_csv(metadata_path, low_memory=False)
    planting_dates, planting_provenance = discover_2023_planting_dates()
    target_manifest_all = target_environment_manifest(metadata, planting_dates)
    target_states, environment_audit = build_2023_t1_states(target_manifest_all)
    supported_envs = set(target_states["environment"].astype(str))
    target_manifest = target_manifest_all[
        target_manifest_all["environment"].astype(str).isin(supported_envs)
    ].copy()

    t1_matrix = b12.build_combined_t1_matrix(
        states,
        historical_manifest,
        target_states,
        target_manifest,
    )

    pheno, geno, ecov = load_materialized(root)
    _, geno, _, cols = prepare_cells(pheno, geno, ecov)
    frozen_genotypes = set(geno[cols["geno_id"]].astype(str))
    roster = build_outcome_free_roster(frozen_genotypes, supported_envs)

    predictions, train_envs = b12._predict_supported(root, roster, t1_matrix)
    historical = b12.historical_calibration_table(
        root,
        states,
        historical_manifest,
        forward,
    )
    recent_2022, recent_provenance = historical_2022_residuals(root)
    policy = construct_drift_policy(historical, recent_2022)

    paths = {
        "predictions": results / "case_study_b13_2023_sealed_predictions.csv",
        "seal": results / "case_study_b13_2023_prediction_seal.json",
        "policy": results / "case_study_b13_2023_drift_policy.csv",
        "input_audit": results / "case_study_b13_2023_input_audit.csv",
        "environment_audit": results / "case_study_b13_2023_environment_input_audit.csv",
        "decision": results / "case_study_b13a_seal_decision.csv",
    }
    results.mkdir(parents=True, exist_ok=True)
    policy.to_csv(paths["policy"], index=False, float_format="%.12g")

    predictions = attach_support_and_dual_intervals(
        predictions,
        t1_matrix,
        train_envs,
        policy,
    )
    input_audit = pd.DataFrame(
        [
            {
                "source_doi": SOURCE_DOI,
                "field_season_doi": FIELD_SEASON_DOI,
                "target_year": TARGET_YEAR,
                "metadata_sha256": metadata_provenance["sha256"],
                "planting_date_source_sha256": planting_provenance["sha256"],
                "planting_date_source_url": planting_provenance["source_url"],
                "planting_date_source_phenotypic_data_accessed": False,
                "n_target_metadata_environments": int(
                    target_manifest_all["environment"].nunique()
                ),
                "n_supported_t1_environments": int(len(supported_envs)),
                "n_frozen_b5_genotypes": int(len(frozen_genotypes)),
                "n_outcome_free_roster_cells": int(len(roster)),
                "n_sealed_prediction_cells": int(len(predictions)),
                "n_historical_calibration_cells": int(len(historical)),
                "historical_calibration_year_min": int(historical["test_year"].min()),
                "historical_calibration_year_max": int(historical["test_year"].max()),
                "n_recent_2022_update_cells": int(len(recent_2022)),
                "n_recent_2022_update_environments": int(
                    recent_2022["environment"].nunique()
                ),
                "target_trait_file_accessed": False,
                "target_outcomes_accessed": False,
                "weather_after_30dap_requested": False,
                "roster_uses_target_outcomes": False,
                "predictive_model_refit_for_b13": False,
                "support_threshold_retuned": False,
                "t2_branch_reopened": False,
                "post_target_tuning_permitted": False,
                "evaluation_policy": EVALUATION_POLICY,
                "evaluation_selection_uses_outcome_availability": True,
                "evaluation_selection_uses_outcome_magnitude": False,
                "trait_aggregation_policy": AGGREGATION_POLICY,
            }
        ]
    )
    input_audit.to_csv(paths["input_audit"], index=False)
    environment_audit.to_csv(paths["environment_audit"], index=False)

    seal = write_prediction_seal(
        predictions,
        paths["predictions"],
        paths["seal"],
        paths["policy"],
        {
            "source_doi": SOURCE_DOI,
            "field_season_doi": FIELD_SEASON_DOI,
            "supported_predictor": MODEL,
            "evaluated_horizon": HORIZON,
            "baseline_interval_method": BASELINE_METHOD,
            "adaptive_interval_method": ADAPTIVE_METHOD,
            "historical_calibration_years": "2016-2021",
            "recent_uncertainty_update_year": 2022,
            "roster_policy": ROSTER_POLICY,
            "environment_support_rule": "B11_FROZEN_TRAINING_NN_ENVELOPE",
            "metadata_sha256": metadata_provenance["sha256"],
            "planting_date_source_sha256": planting_provenance["sha256"],
            "planting_date_source_url": planting_provenance["source_url"],
            "historical_2022_answer_sha256": recent_provenance["answer_sha256"],
        },
    )

    pd.DataFrame(
        [
            {
                "stage": "B13A",
                "decision": "SEALED_2023_DUAL_INTERVALS_READY_FOR_REVEAL",
                "prediction_sha256": seal["prediction_sha256"],
                "drift_policy_sha256": seal["drift_policy_sha256"],
                "n_predictions": seal["n_predictions"],
                "n_environments": seal["n_environments"],
                "n_genotypes": seal["n_genotypes"],
                "target_outcomes_accessed": False,
                "predictive_model_refit_for_b13": False,
                "support_threshold_retuned": False,
                "t2_branch_reopened": False,
                "post_target_tuning_permitted": False,
                "evaluation_policy_predeclared": EVALUATION_POLICY,
            }
        ]
    ).to_csv(paths["decision"], index=False)
    assert_target_blind([raw])
    return paths


def aggregate_target_outcomes(trait: pd.DataFrame) -> pd.DataFrame:
    env_col = _find_column(
        trait,
        ("Env", "Environment", "environment"),
        "trait environment",
        (("env",),),
    )
    genotype_col = _find_column(
        trait,
        ("Hybrid", "Genotype", "hybrid", "genotype"),
        "trait genotype",
        (("hybrid",), ("genotype",)),
    )
    yield_col = _find_column(
        trait,
        (
            "Yield_Mg_ha",
            "Yield",
            "yield",
            "grain_yield",
            "Grain_Yield",
            "Observed",
        ),
        "trait yield",
        (("yield",),),
    )
    target = trait.loc[_target_year_mask(trait, env_col)].copy()
    if target.empty:
        raise ValueError("B13 trait file contains no 2023 rows.")
    target["genotype"] = target[genotype_col].astype(str)
    target["environment"] = target[env_col].astype(str)
    target["_yield"] = pd.to_numeric(target[yield_col], errors="coerce")
    finite = target[np.isfinite(target["_yield"].to_numpy(float))].copy()
    if finite.empty:
        raise ValueError("B13 trait file has no finite 2023 yields.")
    aggregated = (
        finite.groupby(["genotype", "environment"], as_index=False)
        .agg(
            observed=("_yield", "mean"),
            n_finite_plot_yields=("_yield", "size"),
        )
        .sort_values(["environment", "genotype"], kind="mergesort")
        .reset_index(drop=True)
    )
    aggregated["aggregation_policy"] = AGGREGATION_POLICY
    return aggregated


def predeclared_evaluation_cohort(
    predictions: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> pd.DataFrame:
    if predictions.duplicated(["genotype", "environment"]).any():
        raise ValueError("B13 sealed predictions are not unique by exact key.")
    if outcomes.duplicated(["genotype", "environment"]).any():
        raise ValueError("B13 aggregated outcomes are not unique by exact key.")
    cohort = predictions.merge(
        outcomes,
        on=["genotype", "environment"],
        how="inner",
        validate="one_to_one",
    )
    cohort["evaluation_policy"] = EVALUATION_POLICY
    cohort["selection_uses_outcome_availability"] = True
    cohort["selection_uses_outcome_magnitude"] = False
    cohort["post_reveal_row_deletion_permitted"] = False
    return cohort


def _coverage_table(cohort: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    methods = (
        (BASELINE_METHOD, "b11"),
        (ADAPTIVE_METHOD, "b13"),
    )
    for method, prefix in methods:
        for level in NOMINAL_LEVELS:
            key = int(round(100 * level))
            covered_col = f"_{prefix}_covered_{key}"
            cohort[covered_col] = (
                (cohort["observed"] >= cohort[f"{prefix}_lower_{key}"])
                & (cohort["observed"] <= cohort[f"{prefix}_upper_{key}"])
            )
            low, high = _cluster_coverage_ci(cohort, covered_col)
            env_cov = cohort.groupby("environment")[covered_col].mean()
            width = (
                cohort[f"{prefix}_upper_{key}"]
                - cohort[f"{prefix}_lower_{key}"]
            )
            empirical = float(cohort[covered_col].mean())
            rows.append(
                {
                    "method": method,
                    "nominal": float(level),
                    "n": int(len(cohort)),
                    "n_environments": int(cohort["environment"].nunique()),
                    "empirical_coverage": empirical,
                    "environment_balanced_coverage": float(env_cov.mean()),
                    "environment_cluster_ci95_low": float(low),
                    "environment_cluster_ci95_high": float(high),
                    "mean_interval_width": float(width.mean()),
                    "absolute_coverage_gap": abs(empirical - float(level)),
                    "evaluation_policy": EVALUATION_POLICY,
                    "selection_uses_outcome_availability": True,
                    "selection_uses_outcome_magnitude": False,
                }
            )
    return pd.DataFrame(rows)


def interval_criterion(row: pd.Series, nominal: float = 0.90) -> bool:
    return bool(
        abs(float(row["empirical_coverage"]) - float(nominal)) <= 0.03
        and float(row["environment_cluster_ci95_low"])
        <= float(nominal)
        <= float(row["environment_cluster_ci95_high"])
    )


def b13_decision(
    coverage: pd.DataFrame,
    n_cells: int,
    n_environments: int,
) -> str:
    if int(n_cells) < MIN_EVALUATION_CELLS or int(n_environments) < MIN_EVALUATION_ENVIRONMENTS:
        return "B13_INSUFFICIENT_EXTERNAL_OVERLAP"

    baseline = coverage[
        coverage["method"].astype(str).eq(BASELINE_METHOD)
        & np.isclose(coverage["nominal"].astype(float), 0.90)
    ]
    adaptive = coverage[
        coverage["method"].astype(str).eq(ADAPTIVE_METHOD)
        & np.isclose(coverage["nominal"].astype(float), 0.90)
    ]
    if len(baseline) != 1 or len(adaptive) != 1:
        raise ValueError("B13 decision requires one 90% row per method.")
    baseline_pass = interval_criterion(baseline.iloc[0])
    adaptive_pass = interval_criterion(adaptive.iloc[0])
    if adaptive_pass and not baseline_pass:
        return "B13_DRIFT_ADAPTATION_RESTORES_90_CALIBRATION"
    if adaptive_pass and baseline_pass:
        return "B13_BOTH_INTERVAL_RULES_PASS_90_CALIBRATION"
    if baseline_pass and not adaptive_pass:
        return "B13_DRIFT_ADAPTATION_DEGRADES_90_CALIBRATION"
    return "B13_DRIFT_ADAPTATION_INSUFFICIENT"


def _by_environment(cohort: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for environment, part in cohort.groupby("environment", sort=True):
        row: dict[str, object] = {
            "environment": str(environment),
            "n": int(len(part)),
            **metrics(part["observed"], part["predicted"]),
            "evaluation_policy": EVALUATION_POLICY,
            "selection_uses_outcome_magnitude": False,
        }
        for method, prefix in ((BASELINE_METHOD, "b11"), (ADAPTIVE_METHOD, "b13")):
            covered = (
                (part["observed"] >= part[f"{prefix}_lower_90"])
                & (part["observed"] <= part[f"{prefix}_upper_90"])
            )
            row[f"{method.lower()}_coverage_90"] = float(covered.mean())
            row[f"{method.lower()}_mean_width_90"] = float(
                (
                    part[f"{prefix}_upper_90"]
                    - part[f"{prefix}_lower_90"]
                ).mean()
            )
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_reveal(
    prediction_path: Path,
    seal_path: Path,
    policy_path: Path,
    trait_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    seal = verify_prediction_seal(prediction_path, seal_path, policy_path)
    if _norm(Path(trait_path).name) != _norm(TARGET_TRAIT_BASENAME):
        raise ValueError("B13 reveal requires the predeclared 2014-2023 trait basename.")

    predictions = pd.read_csv(prediction_path, low_memory=False)
    predictions["genotype"] = predictions["genotype"].astype(str)
    predictions["environment"] = predictions["environment"].astype(str)

    trait = pd.read_csv(trait_path, low_memory=False)
    outcomes = aggregate_target_outcomes(trait)
    cohort = predeclared_evaluation_cohort(predictions, outcomes)
    if cohort.empty:
        raise ValueError("B13 has zero overlap between the sealed roster and 2023 finite-yield keys.")

    coverage = _coverage_table(cohort)
    decision = b13_decision(
        coverage,
        len(cohort),
        cohort["environment"].nunique(),
    )
    point = metrics(cohort["observed"], cohort["predicted"])
    baseline90 = coverage[
        coverage["method"].eq(BASELINE_METHOD)
        & np.isclose(coverage["nominal"], 0.90)
    ].iloc[0]
    adaptive90 = coverage[
        coverage["method"].eq(ADAPTIVE_METHOD)
        & np.isclose(coverage["nominal"], 0.90)
    ].iloc[0]

    summary = pd.DataFrame(
        [
            {
                "target_year": TARGET_YEAR,
                "source_doi": SOURCE_DOI,
                "field_season_doi": FIELD_SEASON_DOI,
                "prediction_sha256": seal["prediction_sha256"],
                "drift_policy_sha256": seal["drift_policy_sha256"],
                "target_trait_sha256": sha256_file(trait_path),
                "n_sealed_predictions": int(len(predictions)),
                "n_evaluated_exact_keys": int(len(cohort)),
                "n_evaluated_environments": int(cohort["environment"].nunique()),
                "n_evaluated_genotypes": int(cohort["genotype"].nunique()),
                **point,
                "baseline_90_coverage": float(baseline90["empirical_coverage"]),
                "baseline_90_env_ci_low": float(
                    baseline90["environment_cluster_ci95_low"]
                ),
                "baseline_90_env_ci_high": float(
                    baseline90["environment_cluster_ci95_high"]
                ),
                "baseline_90_mean_width": float(baseline90["mean_interval_width"]),
                "baseline_90_criterion_met": interval_criterion(baseline90),
                "adaptive_90_coverage": float(adaptive90["empirical_coverage"]),
                "adaptive_90_env_ci_low": float(
                    adaptive90["environment_cluster_ci95_low"]
                ),
                "adaptive_90_env_ci_high": float(
                    adaptive90["environment_cluster_ci95_high"]
                ),
                "adaptive_90_mean_width": float(adaptive90["mean_interval_width"]),
                "adaptive_90_criterion_met": interval_criterion(adaptive90),
                "evaluation_policy": EVALUATION_POLICY,
                "evaluation_selection_uses_outcome_availability": True,
                "evaluation_selection_uses_outcome_magnitude": False,
                "trait_aggregation_policy": AGGREGATION_POLICY,
                "predictive_model_refit_for_b13": False,
                "interval_retuned_after_2023_reveal": False,
                "support_threshold_retuned_after_2023_reveal": False,
                "t2_branch_reopened": False,
                "post_target_tuning_permitted": False,
                "decision": decision,
            }
        ]
    )
    by_environment = _by_environment(cohort)
    cohort_audit = cohort[
        [
            "genotype",
            "environment",
            "n_finite_plot_yields",
            "aggregation_policy",
            "evaluation_policy",
            "selection_uses_outcome_availability",
            "selection_uses_outcome_magnitude",
            "post_reveal_row_deletion_permitted",
            "reliability_state",
            "support_group",
        ]
    ].copy()
    return summary, coverage, by_environment, cohort_audit


def run_stage_b(root: Path, trait_file: Path | None = None) -> dict[str, Path]:
    results = root / "reports" / "results"
    prediction_path = results / "case_study_b13_2023_sealed_predictions.csv"
    seal_path = results / "case_study_b13_2023_prediction_seal.json"
    policy_path = results / "case_study_b13_2023_drift_policy.csv"

    seal = verify_prediction_seal(prediction_path, seal_path, policy_path)
    if bool(seal.get("target_outcomes_accessed", True)):
        raise B13ProtocolViolation("B13 refuses a seal that reports target outcome access.")

    if trait_file is None:
        trait_path, provenance = acquire_target_trait(root)
    else:
        trait_path = Path(trait_file)
        provenance = {
            "source_url": "user_or_prepositioned_official_file",
            "sha256": sha256_file(trait_path),
            "size_bytes": int(trait_path.stat().st_size),
            "source_doi": SOURCE_DOI,
            "field_season_doi": FIELD_SEASON_DOI,
        }

    summary, coverage, by_environment, cohort = evaluate_reveal(
        prediction_path,
        seal_path,
        policy_path,
        trait_path,
    )
    paths = {
        "summary": results / "case_study_b13_2023_external_summary.csv",
        "coverage": results / "case_study_b13_2023_external_coverage.csv",
        "by_environment": results / "case_study_b13_2023_by_environment.csv",
        "cohort_audit": results / "case_study_b13_2023_cohort_audit.csv",
        "provenance": results / "case_study_b13_2023_reveal_provenance.json",
    }
    summary.to_csv(paths["summary"], index=False)
    coverage.to_csv(paths["coverage"], index=False)
    by_environment.to_csv(paths["by_environment"], index=False)
    cohort.to_csv(paths["cohort_audit"], index=False)
    paths["provenance"].write_text(
        json.dumps(
            {
                **provenance,
                "prediction_sha256_verified_before_target_outcome_access": seal[
                    "prediction_sha256"
                ],
                "drift_policy_sha256_verified_before_target_outcome_access": seal[
                    "drift_policy_sha256"
                ],
                "target_year": TARGET_YEAR,
                "evaluation_policy": EVALUATION_POLICY,
                "selection_uses_outcome_magnitude": False,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Case Study B13 sequential calibration-drift adaptation."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--stage", choices=("seal", "reveal"), required=True)
    parser.add_argument("--trait-file", type=Path)
    args = parser.parse_args()
    root = args.output_root.resolve()

    if args.stage == "seal":
        paths = run_stage_a(root)
        print("Case Study B13A sealed 2023 dual-interval prediction complete")
    else:
        paths = run_stage_b(root, args.trait_file)
        print("Case Study B13B sealed 2023 reveal evaluation complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
