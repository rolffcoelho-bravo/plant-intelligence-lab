"""B13A runner for safe inputs pre-staged through CyVerse GoCommands.

The GitHub Actions workflow acquires only the four allow-listed 2023 files via
anonymous iRODS/GoCommands. This module validates those local bytes and then
runs the unchanged split-schema compatibility audit. It never opens or resolves
the 2023 phenotype path.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from plant_intelligence.uncertainty import maize_b13_2023_source_audit as b13a
from plant_intelligence.uncertainty import maize_b13a_2023_source_audit_runner as schema

IRODS_ROOT = f"/iplant/home/shared/commons_repo/curated/{b13a.DATASET}"


def prestaged_safe_file(
    relative_path: str,
    destination: Path,
    timeout: int = 180,
) -> tuple[str, str, int]:
    del timeout
    b13a.assert_safe_remote_path(relative_path)
    if not destination.exists():
        raise RuntimeError(f"B13A pre-staged safe input is missing: {destination}")
    body = destination.read_bytes()
    if not body:
        raise RuntimeError(f"B13A pre-staged safe input is empty: {destination}")
    if not b13a._schema_valid_csv(body):
        raise RuntimeError(f"B13A pre-staged input is not a schema-valid CSV: {destination}")
    source = f"irods://data.cyverse.org:1247{IRODS_ROOT}/{relative_path.lstrip('/')}"
    return source, hashlib.sha256(body).hexdigest(), len(body)


def run(root: Path):
    original = b13a.download_safe_file
    b13a.download_safe_file = prestaged_safe_file
    try:
        return schema.run(root)
    finally:
        b13a.download_safe_file = original


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run B13A using safe inputs pre-staged via anonymous CyVerse iRODS."
    )
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    print("Case Study B13A pre-staged source audit complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
