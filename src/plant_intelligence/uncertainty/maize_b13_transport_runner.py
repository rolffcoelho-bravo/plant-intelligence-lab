"""Hardened WebDAV transport wrapper for Case Study B13.

This module changes source transport only. It preserves B13's safe-file
allow-list and target-outcome gate, follows CyVerse redirects manually so the
HTTP method and authentication policy remain explicit, traverses the 2023
supplemental directory with standards-compliant WebDAV ``Depth: 1`` requests,
and then delegates to the frozen B13 scientific implementation.
"""

from __future__ import annotations

import argparse
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests

from plant_intelligence.uncertainty import maize_b12_cyverse_source as b12_source
from plant_intelligence.uncertainty import maize_b13_sequential_drift_calibration as b13

_REDIRECTS = {301, 302, 303, 307, 308}
_PHENOTYPE_TOKEN = "a._2023_phenotypic_data"
_SUPPLEMENTAL_TOKEN = "z._2023_supplemental_info"


def _needs_auth(url: str) -> bool:
    return "/dav/" in str(url) and "/dav-anon/" not in str(url)


def _safe_redirect(url: str, location: str) -> str:
    target = urljoin(url, location)
    if _PHENOTYPE_TOKEN in target.lower():
        raise b13.B13ProtocolViolation(
            "B13 source transport refuses a redirect into 2023 phenotypic data."
        )
    return target


