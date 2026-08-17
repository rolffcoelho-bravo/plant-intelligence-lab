"""Resilient safe-source runner for B13A.

CyVerse occasionally returns transient non-CSV payloads from legacy public
WebDAV aliases. This runner changes only transport robustness. It preserves
B13A's strict allow-list and phenotype boundary, prefers CyVerse's documented
DOI-curated endpoint, retries only issuance-safe files, validates CSV schema
before accepting bytes, and then delegates to the 2023 split-schema adapter.
"""

from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

import requests

from plant_intelligence.uncertainty import maize_b13_2023_source_audit as b13a
from plant_intelligence.uncertainty import maize_b13a_2023_source_audit_runner as schema

DATASET = b13a.DATASET
SAFE_BASES = (
    f"https://data.cyverse.org/dav-anon/iplant/commons/cyverse_curated/{DATASET}",
    f"https://data.cyverse.org/dav/iplant/commons/cyverse_curated/{DATASET}",
    f"https://data.cyverse.org/dav-anon/iplant/projects/commons_repo/curated/{DATASET}",
    f"https://data.cyverse.org/dav/iplant/projects/commons_repo/curated/{DATASET}",
    f"https://data.cyverse.org/dav-anon/iplant/home/shared/commons_repo/curated/{DATASET}",
    f"https://data.cyverse.org/dav/iplant/home/shared/commons_repo/curated/{DATASET}",
)
MAX_ATTEMPTS_PER_URL = 3


def _html_like(response: requests.Response) -> bool:
    ctype = str(response.headers.get("content-type", "")).lower()
    head = response.content[:512].lstrip().lower()
    return "text/html" in ctype or head.startswith(b"<!doctype html") or head.startswith(b"<html")


def resilient_download_safe_file(
    relative_path: str,
    destination: Path,
    timeout: int = 180,
) -> tuple[str, str, int]:
    b13a.assert_safe_remote_path(relative_path)
    failures: list[str] = []

    for base in SAFE_BASES:
        url = f"{base.rstrip('/')}/{relative_path.lstrip('/')}"
        auth = ("anonymous", "") if "/dav/" in url and "/dav-anon/" not in url else None
        for attempt in range(1, MAX_ATTEMPTS_PER_URL + 1):
            try:
                response = requests.get(
                    url,
                    auth=auth,
                    headers={"User-Agent": b13a.USER_AGENT, "Accept": "text/csv,*/*;q=0.5"},
                    timeout=(30, timeout),
                    allow_redirects=True,
                )
                response.raise_for_status()
                body = response.content
                if not body:
                    raise RuntimeError("empty response")
                if _html_like(response):
                    raise RuntimeError("HTML-like response")
                if not b13a._schema_valid_csv(body):
                    raise RuntimeError("response is not a schema-valid CSV")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(body)
                return url, hashlib.sha256(body).hexdigest(), len(body)
            except Exception as exc:
                failures.append(
                    f"{url} attempt={attempt}: {type(exc).__name__}: {exc}"
                )
                if attempt < MAX_ATTEMPTS_PER_URL:
                    time.sleep(float(attempt))

    raise RuntimeError(
        "B13A could not acquire allow-listed 2023 source after resilient retries: "
        + " | ".join(failures[-36:])
    )


def run(root: Path):
    original = b13a.download_safe_file
    b13a.download_safe_file = resilient_download_safe_file
    try:
        return schema.run(root)
    finally:
        b13a.download_safe_file = original


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run B13A with resilient safe-only CyVerse acquisition."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    print("Case Study B13A resilient source audit complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
