"""Run blind B12A through CyVerse's authenticated-anonymous WebDAV endpoint.

CyVerse documents `anonymous` with an empty password as a supported Data Store
credential. This runner changes only transport from the IP-gated `dav-anon`
endpoint to `dav`; prediction, calibration, support, and outcome-seal logic are
unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

import requests

from plant_intelligence.uncertainty import maize_b12_cyverse_source as source
from plant_intelligence.uncertainty import maize_b12_registry_runner as registry
from plant_intelligence.uncertainty import maize_external_temporal_validation as b12

USER_AGENT = "plant-intelligence-lab/0.1 B12A authenticated-anonymous-webdav"


def _authenticated_url(url: str) -> str:
    parts = urlsplit(str(url))
    path = parts.path.replace("/dav-anon/", "/dav/", 1)
    return urlunsplit(("https", parts.netloc, path, parts.query, ""))


def authenticated_download_current_safe_file(
    relative_paths: Iterable[str], destination: Path, timeout: int = 180
) -> tuple[str, str, int]:
    relative_paths = tuple(relative_paths)
    if len(relative_paths) != 1:
        raise source.SourceResolutionError(
            "B12A authenticated resolver requires one logical file at a time."
        )
    basename = Path(relative_paths[0]).name
    if basename not in source.SAFE_BASENAMES:
        raise b12.SealViolation(f"B12A refuses non-allow-listed basename {basename!r}.")
    if source._norm(basename) == source._norm(b12.FORBIDDEN_ANSWER_BASENAME):
        raise b12.SealViolation("B12A authenticated resolver cannot acquire outcomes.")

    payload = source.registry_payload()
    candidates = source.candidate_urls(payload, basename)
    attempts: list[dict[str, object]] = []
    seen: set[str] = set()
    for candidate in candidates:
        url = _authenticated_url(candidate)
        if url in seen:
            continue
        seen.add(url)
        try:
            response = requests.get(
                url,
                auth=("anonymous", ""),
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/csv,*/*;q=0.5",
                },
                timeout=(30, timeout),
                allow_redirects=False,
            )
            attempts.append(
                {
                    "url": url,
                    "status": response.status_code,
                    "location": response.headers.get("location", ""),
                    "content_type": response.headers.get("content-type", ""),
                    "size": len(response.content),
                    "html_like": source._is_html_response(response),
                }
            )
            response.raise_for_status()
            if response.is_redirect or not response.content:
                continue
            if source._is_html_response(response):
                continue
            if not registry.permissive_safe_schema(basename, response.content):
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
            return url, b12._sha256_bytes(response.content), len(response.content)
        except Exception as exc:
            attempts.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    raise source.SourceResolutionError(
        "Unable to resolve official B12A input through authenticated-anonymous "
        f"CyVerse WebDAV for {basename}. Diagnostics:\n"
        + json.dumps(attempts[-20:], indent=2)
    )


def run(root: Path):
    source.download_current_safe_file = authenticated_download_current_safe_file
    return registry.run(root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run blind B12A via authenticated-anonymous CyVerse WebDAV."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B12A sealed prediction stage complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