def robust_download_competition_file(
    basename: str,
    destination: Path,
    *,
    allow_target_outcome: bool,
    timeout: int = 180,
) -> tuple[Path, dict[str, object]]:
    """Download one B13 competition file through explicit safe redirects."""
    if basename == b13.TARGET_TRAIT_BASENAME and not allow_target_outcome:
        raise b13.B13ProtocolViolation(
            "B13 Stage A cannot acquire the 2014-2023 trait file containing "
            "2023 outcomes."
        )
    if basename not in {b13.METADATA_BASENAME, b13.TARGET_TRAIT_BASENAME}:
        raise ValueError(f"B13 transport refuses unknown file {basename!r}.")

    payload = b13._registry_payload()
    attempts: list[dict[str, object]] = []
    for initial_url, _ in b13._source_candidates(payload, basename):
        current = initial_url
        visited: set[str] = set()
        for _ in range(6):
            if current in visited:
                attempts.append({"url": current, "error": "redirect loop"})
                break
            visited.add(current)

            if basename == b13.TARGET_TRAIT_BASENAME and not allow_target_outcome:
                raise b13.B13ProtocolViolation(
                    "B13 target-trait gate changed during transport."
                )
            try:
                response = requests.get(
                    current,
                    auth=("anonymous", "") if _needs_auth(current) else None,
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
                    current = _safe_redirect(current, location)
                    continue

                response.raise_for_status()
                if not response.content:
                    break
                if b12_source._is_html_response(response):
                    break
                if not b13._schema_ok(basename, response.content):
                    attempts[-1]["schema_valid"] = False
                    break

                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(response.content)
                return destination, {
                    "source_url": str(current),
                    "sha256": b13._sha256_bytes(response.content),
                    "size_bytes": int(len(response.content)),
                    "source_doi": b13.SOURCE_DOI,
                    "field_season_doi": b13.FIELD_SEASON_DOI,
                    "redirects_preserved_explicitly": True,
                }
            except b13.B13ProtocolViolation:
                raise
            except Exception as exc:
                attempts.append(
                    {"url": current, "error": f"{type(exc).__name__}: {exc}"}
                )
                break

    raise RuntimeError(
        f"B13 could not acquire schema-valid {basename} through hardened "
        "WebDAV transport. Safe diagnostics: "
        + json.dumps(attempts[-40:], indent=2)
    )


def _propfind_depth_one(
    initial_url: str,
    timeout: int,
    diagnostics: list[dict[str, object]],
) -> tuple[str, bytes]:
    """Issue one standards-compliant WebDAV Depth:1 listing with redirects."""
    current = initial_url.rstrip("/") + "/"
    visited: set[str] = set()
    for _ in range(6):
        if current in visited:
            raise RuntimeError(f"B13 WebDAV PROPFIND redirect loop at {current}")
        visited.add(current)
        if _SUPPLEMENTAL_TOKEN not in current.lower():
            raise b13.B13ProtocolViolation(
                "B13 supplemental traversal escaped its allow-listed directory."
            )
        if _PHENOTYPE_TOKEN in current.lower():
            raise b13.B13ProtocolViolation(
                "B13 supplemental traversal entered phenotypic data."
            )

        response = requests.request(
            "PROPFIND",
            current,
            auth=("anonymous", "") if _needs_auth(current) else None,
            headers={"User-Agent": b13.USER_AGENT, "Depth": "1"},
            timeout=(30, timeout),
            allow_redirects=False,
        )
        diagnostics.append(
            {
                "method": "PROPFIND",
                "url": current,
                "status": int(response.status_code),
                "location": response.headers.get("location", ""),
                "content_type": response.headers.get("content-type", ""),
                "size": int(len(response.content)),
            }
        )
        if response.status_code in _REDIRECTS:
            location = response.headers.get("location")
            if not location:
                break
            current = _safe_redirect(current, location)
            continue
        if response.status_code != 207:
            raise RuntimeError(
                f"B13 supplemental Depth:1 PROPFIND failed at {current}: "
                f"HTTP {response.status_code}"
            )
        if b"<html" in response.content[:2000].lower():
            raise RuntimeError(
                "B13 supplemental PROPFIND returned HTML instead of WebDAV XML."
            )
        return current, response.content
    raise RuntimeError(f"B13 supplemental PROPFIND could not resolve {initial_url}")


def _webdav_hrefs(xml_body: bytes) -> list[str]:
    tree = ET.fromstring(xml_body)
    hrefs: list[str] = []
    for node in tree.iter():
        if node.tag.endswith("href") and node.text:
            href = str(node.text)
            low = href.lower()
            if _PHENOTYPE_TOKEN in low:
                raise b13.B13ProtocolViolation(
                    "B13 supplemental listing exposed a phenotypic-data path."
                )
            if href not in hrefs:
                hrefs.append(href)
    return hrefs


def _absolute_webdav_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        url = href
    else:
        url = "https://data.cyverse.org" + href
    return url.replace("/dav-anon/", "/dav/")


def robust_discover_2023_planting_dates(
    timeout: int = 180,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Find exact planting dates inside outcome-free 2023 supplemental data.

    WebDAV only standardizes Depth 0, 1 and infinity.  We deliberately recurse
    with individual Depth:1 requests, maintaining a hard path allow-list and a
    maximum depth of three directory levels.
    """
    root = b13.SUPPLEMENTAL_ROOT.rstrip("/") + "/"
    if _PHENOTYPE_TOKEN in root.lower() or _SUPPLEMENTAL_TOKEN not in root.lower():
        raise b13.B13ProtocolViolation("B13 supplemental root is not safely scoped.")

    listing_diagnostics: list[dict[str, object]] = []
    files: list[str] = []
    queue: list[tuple[str, int]] = [(root, 0)]
    seen_dirs: set[str] = set()

    while queue:
        directory, depth = queue.pop(0)
        if directory in seen_dirs:
            continue
        seen_dirs.add(directory)
        resolved, body = _propfind_depth_one(
            directory,
            timeout,
            listing_diagnostics,
        )
        for href in _webdav_hrefs(body):
            url = _absolute_webdav_url(href)
            low = url.lower()
            if _SUPPLEMENTAL_TOKEN not in low:
                continue
            if _PHENOTYPE_TOKEN in low:
                raise b13.B13ProtocolViolation(
                    "B13 recursive supplemental traversal crossed into phenotypic data."
                )
            if url.rstrip("/") == resolved.rstrip("/"):
                continue
            if url.endswith("/"):
                if depth < 3:
                    queue.append((url, depth + 1))
                continue
            if url not in files:
                files.append(url)

    probes: list[dict[str, object]] = []
    candidate_files = [
        url for url in files if url.lower().endswith((".csv", ".tsv", ".txt"))
    ]
    for initial_url in candidate_files:
        current = initial_url
        visited: set[str] = set()
        for _ in range(6):
            if current in visited:
                probes.append({"url": current, "error": "redirect loop"})
                break
            visited.add(current)
            if _SUPPLEMENTAL_TOKEN not in current.lower():
                raise b13.B13ProtocolViolation(
                    "B13 supplemental file request escaped its allow-list."
                )
            if _PHENOTYPE_TOKEN in current.lower():
                raise b13.B13ProtocolViolation(
                    "B13 supplemental file request entered phenotypic data."
                )
            try:
                response = requests.get(
                    current,
                    auth=("anonymous", "") if _needs_auth(current) else None,
                    headers={
                        "User-Agent": b13.USER_AGENT,
                        "Accept": "text/csv,text/plain,*/*;q=0.2",
                    },
                    timeout=(30, timeout),
                    allow_redirects=False,
                )
                probes.append(
                    {
                        "url": current,
                        "status": int(response.status_code),
                        "location": response.headers.get("location", ""),
                        "content_type": response.headers.get("content-type", ""),
                        "size": int(len(response.content)),
                    }
                )
                if response.status_code in _REDIRECTS:
                    location = response.headers.get("location")
                    if not location:
                        break
                    current = _safe_redirect(current, location)
                    continue
                response.raise_for_status()
                if not response.content or b"<html" in response.content[:2000].lower():
                    break

                low = current.lower()
                sep = "\t" if low.endswith(".tsv") else ","
                header = pd.read_csv(
                    io.BytesIO(response.content),
                    nrows=0,
                    sep=sep,
                    low_memory=False,
                )
                columns = list(map(str, header.columns))
                probes[-1]["columns"] = columns
                env_col = b13._optional_column(
                    header,
                    ("Env", "Environment", "environment"),
                    (("env",),),
                )
                plant_col = b13._optional_column(
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
                    break

                frame = pd.read_csv(
                    io.BytesIO(response.content),
                    sep=sep,
                    low_memory=False,
                )
                target = frame.loc[b13._target_year_mask(frame, env_col)].copy()
                if target.empty:
                    break
                target["environment"] = target[env_col].astype(str).str.strip()
                target["planting_date"] = pd.to_datetime(
                    target[plant_col], errors="coerce"
                )
                target = target.dropna(subset=["environment", "planting_date"])
                if target.empty:
                    break

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
                    break
                return planting, {
                    "source_url": str(current),
                    "sha256": b13._sha256_bytes(response.content),
                    "size_bytes": int(len(response.content)),
                    "source_doi": b13.FIELD_SEASON_DOI,
                    "source_scope": _SUPPLEMENTAL_TOKEN,
                    "phenotypic_data_accessed": False,
                    "webdav_listing_method": "recursive_depth_1",
                    "n_supplemental_files_discovered": int(len(files)),
                }
            except b13.B13ProtocolViolation:
                raise
            except Exception as exc:
                probes.append(
                    {"url": current, "error": f"{type(exc).__name__}: {exc}"}
                )
                break

    raise RuntimeError(
        "B13 found no exact environment-level planting-date CSV/TSV/TXT inside "
        "the outcome-free 2023 supplemental directory. Safe discovered files "
        "and schema diagnostics: "
        + json.dumps(
            {
                "files": files[-100:],
                "listings": listing_diagnostics[-50:],
                "probes": probes[-60:],
            },
            indent=2,
        )
    )


def _install_transport() -> None:
    b13.download_competition_file = robust_download_competition_file
    b13.discover_2023_planting_dates = robust_discover_2023_planting_dates


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run B13 with hardened CyVerse WebDAV transport."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--stage", choices=("seal", "reveal"), required=True)
    parser.add_argument("--trait-file", type=Path)
    args = parser.parse_args()
    root = args.output_root.resolve()

    _install_transport()
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
