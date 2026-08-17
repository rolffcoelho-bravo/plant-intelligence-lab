"""Outcome-free season-boundary resolver for Case Study B13.

The official G2F 2024 competition documentation defines
``4_Training_Weather_Data_2014_2023_seasons_only.csv`` as the same NASA POWER
weather as the full-year file, restricted to the interval from 14 days before
planting through 14 days after harvest for each environment.  B13 therefore
recovers the 2023 planting date deterministically as:

    planting_date = first_seasons_only_date + 14 days

This module never reads the 2014-2023 trait file during Stage A.  It installs
that documented season-boundary resolver on top of the hardened B13 WebDAV
transport and delegates the scientific computation to the frozen B13 engine.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests

from plant_intelligence.uncertainty import maize_b12_cyverse_source as b12_source
from plant_intelligence.uncertainty import maize_b13_sequential_drift_calibration as b13
from plant_intelligence.uncertainty import maize_b13_transport_runner as transport

SEASONS_WEATHER_BASENAME = "4_Training_Weather_Data_2014_2023_seasons_only.csv"
SEASON_BOUNDARY_RULE = (
    "OFFICIAL_SEASONS_ONLY_START_PLUS_14_DAYS_EQUALS_PLANTING_DATE"
)
SEASON_DOCUMENTATION_RULE = (
    "SEASONS_ONLY_INCLUDES_14_DAYS_PRIOR_TO_PLANTING_THROUGH_"
    "14_DAYS_AFTER_HARVEST"
)
_REDIRECTS = {301, 302, 303, 307, 308}


def planting_dates_from_seasons_weather(weather: pd.DataFrame) -> pd.DataFrame:
    """Derive exact planting dates from the documented seasons-only boundary."""
    env_col = b13._find_column(
        weather,
        ("Env", "Environment", "environment"),
        "seasons-only environment",
        (("env",),),
    )
    date_col = b13._find_column(
        weather,
        ("Date", "date"),
        "seasons-only date",
        (("date",),),
    )

    frame = weather[[env_col, date_col]].copy()
    frame["environment"] = frame[env_col].astype(str).str.strip()
    # The competition README defines Date as YYYYMMDD.  Explicit format avoids
    # pandas treating integer dates as nanoseconds from the Unix epoch.
    raw_date = frame[date_col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    frame["_date"] = pd.to_datetime(raw_date, format="%Y%m%d", errors="coerce")
    frame = frame.dropna(subset=["environment", "_date"])
    frame = frame[
        frame["environment"].astype(str).str.contains(str(b13.TARGET_YEAR), regex=False)
    ].copy()
    if frame.empty:
        raise ValueError("B13 seasons-only weather contains no 2023 environments.")

    rows: list[dict[str, object]] = []
    for environment, part in frame.groupby("environment", sort=True):
        dates = pd.DatetimeIndex(part["_date"].dropna().drop_duplicates().sort_values())
        if len(dates) < 15:
            continue
        start = pd.Timestamp(dates.min()).normalize()
        expected_preplant = pd.date_range(start, start + pd.Timedelta(days=14), freq="D")
        observed = set(pd.Timestamp(value).normalize() for value in dates)
        if not set(expected_preplant).issubset(observed):
            # If the documented 14-day pre-plant window is not actually present
            # day-by-day, B13 refuses to manufacture the boundary.
            continue
        planting = start + pd.Timedelta(days=14)
        rows.append(
            {
                "environment": str(environment),
                "planting_date": planting.date().isoformat(),
                "seasons_only_start_date": start.date().isoformat(),
                "n_seasons_only_dates": int(len(dates)),
                "season_boundary_rule": SEASON_BOUNDARY_RULE,
                "target_outcomes_used": False,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError(
            "B13 could not recover any 2023 planting date from a complete "
            "documented 14-day pre-plant seasons-only window."
        )
    if result["environment"].duplicated().any():
        raise ValueError("B13 seasons-only planting dates are not unique by environment.")
    return result.sort_values("environment").reset_index(drop=True)


def _download_seasons_weather(timeout: int = 240) -> tuple[bytes, str]:
    payload = b13._registry_payload()
    attempts: list[dict[str, object]] = []
    for initial_url, _ in b13._source_candidates(payload, SEASONS_WEATHER_BASENAME):
        current = initial_url
        visited: set[str] = set()
        for _ in range(8):
            if current in visited:
                attempts.append({"url": current, "error": "redirect loop"})
                break
            visited.add(current)
            if b13.TARGET_TRAIT_BASENAME.lower() in current.lower():
                raise b13.B13ProtocolViolation(
                    "B13 seasons resolver crossed into the target trait file."
                )
            try:
                needs_auth = "/dav/" in current and "/dav-anon/" not in current
                response = requests.get(
                    current,
                    auth=("anonymous", "") if needs_auth else None,
                    headers={
                        "User-Agent": b13.USER_AGENT,
                        "Accept": "text/csv,*/*;q=0.5",
                    },
                    timeout=(30, timeout),
                    allow_redirects=False,
                )
                attempts.append(
                    {
                        "url": current,
                        "status": int(response.status_code),
                        "location": response.headers.get("location", ""),
                        "content_type": response.headers.get("content-type", ""),
                        "size": int(len(response.content)),
                        "html_like": b12_source._is_html_response(response),
                    }
                )
                if response.status_code in _REDIRECTS:
                    location = response.headers.get("location")
                    if not location:
                        break
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                if not response.content or b12_source._is_html_response(response):
                    break
                try:
                    header = pd.read_csv(io.BytesIO(response.content), nrows=0, low_memory=False)
                    b13._find_column(
                        header,
                        ("Env", "Environment", "environment"),
                        "seasons-only environment",
                        (("env",),),
                    )
                    b13._find_column(
                        header,
                        ("Date", "date"),
                        "seasons-only date",
                        (("date",),),
                    )
                except Exception:
                    attempts[-1]["schema_valid"] = False
                    break
                return response.content, str(current)
            except b13.B13ProtocolViolation:
                raise
            except Exception as exc:
                attempts.append(
                    {"url": current, "error": f"{type(exc).__name__}: {exc}"}
                )
                break
    raise RuntimeError(
        "B13 could not acquire the outcome-free seasons-only weather file. "
        + json.dumps(attempts[-40:], indent=2)
    )


def derive_2023_planting_dates_from_official_seasons(
    timeout: int = 240,
) -> tuple[pd.DataFrame, dict[str, object]]:
    body, source_url = _download_seasons_weather(timeout=timeout)
    weather = pd.read_csv(io.BytesIO(body), low_memory=False)
    planting = planting_dates_from_seasons_weather(weather)
    return planting, {
        "source_url": source_url,
        "sha256": b13._sha256_bytes(body),
        "size_bytes": int(len(body)),
        "source_doi": b13.SOURCE_DOI,
        "source_file": SEASONS_WEATHER_BASENAME,
        "source_scope": "Training_data outcome-free weather",
        "season_documentation_rule": SEASON_DOCUMENTATION_RULE,
        "season_boundary_rule": SEASON_BOUNDARY_RULE,
        "phenotypic_data_accessed": False,
        "target_trait_file_accessed": False,
        "target_outcomes_accessed": False,
    }


def _install() -> None:
    transport._install_transport()
    b13.discover_2023_planting_dates = derive_2023_planting_dates_from_official_seasons


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run B13 using the documented seasons-only planting boundary."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--stage", choices=("seal", "reveal"), required=True)
    parser.add_argument("--trait-file", type=Path)
    args = parser.parse_args()
    root = args.output_root.resolve()

    _install()
    if args.stage == "seal":
        paths = b13.run_stage_a(root)
        print("Case Study B13A sealed 2023 dual-interval prediction complete")
    else:
        paths = b13.run_stage_b(root, args.trait_file)
        print("Case Study B13B sealed 2023 reveal evaluation complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
