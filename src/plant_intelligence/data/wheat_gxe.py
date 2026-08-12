"""Case Study B acquisition and validation design for multi-environment wheat.

The locked source is the Dryad dataset accompanying Lopez-Cruz & de los Campos
(2025), DOI 10.5061/dryad.vx0k6dk3p. It contains 3,731 CIMMYT wheat lines,
9,045 filtered SNP markers, and grain-yield records in four managed environments.

Large source files are downloaded at execution time and remain outside Git. The
module publishes only compact audits and split manifests under reports/results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
from sklearn.model_selection import KFold

DRYAD_DOI = "10.5061/dryad.vx0k6dk3p"
DRYAD_DATASET_URL = "https://datadryad.org/dataset/doi:10.5061/dryad.vx0k6dk3p"
DRYAD_FILE_NAME = "wheat_data.tar.gz"
DRYAD_FILE_STREAMS = (
    "https://datadryad.org/downloads/file_stream/4077944",
    "https://datadryad.org/downloads/file_stream/4074242",
)
EXPECTED_LINES = 3731
EXPECTED_MARKERS = 9045
EXPECTED_ENVIRONMENTS = ("B2I", "B5I", "MEL", "LHT")
SEED = 20260812


def environment_metadata() -> pd.DataFrame:
    """Return source-documented environment descriptors without inventing fields."""

    return pd.DataFrame(
        [
            {
                "environment": "B2I",
                "description": "bed planting and two irrigations",
                "planting_system": "bed",
                "irrigations": 2,
                "stress_family": "drought",
                "heat_timing": "none_documented",
            },
            {
                "environment": "B5I",
                "description": "bed planting and five irrigations",
                "planting_system": "bed",
                "irrigations": 5,
                "stress_family": "optimal",
                "heat_timing": "none_documented",
            },
            {
                "environment": "MEL",
                "description": "melgas flat planting and five irrigations",
                "planting_system": "flat",
                "irrigations": 5,
                "stress_family": "optimal",
                "heat_timing": "none_documented",
            },
            {
                "environment": "LHT",
                "description": "late heat",
                "planting_system": pd.NA,
                "irrigations": pd.NA,
                "stress_family": "heat",
                "heat_timing": "late",
            },
        ]
    )


def _download_candidates() -> tuple[str, ...]:
    encoded = quote(f"doi:{DRYAD_DOI}", safe="")
    double_encoded = quote(encoded, safe="")
    return (
        f"https://datadryad.org/api/v2/datasets/{encoded}/download",
        f"https://datadryad.org/api/v2/datasets/{double_encoded}/download",
        *DRYAD_FILE_STREAMS,
    )


def _safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Unsafe zip member: {member.filename}")
        zf.extractall(destination)


def _materialize_download_payload(
    response: requests.Response,
    destination: Path,
    source_url: str,
) -> tuple[Path, str]:
    """Normalize a Dryad gzip or full-dataset ZIP response to wheat_data.tar.gz."""

    first = next(response.iter_content(chunk_size=1024 * 1024), b"")
    if not first:
        raise ValueError("empty payload")

    if first.startswith(b"\x1f\x8b"):
        digest = hashlib.sha256()
        with destination.open("wb") as handle:
            handle.write(first)
            digest.update(first)
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
                    digest.update(chunk)
        return destination, digest.hexdigest()

    if first.startswith(b"PK\x03\x04"):
        package = destination.with_suffix(".dryad.zip")
        with package.open("wb") as handle:
            handle.write(first)
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        unpacked = destination.parent / "dryad_package"
        if unpacked.exists():
            shutil.rmtree(unpacked)
        _safe_extract_zip(package, unpacked)
        matches = list(unpacked.rglob(DRYAD_FILE_NAME))
        if len(matches) != 1:
            raise ValueError(
                f"Dryad ZIP from {source_url} contained {len(matches)} {DRYAD_FILE_NAME!r} files"
            )
        shutil.copyfile(matches[0], destination)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        return destination, digest

    content_type = response.headers.get("Content-Type", "unknown")
    raise ValueError(f"unsupported payload {content_type}; prefix={first[:32]!r}")


def download_source_archive(destination: Path, timeout: int = 240) -> dict[str, str]:
    """Download the locked Dryad archive through the public dataset API.

    The public landing page's individual file route can return an HTML interstitial
    to automated clients. The function therefore tries the dataset API archive first,
    accepts either a full-dataset ZIP or the target gzip, validates the payload magic,
    and records the exact successful URL plus SHA-256 checksum.
    """

    destination.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": "plant-intelligence-lab/0.1 reproducible-research",
        "Accept": "application/zip,application/gzip,application/octet-stream,*/*;q=0.5",
        "Referer": DRYAD_DATASET_URL,
    }
    failures: list[str] = []

    with requests.Session() as session:
        for url in _download_candidates():
            try:
                with session.get(
                    url,
                    headers=headers,
                    timeout=(30, timeout),
                    stream=True,
                    allow_redirects=True,
                ) as response:
                    if response.status_code != 200:
                        failures.append(f"{url} -> HTTP {response.status_code}")
                        continue
                    try:
                        archive, digest = _materialize_download_payload(response, destination, url)
                    except ValueError as exc:
                        failures.append(f"{url} -> {exc}")
                        continue
                    return {
                        "dataset_doi": DRYAD_DOI,
                        "dataset_url": DRYAD_DATASET_URL,
                        "download_url": url,
                        "archive": archive.name,
                        "sha256": digest,
                    }
            except requests.RequestException as exc:
                failures.append(f"{url} -> {type(exc).__name__}: {exc}")

    raise RuntimeError("Dryad archive acquisition failed: " + " | ".join(failures))


def _safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            target = (destination / member.name).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Unsafe archive member: {member.name}")
        tf.extractall(destination)  # noqa: S202 - paths validated immediately above


def _find_unique(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected exactly one {name!r}; found {len(matches)}")
    return matches[0]


def load_locked_matrices(extracted_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load phenotype and genotype matrices from the Dryad archive."""

    pheno = pd.read_csv(_find_unique(extracted_dir, "pheno.csv"), index_col=0)
    geno = pd.read_csv(_find_unique(extracted_dir, "geno.csv"), index_col=0)
    pheno.index = pheno.index.astype(str)
    geno.index = geno.index.astype(str)
    pheno.columns = [str(col) for col in pheno.columns]
    geno.columns = [str(col) for col in geno.columns]
    return pheno, geno


