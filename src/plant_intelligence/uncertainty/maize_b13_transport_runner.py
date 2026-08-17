"""Hardened WebDAV transport wrapper for Case Study B13.

This module changes source transport only.  It preserves B13's safe-file
allow-list and target-outcome gate, follows CyVerse redirects manually so the
HTTP method and authentication policy remain explicit, validates the exact
expected schema before writing bytes, and then delegates to the frozen B13
Stage-A/Stage-B scientific implementation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin

import requests

from plant_intelligence.uncertainty import maize_b12_cyverse_source as b12_source
from plant_intelligence.uncertainty import maize_b13_sequential_drift_calibration as b13

_REDIRECTS = {301, 302, 303, 307, 308}


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

            needs_auth = "/dav/" in current and "/dav-anon/" not in current
            try:
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


def _install_transport() -> None:
    b13.download_competition_file = robust_download_competition_file


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
