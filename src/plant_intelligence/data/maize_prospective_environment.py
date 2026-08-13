"""Case Study B9: prospective environmental-state reconstruction data lock.

B9 converts the retrospective continuous-environment extension into a strict
forecast-time input problem. It does not fit a new predictor. It acquires and
audits public weather, soil, and management information; constructs three
issuance-time-safe environmental states; and freezes a forward-year validation
manifest before any B9 model is fitted.

The controlling rules are:

* no observed yield, anthesis, silking, harvest date, or future realized weather
  may enter a forecast state;
* T0 uses prior-year weather history only;
* T1 uses current-year weather only through 30 days after planting;
* T2 uses current-year weather only through 60 days after planting and is a
  fixed calendar-time reproductive-window proxy, not observed phenology;
* the existing B5 environment and genotype folds remain unchanged;
* forward-year evaluation trains strictly on years earlier than the test year.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from plant_intelligence.data.maize_environment_transfer import (
    acquire_source,
    load_source,
)

SEED = 20260813
MAIZE_HUB_COMMIT = "0385ac0f705eec9f4df41873467ed388e878bd1f"
HISTORICAL_ECOV_URL = (
    "https://raw.githubusercontent.com/QuantGen/MAIZE-HUB/"
    f"{MAIZE_HUB_COMMIT}/historical_ecov.zip"
)
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_PARAMETERS = (
    "T2M",
    "T2M_MIN",
    "T2M_MAX",
    "PRECTOTCORR",
    "ALLSKY_SFC_SW_DWN",
    "RH2M",
    "WS2M",
)
SSURGO_URL = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
WEATHER_HISTORY_START_YEAR = 2000
WEATHER_HISTORY_YEARS = 10


@dataclass(frozen=True)
class Horizon:
    name: str
    offset_days: int
    uses_current_year_weather: bool
    state: str
    description: str


HORIZONS = (
    Horizon(
        "T0_preseason",
        0,
        False,
        "PROSPECTIVE_INPUT_LOCK",
        "Prior-year weather climatology + static soil + planting/management metadata; no current-year realized weather.",
    ),
    Horizon(
        "T1_30DAP",
        30,
        True,
        "PROSPECTIVE_OBSERVED_TO_DATE",
        "Observed current-year weather from planting through 30 days after planting; no later weather.",
    ),
    Horizon(
        "T2_60DAP_reproductive_window_proxy",
        60,
        True,
        "PROSPECTIVE_OBSERVED_TO_DATE",
        "Observed current-year weather from planting through 60 days after planting; fixed-time proxy, not observed flowering/silking.",
    ),
)

FORBIDDEN_PHENOTYPE_TOKENS = (
    "yield",
    "anthesis",
    "silk",
    "flower",
    "harvest",
    "asi",
)


def _normalized(name: object) -> str:
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())


def resolve_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    exact = {str(c): str(c) for c in frame.columns}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
    normalized = {_normalized(c): str(c) for c in frame.columns}
    for candidate in candidates:
        hit = normalized.get(_normalized(candidate))
        if hit is not None:
            return hit
    return None


def _download_bytes(url: str, timeout: int = 180) -> tuple[bytes, str]:
    headers = {"User-Agent": "plant-intelligence-lab/0.1 reproducible-research"}
    last: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.get(url, headers=headers, timeout=(30, timeout))
            response.raise_for_status()
            body = response.content
            return body, hashlib.sha256(body).hexdigest()
        except Exception as exc:  # network retries are part of reproducible acquisition robustness
            last = exc
            if attempt == 3:
                break
            time.sleep(2**attempt)
    raise RuntimeError(f"Failed to download {url}: {last}")


def acquire_historical_metadata(root: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    raw = root / "data" / "raw" / "case_study_b9_prospective_environment"
    raw.mkdir(parents=True, exist_ok=True)
    body, sha256 = _download_bytes(HISTORICAL_ECOV_URL)
    archive = raw / "historical_ecov.zip"
    archive.write_bytes(body)
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        names = zf.namelist()
        matches = [n for n in names if Path(n).name == "ECOV_info.csv"]
        if len(matches) != 1:
            raise FileNotFoundError(f"Expected one ECOV_info.csv in historical_ecov.zip; matches={matches}")
        info = pd.read_csv(zf.open(matches[0]), low_memory=False)
    provenance = {
        "source": "QuantGen/MAIZE-HUB historical environmental metadata",
        "repository_commit": MAIZE_HUB_COMMIT,
        "archive_url": HISTORICAL_ECOV_URL,
        "sha256": sha256,
        "n_rows": int(len(info)),
        "n_columns": int(info.shape[1]),
    }
    (raw / "historical_ecov_provenance.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )
    return info, provenance


def _median_datetime(series: pd.Series) -> pd.Timestamp | pd.NaT:
    values = pd.to_datetime(series, errors="coerce").dropna().sort_values()
    if values.empty:
        return pd.NaT
    return values.iloc[len(values) // 2]


def _environment_metadata(pheno: pd.DataFrame, hist_info: pd.DataFrame) -> pd.DataFrame:
    env_col = resolve_column(pheno, ("year_loc", "environment", "Environment", "Env"))
    year_col = resolve_column(pheno, ("year", "Year"))
    city_col = resolve_column(pheno, ("city", "City", "location", "Location"))
    plant_col = resolve_column(pheno, ("date_plant", "planting_date", "dateplant", "sowing_date"))
    if None in (env_col, year_col, city_col, plant_col):
        raise ValueError(
            "B9 requires year_loc/year/city/date_plant in PHENO.csv; "
            f"resolved env={env_col}, year={year_col}, city={city_col}, plant={plant_col}."
        )

    lat_pheno = resolve_column(pheno, ("latitude", "lat", "gps_lat", "site_latitude"))
    lon_pheno = resolve_column(pheno, ("longitude", "lon", "lng", "long", "gps_lon", "site_longitude"))
    pop_col = resolve_column(
        pheno,
        (
            "plant_population",
            "plant_pop",
            "plant_density",
            "population",
            "plants_per_m2",
            "plants_m2",
        ),
    )

    info_year_city = resolve_column(hist_info, ("year_city", "yearcity"))
    info_plant = resolve_column(hist_info, ("date_plant_opt", "date_plant", "planting_date"))
    info_lat = resolve_column(hist_info, ("latitude", "lat", "gps_lat", "site_latitude"))
    info_lon = resolve_column(hist_info, ("longitude", "lon", "lng", "long", "gps_lon", "site_longitude"))

    rows: list[dict[str, object]] = []
    for environment, part in pheno.groupby(env_col, sort=True):
        year_values = pd.to_numeric(part[year_col], errors="coerce").dropna()
        if year_values.empty:
            year_match = pd.Series(str(environment)).str.extract(r"((?:19|20)\d{2})", expand=False).iloc[0]
            year = int(year_match) if pd.notna(year_match) else -1
        else:
            year = int(round(float(year_values.median())))
        city = str(part[city_col].dropna().astype(str).mode().iloc[0]) if part[city_col].notna().any() else "unknown"
        planting = _median_datetime(part[plant_col])

        latitude = float("nan")
        longitude = float("nan")
        coordinate_source = "unresolved"
        if lat_pheno and lon_pheno:
            lat_values = pd.to_numeric(part[lat_pheno], errors="coerce").dropna()
            lon_values = pd.to_numeric(part[lon_pheno], errors="coerce").dropna()
            if not lat_values.empty and not lon_values.empty:
                latitude = float(lat_values.median())
                longitude = float(lon_values.median())
                coordinate_source = "PHENO"

        historical_match = ""
        if info_year_city:
            base = f"{year}-{city}"
            candidates = hist_info[
                hist_info[info_year_city].astype(str).str.startswith(base, na=False)
            ].copy()
            if not candidates.empty and info_plant and pd.notna(planting):
                candidate_dates = pd.to_datetime(candidates[info_plant], errors="coerce")
                delta = (candidate_dates - planting).abs()
                if delta.notna().any():
                    candidates = candidates.loc[[delta.idxmin()]]
            if not candidates.empty:
                chosen = candidates.iloc[0]
                historical_match = str(chosen[info_year_city])
                if coordinate_source == "unresolved" and info_lat and info_lon:
                    lat = pd.to_numeric(pd.Series([chosen[info_lat]]), errors="coerce").iloc[0]
                    lon = pd.to_numeric(pd.Series([chosen[info_lon]]), errors="coerce").iloc[0]
                    if pd.notna(lat) and pd.notna(lon):
                        latitude = float(lat)
                        longitude = float(lon)
                        coordinate_source = "MAIZE-HUB_ECOV_info"

        population = float("nan")
        if pop_col:
            values = pd.to_numeric(part[pop_col], errors="coerce").dropna()
            if not values.empty:
                population = float(values.median())

        rows.append(
            {
                "environment": str(environment),
                "year": year,
                "city": city,
                "planting_date": planting.date().isoformat() if pd.notna(planting) else "",
                "latitude": latitude,
                "longitude": longitude,
                "coordinate_source": coordinate_source,
                "historical_year_city_match": historical_match,
                "plant_population_proxy": population,
                "n_plot_records": int(len(part)),
            }
        )

    frame = pd.DataFrame(rows)
    if frame["planting_date"].eq("").any():
        missing = frame.loc[frame["planting_date"].eq(""), "environment"].tolist()
        raise ValueError(f"Planting date unresolved for environments: {missing[:5]}")
    if frame[["latitude", "longitude"]].isna().any(axis=1).any():
        missing = frame.loc[frame[["latitude", "longitude"]].isna().any(axis=1), "environment"].tolist()
        raise ValueError(f"Coordinates unresolved for environments: {missing[:8]}")
    return frame


def _request_power(latitude: float, longitude: float, start_year: int, end_year: int) -> pd.DataFrame:
    params = {
        "parameters": ",".join(POWER_PARAMETERS),
        "community": "AG",
        "longitude": f"{longitude:.5f}",
        "latitude": f"{latitude:.5f}",
        "start": f"{start_year}0101",
        "end": f"{end_year}1231",
        "format": "JSON",
        "time-standard": "LST",
    }
    headers = {"User-Agent": "plant-intelligence-lab/0.1 reproducible-research"}
    last: Exception | None = None
    for attempt in range(5):
        try:
            response = requests.get(POWER_URL, params=params, headers=headers, timeout=(30, 240))
            response.raise_for_status()
            payload = response.json()
            parameters = payload["properties"]["parameter"]
            dates = sorted({d for values in parameters.values() for d in values})
            frame = pd.DataFrame(index=pd.to_datetime(dates, format="%Y%m%d"))
            for parameter in POWER_PARAMETERS:
                values = parameters.get(parameter, {})
                frame[parameter] = pd.to_numeric(
                    pd.Series({pd.to_datetime(k, format="%Y%m%d"): v for k, v in values.items()}),
                    errors="coerce",
                ).reindex(frame.index)
            frame = frame.replace({-999.0: np.nan, -999: np.nan})
            return frame.sort_index()
        except Exception as exc:
            last = exc
            if attempt == 4:
                break
            time.sleep(2**attempt)
    raise RuntimeError(
        f"NASA POWER request failed for lat={latitude}, lon={longitude}, {start_year}-{end_year}: {last}"
    )


def _coord_key(latitude: float, longitude: float) -> str:
    return f"{latitude:.4f}_{longitude:.4f}"


def acquire_power_weather(root: Path, environments: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    raw = root / "data" / "raw" / "case_study_b9_prospective_environment" / "power"
    raw.mkdir(parents=True, exist_ok=True)
    first_year = min(WEATHER_HISTORY_START_YEAR, int(environments["year"].min()))
    last_year = int(environments["year"].max())
    cache: dict[str, pd.DataFrame] = {}
    audit_rows: list[dict[str, object]] = []

    unique = environments[["latitude", "longitude"]].drop_duplicates().sort_values(["latitude", "longitude"])
    for row in unique.itertuples(index=False):
        lat = float(row.latitude)
        lon = float(row.longitude)
        key = _coord_key(lat, lon)
        frame = _request_power(lat, lon, first_year, last_year)
        cache[key] = frame
        csv_path = raw / f"power_{key}.csv.gz"
        frame.to_csv(csv_path, compression="gzip")
        audit_rows.append(
            {
                "coordinate_key": key,
                "latitude": lat,
                "longitude": lon,
                "first_date": frame.index.min().date().isoformat(),
                "last_date": frame.index.max().date().isoformat(),
                "n_days": int(len(frame)),
                "missing_fraction": float(frame.isna().mean().mean()),
                "parameters": "|".join(POWER_PARAMETERS),
                "source": "NASA POWER Daily API",
                "time_standard": "LST",
            }
        )
    return cache, pd.DataFrame(audit_rows)


def _parse_sda_table(payload: object) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    table = payload.get("Table")
    if not isinstance(table, list) or len(table) < 2:
        return None
    header = [str(v) for v in table[0]]
    row = table[1]
    return {header[i]: row[i] if i < len(row) else None for i in range(len(header))}


def query_ssurgo_point(latitude: float, longitude: float) -> dict[str, object]:
    point = f"point ({longitude:.6f} {latitude:.6f})"
    sql = f"""
    SELECT TOP 1
      mu.mukey,
      mu.musym,
      mu.muname,
      co.cokey,
      co.compname,
      co.comppct_r,
      co.taxorder,
      co.taxsuborder,
      co.taxgrtgroup,
      co.taxsubgrp
    FROM mapunit AS mu
    LEFT JOIN component AS co ON co.mukey = mu.mukey
    WHERE mu.mukey IN (
      SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{point}')
    )
    ORDER BY co.comppct_r DESC
    """
    body = {"query": sql, "format": "JSON+COLUMNNAME"}
    headers = {
        "User-Agent": "plant-intelligence-lab/0.1 reproducible-research",
        "Content-Type": "application/json",
    }
    last: Exception | None = None
    for attempt in range(4):
        try:
            response = requests.post(SSURGO_URL, json=body, headers=headers, timeout=(30, 120))
            response.raise_for_status()
            row = _parse_sda_table(response.json())
            if row is None:
                return {"ssurgo_available": False}
            return {"ssurgo_available": True, **row}
        except Exception as exc:
            last = exc
            if attempt == 3:
                break
            time.sleep(2**attempt)
    return {"ssurgo_available": False, "ssurgo_error": str(last)}


def acquire_ssurgo(environments: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    unique = environments[["latitude", "longitude", "city"]].drop_duplicates().sort_values(["city", "latitude", "longitude"])
    for row in unique.itertuples(index=False):
        result = query_ssurgo_point(float(row.latitude), float(row.longitude))
        rows.append(
            {
                "city": str(row.city),
                "coordinate_key": _coord_key(float(row.latitude), float(row.longitude)),
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "source": "USDA-NRCS Soil Data Access / SSURGO",
                **result,
            }
        )
    return pd.DataFrame(rows)


def _safe_anchor(year: int, month: int, day: int) -> pd.Timestamp:
    try:
        return pd.Timestamp(date(year, month, day))
    except ValueError:
        return pd.Timestamp(date(year, month, 28))


def aggregate_weather(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return {f"wx_{p.lower()}": float("nan") for p in POWER_PARAMETERS} | {"wx_n_days": 0}
    out = {
        "wx_t2m": float(frame["T2M"].mean()),
        "wx_t2m_min": float(frame["T2M_MIN"].min()),
        "wx_t2m_max": float(frame["T2M_MAX"].max()),
        "wx_prectotcorr": float(frame["PRECTOTCORR"].sum(min_count=1)),
        "wx_allsky_sfc_sw_dwn": float(frame["ALLSKY_SFC_SW_DWN"].sum(min_count=1)),
        "wx_rh2m": float(frame["RH2M"].mean()),
        "wx_ws2m": float(frame["WS2M"].mean()),
        "wx_n_days": int(len(frame)),
    }
    return out


def historical_climatology(frame: pd.DataFrame, planting: pd.Timestamp, current_year: int) -> tuple[dict[str, float], int]:
    start_year = max(WEATHER_HISTORY_START_YEAR, current_year - WEATHER_HISTORY_YEARS)
    pieces: list[pd.DataFrame] = []
    years_used = 0
    for year in range(start_year, current_year):
        anchor = _safe_anchor(year, planting.month, planting.day)
        window = frame.loc[(frame.index >= anchor) & (frame.index <= anchor + pd.Timedelta(days=60))]
        if not window.empty:
            pieces.append(window)
            years_used += 1
    combined = pd.concat(pieces) if pieces else frame.iloc[0:0]
    return aggregate_weather(combined), years_used


def build_safe_states(
    environments: pd.DataFrame,
    weather: dict[str, pd.DataFrame],
    soil: pd.DataFrame,
) -> pd.DataFrame:
    soil_by_key = soil.set_index("coordinate_key", drop=False).to_dict("index") if not soil.empty else {}
    rows: list[dict[str, object]] = []
    for env in environments.itertuples(index=False):
        planting = pd.Timestamp(env.planting_date)
        key = _coord_key(float(env.latitude), float(env.longitude))
        frame = weather[key]
        soil_row = soil_by_key.get(key, {})

        t0_weather, years_used = historical_climatology(frame, planting, int(env.year))
        rows.append(
            {
                "environment": env.environment,
                "year": int(env.year),
                "city": env.city,
                "horizon": "T0_preseason",
                "issuance_date": planting.date().isoformat(),
                "planting_date": planting.date().isoformat(),
                "uses_current_year_realized_weather": False,
                "max_current_year_weather_date_used": "",
                "uses_future_weather": False,
                "uses_observed_phenology": False,
                "historical_weather_years_used": years_used,
                "plant_population_proxy": env.plant_population_proxy,
                "ssurgo_available": bool(soil_row.get("ssurgo_available", False)),
                "ssurgo_mukey": soil_row.get("mukey", ""),
                "ssurgo_mapunit": soil_row.get("muname", ""),
                "ssurgo_component": soil_row.get("compname", ""),
                **t0_weather,
            }
        )

        for horizon in HORIZONS[1:]:
            issuance = planting + pd.Timedelta(days=horizon.offset_days)
            window = frame.loc[(frame.index >= planting) & (frame.index <= issuance)]
            max_used = window.index.max() if not window.empty else pd.NaT
            uses_future = bool(pd.notna(max_used) and max_used > issuance)
            rows.append(
                {
                    "environment": env.environment,
                    "year": int(env.year),
                    "city": env.city,
                    "horizon": horizon.name,
                    "issuance_date": issuance.date().isoformat(),
                    "planting_date": planting.date().isoformat(),
                    "uses_current_year_realized_weather": True,
                    "max_current_year_weather_date_used": max_used.date().isoformat() if pd.notna(max_used) else "",
                    "uses_future_weather": uses_future,
                    "uses_observed_phenology": False,
                    "historical_weather_years_used": 0,
                    "plant_population_proxy": env.plant_population_proxy,
                    "ssurgo_available": bool(soil_row.get("ssurgo_available", False)),
                    "ssurgo_mukey": soil_row.get("mukey", ""),
                    "ssurgo_mapunit": soil_row.get("muname", ""),
                    "ssurgo_component": soil_row.get("compname", ""),
                    **aggregate_weather(window),
                }
            )
    states = pd.DataFrame(rows)
    if states["uses_future_weather"].astype(bool).any():
        raise AssertionError("B9 state construction admitted future realized weather.")
    if states["uses_observed_phenology"].astype(bool).any():
        raise AssertionError("B9 state construction admitted observed phenology.")
    return states


def build_forward_year_manifest(environments: pd.DataFrame, min_prior_years: int = 2) -> pd.DataFrame:
    years = sorted(int(v) for v in environments["year"].unique())
    rows: list[dict[str, object]] = []
    for position, test_year in enumerate(years):
        train_years = years[:position]
        if len(train_years) < min_prior_years:
            continue
        test_envs = environments.loc[environments["year"] == test_year, "environment"].astype(str)
        for environment in sorted(test_envs):
            rows.append(
                {
                    "scenario": f"forward_year_{test_year}",
                    "test_year": test_year,
                    "environment": environment,
                    "train_year_min": min(train_years),
                    "train_year_max": max(train_years),
                    "n_training_years": len(train_years),
                    "admission": "FORWARD_YEAR_LOCKED",
                }
            )
    manifest = pd.DataFrame(rows)
    if manifest.empty:
        raise ValueError("No forward-year scenarios could be registered.")
    if not (manifest["train_year_max"] < manifest["test_year"]).all():
        raise AssertionError("Forward-year manifest contains temporal leakage.")
    return manifest


def horizon_audit() -> pd.DataFrame:
    rows = []
    for order, h in enumerate(HORIZONS):
        rows.append(
            {
                "horizon_order": order,
                "horizon": h.name,
                "offset_days_after_planting": h.offset_days,
                "uses_current_year_weather": h.uses_current_year_weather,
                "availability_state": h.state,
                "uses_future_realized_weather": False,
                "uses_observed_anthesis": False,
                "uses_observed_silking": False,
                "uses_observed_harvest": False,
                "uses_observed_yield": False,
                "description": h.description,
            }
        )
    return pd.DataFrame(rows)


def feature_provenance(pheno: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "feature_group": "weather",
            "source": "NASA POWER Daily API",
            "T0": "prior-year climatology only",
            "T1": "observed through 30 DAP",
            "T2": "observed through 60 DAP",
            "admission": "ALLOWED_WITH_ISSUANCE_CUTOFF",
        },
        {
            "feature_group": "soil",
            "source": "USDA-NRCS Soil Data Access / SSURGO",
            "T0": "static point soil map unit/component",
            "T1": "static",
            "T2": "static",
            "admission": "ALLOWED_STATIC",
        },
        {
            "feature_group": "management",
            "source": "G2F curated PHENO metadata",
            "T0": "planting date and plant-population proxy when available",
            "T1": "same locked management metadata",
            "T2": "same locked management metadata",
            "admission": "ALLOWED_IF_KNOWN_AT_ISSUANCE",
        },
    ]
    for column in pheno.columns:
        norm = _normalized(column)
        if any(token in norm for token in FORBIDDEN_PHENOTYPE_TOKENS):
            rows.append(
                {
                    "feature_group": f"forbidden:{column}",
                    "source": "G2F phenotype/outcome field",
                    "T0": "excluded",
                    "T1": "excluded",
                    "T2": "excluded",
                    "admission": "FORBIDDEN_OUTCOME_OR_FUTURE_PHENOLOGY",
                }
            )
    return pd.DataFrame(rows)


def source_audit(
    environments: pd.DataFrame,
    weather_audit: pd.DataFrame,
    soil: pd.DataFrame,
    states: pd.DataFrame,
    forward: pd.DataFrame,
    historical_provenance: dict[str, object],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "n_environments": int(len(environments)),
                "n_years": int(environments["year"].nunique()),
                "first_year": int(environments["year"].min()),
                "last_year": int(environments["year"].max()),
                "planting_date_coverage": float(environments["planting_date"].ne("").mean()),
                "coordinate_coverage": float(environments[["latitude", "longitude"]].notna().all(axis=1).mean()),
                "n_unique_weather_coordinates": int(len(weather_audit)),
                "power_weather_missing_fraction": float(weather_audit["missing_fraction"].mean()),
                "ssurgo_location_coverage": float(soil["ssurgo_available"].astype(bool).mean()) if not soil.empty else 0.0,
                "n_safe_state_rows": int(len(states)),
                "n_horizons": int(states["horizon"].nunique()),
                "future_weather_violations": int(states["uses_future_weather"].astype(bool).sum()),
                "observed_phenology_violations": int(states["uses_observed_phenology"].astype(bool).sum()),
                "n_forward_year_test_environments": int(len(forward)),
                "n_forward_year_scenarios": int(forward["scenario"].nunique()),
                "historical_metadata_commit": historical_provenance["repository_commit"],
                "historical_metadata_sha256": historical_provenance["sha256"],
                "prediction_performance_claim": "NONE_B9_IS_DATA_AND_VALIDATION_LOCK",
            }
        ]
    )


def make_coverage_figure(audit: pd.DataFrame, soil: pd.DataFrame, destination: Path) -> None:
    row = audit.iloc[0]
    labels = ["Planting date", "Coordinates", "NASA POWER", "SSURGO"]
    values = [
        100.0 * float(row["planting_date_coverage"]),
        100.0 * float(row["coordinate_coverage"]),
        100.0 if int(row["n_unique_weather_coordinates"]) > 0 else 0.0,
        100.0 * float(row["ssurgo_location_coverage"]),
    ]
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    bars = ax.bar(labels, values)
    ax.bar_label(bars, fmt="%.1f%%", padding=3)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Availability / coverage")
    ax.set_title("Case Study B9 — forecast-time input data lock")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(root: Path) -> dict[str, Path]:
    root = root.resolve()
    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    paths, _ = acquire_source(root)
    pheno, _, _ = load_source(paths)
    hist_info, historical_provenance = acquire_historical_metadata(root)
    environments = _environment_metadata(pheno, hist_info)
    weather, weather_audit = acquire_power_weather(root, environments)
    soil = acquire_ssurgo(environments)
    states = build_safe_states(environments, weather, soil)
    forward = build_forward_year_manifest(environments)
    horizons = horizon_audit()
    provenance = feature_provenance(pheno)
    audit = source_audit(environments, weather_audit, soil, states, forward, historical_provenance)

    # Preserve the already-locked B5 cold-start manifests as controlling external files.
    b5_env = results / "case_study_b5_environment_transfer_folds.csv"
    b5_geno = results / "case_study_b5_genotype_transfer_folds.csv"
    if not b5_env.exists() or not b5_geno.exists():
        raise FileNotFoundError("B9 requires the locked B5 environment and genotype manifests.")
    design = pd.DataFrame(
        [
            {
                "validation": "B5_CV-E",
                "state": "PRESERVED_UNCHANGED",
                "manifest": b5_env.name,
                "sha256": hashlib.sha256(b5_env.read_bytes()).hexdigest(),
            },
            {
                "validation": "B5_CV-GE",
                "state": "PRESERVED_UNCHANGED",
                "manifest": "B5 environment + genotype fold cross-product",
                "sha256": hashlib.sha256(b5_geno.read_bytes()).hexdigest(),
            },
            {
                "validation": "B9_FORWARD_YEAR",
                "state": "REGISTERED_BEFORE_MODELING",
                "manifest": "case_study_b9_forward_year_folds.csv",
                "sha256": "generated_below",
            },
        ]
    )

    outputs = {
        "source_audit": results / "case_study_b9_source_audit.csv",
        "environment_manifest": results / "case_study_b9_environment_manifest.csv",
        "weather_audit": results / "case_study_b9_power_weather_audit.csv",
        "soil_audit": results / "case_study_b9_ssurgo_audit.csv",
        "safe_states": results / "case_study_b9_safe_environment_states.csv",
        "horizons": results / "case_study_b9_horizon_lock.csv",
        "feature_provenance": results / "case_study_b9_feature_provenance.csv",
        "forward_year": results / "case_study_b9_forward_year_folds.csv",
        "validation_design": results / "case_study_b9_validation_lock.csv",
        "figure": figures / "case_study_b9_input_coverage.png",
    }
    audit.to_csv(outputs["source_audit"], index=False)
    environments.to_csv(outputs["environment_manifest"], index=False)
    weather_audit.to_csv(outputs["weather_audit"], index=False)
    soil.to_csv(outputs["soil_audit"], index=False)
    states.to_csv(outputs["safe_states"], index=False)
    horizons.to_csv(outputs["horizons"], index=False)
    provenance.to_csv(outputs["feature_provenance"], index=False)
    forward.to_csv(outputs["forward_year"], index=False)
    design.loc[design["validation"] == "B9_FORWARD_YEAR", "sha256"] = hashlib.sha256(
        outputs["forward_year"].read_bytes()
    ).hexdigest()
    design.to_csv(outputs["validation_design"], index=False)
    make_coverage_figure(audit, soil, outputs["figure"])
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Lock Case Study B9 prospective environmental inputs.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    outputs = run(args.output_root)
    print("Case Study B9 prospective environmental-state data lock complete")
    for key, path in outputs.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