def audit_matrices(pheno: pd.DataFrame, geno: pd.DataFrame) -> pd.DataFrame:
    """Validate the public data lock and return a one-row scientific audit."""

    envs = tuple(pheno.columns)
    if pheno.shape != (EXPECTED_LINES, len(EXPECTED_ENVIRONMENTS)):
        raise ValueError(f"Unexpected phenotype shape: {pheno.shape}")
    if geno.shape != (EXPECTED_LINES, EXPECTED_MARKERS):
        raise ValueError(f"Unexpected genotype shape: {geno.shape}")
    if set(envs) != set(EXPECTED_ENVIRONMENTS):
        raise ValueError(f"Unexpected environments: {envs}")
    if set(pheno.index) != set(geno.index):
        raise ValueError("Phenotype and genotype line identifiers do not match exactly.")

    pheno_missing = int(pheno.isna().sum().sum())
    geno_missing = int(geno.isna().sum().sum())
    return pd.DataFrame(
        [
            {
                "dataset_doi": DRYAD_DOI,
                "data_license": "CC0",
                "n_lines": len(pheno),
                "n_markers": geno.shape[1],
                "n_environments": pheno.shape[1],
                "n_phenotype_cells": int(pheno.size),
                "phenotype_missing_cells": pheno_missing,
                "genotype_missing_cells": geno_missing,
                "p_over_n": float(geno.shape[1] / len(pheno)),
                "primary_validation": "CV-G + CV2 sparse-cell",
                "stress_validation": "CV-E + CV-GE",
                "cold_environment_limitation": (
                    "Only four managed environments and incomplete transferable environment "
                    "descriptors; CV-E/CV-GE are stress tests, not headline evidence."
                ),
            }
        ]
    )


def build_cv_g(genotype_ids: list[str], n_splits: int = 5, seed: int = SEED) -> pd.DataFrame:
    """CV-G / CV1: hold out entire genotypes across all environments."""

    ids = np.asarray(sorted(map(str, genotype_ids)))
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    rows: list[dict[str, object]] = []
    for fold, (_, test_idx) in enumerate(splitter.split(ids)):
        rows.extend({"genotype_id": ids[i], "fold": fold} for i in test_idx)
    out = pd.DataFrame(rows).sort_values("genotype_id").reset_index(drop=True)
    if out["genotype_id"].duplicated().any():
        raise AssertionError("Each genotype must belong to exactly one CV-G fold.")
    return out


