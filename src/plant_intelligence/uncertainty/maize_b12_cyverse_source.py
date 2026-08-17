"""Current CyVerse registry resolver for the blind B12A input stage.

This module exists only to resolve the post-2026 CyVerse Data Commons migration.
It does not alter the B12 predictor, calibration, support rule, or reveal boundary.
Only the two allow-listed 2022 *input* CSV files are eligible here.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests

from plant_intelligence.uncertainty import maize_external_temporal_validation as b12

CKAN_PACKAGE_URL = (
    "https://dc.cyverse.org/api/3/action/package_show"
    "?id=genomes_to_fields_2022_maize_genotype_by_environment_prediction_competition"
)
TESTING_FOLDER_NAMES = ("Testing_data", "Testing_Data")
SAFE_BASENAMES = {
    "1_Submission_Template_2022.csv": {"hybrid", "env"},
    "2_Testing_Meta_Data_2022.csv": {"env"},
}
HTML_PREFIXES = (b"<!doctype html", b"<html", b"<?xml")
USER_AGENT = "plant-intelligence-lab/0.1 B12A blind-source-resolver"


class SourceResolutionError(RuntimeError):
    pass


def _norm(value: object) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def _all_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _all_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _all_strings(item)


def _is_html_response(response: requests.Response) -> bool:
    content_type = str(response.headers.get("content-type", "")).lower()
    if "text/html" in content_type or "application/xhtml" in content_type:
        return True
    prefix = response.content[:256].lstrip().lower()
    return any(prefix.startswith(marker) for marker in HTML_PREFIXES)


def _schema_ok(basename: str, body: bytes) -> bool:
    if basename not in SAFE_BASENAMES:
        return False
    try:
        frame = pd.read_csv(io.BytesIO(body), nrows=8)
    except Exception:
        return False
    normalized = {_norm(column) for column in frame.columns}
    required = {_norm(column) for column in SAFE_BASENAMES[basename]}
    if basename == "1_Submission_Template_2022.csv":
        genotype_ok = bool(
            normalized.intersection({_norm("Hybrid"), _norm("Genotype")})
        )
        env_ok = bool(
            normalized.intersection({_norm("Env"), _norm("Environment")})
        )
        return genotype_ok and env_ok
    env_ok = bool(normalized.intersection({_norm("Env"), _norm("Environment")}))
    coord_ok = bool(
        normalized.intersection(
            {
                _norm("Weather_Station_Latitude"),
                _norm("Latitude"),
                _norm("Lat"),
            }
        )
    ) and bool(
        normalized.intersection(
            {
                _norm("Weather_Station_Longitude"),
                _norm("Longitude"),
                _norm("Lon"),
                _norm("Long"),
            }
        )
    )
    return env_ok and coord_ok


def _clean_http_url(value: str) -> str | None:
    value = str(value).strip()
    if not value.lower().startswith(("http://", "https://")):
        return None
    parts = urlsplit(value)
    return urlunsplit(("https", parts.netloc, parts.path.rstrip("/"), parts.query, ""))


def _irods_path_from_string(value: str) -> str | None:
    text = str(value).strip()
    markers = ("/iplant/home/", "/iplant/commons/")
    for marker in markers:
        index = text.find(marker)
        if index >= 0:
            path = text[index:].split("?", 1)[0].split("#", 1)[0].rstrip("/")
            return path
    return None


def registry_payload(timeout: int = 60) -> dict[str, object]:
    response = requests.get(
        CKAN_PACKAGE_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=(20, timeout),
    )
    response.raise_for_status()
    payload = response.json()
    if not bool(payload.get("success")) or not isinstance(payload.get("result"), dict):
        raise SourceResolutionError("CyVerse CKAN package_show returned no dataset result.")
    return payload


def candidate_urls(payload: dict[str, object], basename: str) -> list[str]:
    if basename not in SAFE_BASENAMES:
        raise SourceResolutionError(f"B12A refuses non-allow-listed file {basename!r}.")

    result = payload.get("result", {})
    resources = result.get("resources", []) if isinstance(result, dict) else []
    candidates: list[str] = []

    def add(url: str) -> None:
        if url and url not in candidates:
            candidates.append(url)

    strings = list(_all_strings(resources)) + list(_all_strings(result))
    for value in strings:
        clean = _clean_http_url(value)
        irods = _irods_path_from_string(value)

        if irods:
            for folder in TESTING_FOLDER_NAMES:
                if irods.lower().endswith(folder.lower()):
                    add(f"https://data.cyverse.org/dav-anon{irods}/{basename}")
                elif folder.lower() in irods.lower():
                    prefix = irods[: irods.lower().find(folder.lower()) + len(folder)]
                    add(f"https://data.cyverse.org/dav-anon{prefix}/{basename}")
            if not any(folder.lower() in irods.lower() for folder in TESTING_FOLDER_NAMES):
                for folder in TESTING_FOLDER_NAMES:
                    add(f"https://data.cyverse.org/dav-anon{irods}/{folder}/{basename}")

        if clean:
            path_lower = urlsplit(clean).path.lower()
            for folder in TESTING_FOLDER_NAMES:
                token = "/" + folder.lower()
                if path_lower.endswith(token):
                    add(clean + "/" + basename)
                elif token + "/" in path_lower:
                    prefix_len = path_lower.find(token) + len(token)
                    parts = urlsplit(clean)
                    add(
                        urlunsplit(
                            (
                                "https",
                                parts.netloc,
                                parts.path[:prefix_len] + "/" + basename,
                                "",
                                "",
                            )
                        )
                    )

    # Historical curated path fallbacks are retained only as candidates. Every
    # response is MIME/signature/schema validated before it can be accepted.
    roots = (
        "/iplant/home/shared/commons_repo/curated/"
        "GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2023",
        "/iplant/commons/cyverse_curated/"
        "GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2023",
    )
    for root in roots:
        for folder in TESTING_FOLDER_NAMES:
            add(f"https://data.cyverse.org/dav-anon{root}/{folder}/{basename}")
    return candidates


def download_current_safe_file(
    relative_paths: Iterable[str], destination: Path, timeout: int = 180
) -> tuple[str, str, int]:
    relative_paths = tuple(relative_paths)
    if len(relative_paths) != 1:
        raise SourceResolutionError("B12A registry resolver requires one logical file at a time.")
    basename = Path(relative_paths[0]).name
    if basename not in SAFE_BASENAMES:
        raise b12.SealViolation(f"B12A refuses non-allow-listed basename {basename!r}.")
    if _norm(basename) == _norm(b12.FORBIDDEN_ANSWER_BASENAME):
        raise b12.SealViolation("B12A resolver cannot acquire the observed-answer file.")

    payload = registry_payload()
    candidates = candidate_urls(payload, basename)
    attempts: list[dict[str, object]] = []
    for url in candidates:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*;q=0.5"},
                timeout=(30, timeout),
                allow_redirects=True,
            )
            attempts.append(
                {
                    "url": url,
                    "final_url": response.url,
                    "status": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "size": len(response.content),
                    "html_like": _is_html_response(response),
                }
            )
            response.raise_for_status()
            if not response.content or _is_html_response(response):
                continue
            if not _schema_ok(basename, response.content):
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
            return response.url, b12._sha256_bytes(response.content), len(response.content)
        except Exception as exc:
            attempts.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    compact = json.dumps(attempts[-20:], indent=2)
    raise SourceResolutionError(
        f"Unable to resolve current CyVerse CSV {basename}. Candidate diagnostics:\n{compact}"
    )


def run_stage_a(root: Path) -> dict[str, Path]:
    # Monkey-patch only the transport function. All prediction/calibration logic
    # remains exactly in maize_external_temporal_validation.
    b12._download_first_available = download_current_safe_file
    return b12.run_stage_a(root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run B12A using the current CyVerse registry resolver."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.probe:
        payload = registry_payload()
        safe_summary = []
        result = payload.get("result", {})
        for resource in result.get("resources", []) if isinstance(result, dict) else []:
            if not isinstance(resource, dict):
                continue
            safe_summary.append(
                {
                    "name": resource.get("name"),
                    "format": resource.get("format"),
                    "url": resource.get("url"),
                    "resource_type": resource.get("resource_type"),
                }
            )
        print(json.dumps(safe_summary, indent=2))
        return
    paths = run_stage_a(args.output_root.resolve())
    print("Case Study B12A sealed prediction stage complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