def build_cv2_sparse(genotype_ids: list[str], environments: tuple[str, ...]) -> pd.DataFrame:
    """CV2-style sparse MET design: one held-out environment per genotype."""

    ids = sorted(map(str, genotype_ids))
    envs = tuple(environments)
    rows = [
        {"genotype_id": gid, "test_environment": envs[i % len(envs)]}
        for i, gid in enumerate(ids)
    ]
    return pd.DataFrame(rows)


def build_cv_e(environments: tuple[str, ...]) -> pd.DataFrame:
    """CV-E diagnostic: leave one entire managed environment out."""

    return pd.DataFrame(
        [{"environment": env, "fold": fold} for fold, env in enumerate(environments)]
    )


def build_cv_ge_scenarios(
    cv_g: pd.DataFrame,
    environments: tuple[str, ...],
) -> pd.DataFrame:
    """Strict genotype-plus-environment cold-start scenarios."""

    n_total_genotypes = cv_g["genotype_id"].nunique()
    n_g_folds = cv_g["fold"].nunique()
    rows: list[dict[str, object]] = []
    for env_fold, env in enumerate(environments):
        for g_fold in sorted(cv_g["fold"].unique()):
            n_test_genotypes = int((cv_g["fold"] == g_fold).sum())
            n_train_genotypes = n_total_genotypes - n_test_genotypes
            rows.append(
                {
                    "scenario": f"env_{env}__gfold_{g_fold}",
                    "held_out_environment": env,
                    "environment_fold": env_fold,
                    "genotype_fold": int(g_fold),
                    "n_test_genotypes": n_test_genotypes,
                    "n_test_cells": n_test_genotypes,
                    "n_train_genotypes": n_train_genotypes,
                    "n_train_cells": n_train_genotypes * (len(environments) - 1),
                    "admission": "stress_test_only",
                }
            )
    if len(rows) != len(environments) * n_g_folds:
        raise AssertionError("Unexpected number of CV-GE scenarios.")
    return pd.DataFrame(rows)


def run_data_lock(output_root: Path) -> dict[str, Path]:
    """Acquire, audit, and materialize compact Case Study B evidence."""

    raw_dir = output_root / "data" / "raw" / "case_study_b"
    interim_dir = output_root / "data" / "interim" / "case_study_b"
    results_dir = output_root / "reports" / "results"
    raw_dir.mkdir(parents=True, exist_ok=True)
    interim_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    archive = raw_dir / DRYAD_FILE_NAME
    provenance = download_source_archive(archive)
    provenance_path = raw_dir / "source_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    _safe_extract(archive, interim_dir)
    pheno, geno = load_locked_matrices(interim_dir)
    audit = audit_matrices(pheno, geno)
    cv_g = build_cv_g(pheno.index.tolist())
    cv2 = build_cv2_sparse(pheno.index.tolist(), EXPECTED_ENVIRONMENTS)
    cv_e = build_cv_e(EXPECTED_ENVIRONMENTS)
    cv_ge = build_cv_ge_scenarios(cv_g, EXPECTED_ENVIRONMENTS)
    env_meta = environment_metadata()
    correlations = pheno.loc[:, list(EXPECTED_ENVIRONMENTS)].corr()

    paths = {
        "audit": results_dir / "case_study_b_data_lock_summary.csv",
        "environment_metadata": results_dir / "case_study_b_environment_metadata.csv",
        "environment_correlations": results_dir / "case_study_b_environment_correlations.csv",
        "cv_g": results_dir / "case_study_b_cv_g_folds.csv",
        "cv2": results_dir / "case_study_b_cv2_sparse_mask.csv",
        "cv_e": results_dir / "case_study_b_cv_e_folds.csv",
        "cv_ge": results_dir / "case_study_b_cv_ge_scenarios.csv",
    }
    audit.to_csv(paths["audit"], index=False)
    env_meta.to_csv(paths["environment_metadata"], index=False)
    correlations.to_csv(paths["environment_correlations"])
    cv_g.to_csv(paths["cv_g"], index=False)
    cv2.to_csv(paths["cv2"], index=False)
    cv_e.to_csv(paths["cv_e"], index=False)
    cv_ge.to_csv(paths["cv_ge"], index=False)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire and audit Case Study B wheat GxE data.")
    parser.add_argument("--output-root", default=".", help="Repository root for materialized outputs.")
    args = parser.parse_args()
    paths = run_data_lock(Path(args.output_root).resolve())
    print("Case Study B data lock complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
