"""Case Study B acquisition and validation design for multi-environment wheat.

The executable data lock uses the canonical ``wheat`` dataset distributed with
BGLR on CRAN. It contains 599 historical CIMMYT wheat lines, 1,279 edited DArT
markers, and standardized grain-yield phenotypes in four mega-environments.

The source package is downloaded at execution time and remains outside Git. Only
compact audit and validation manifests are published under ``reports/results``.
"""

from __future__ import annotations

import argparse
import hashlib
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.model_selection import KFold

BGLR_VERSION = "1.1.4"
BGLR_PACKAGE_URL = f"https://cran.r-project.org/src/contrib/BGLR_{BGLR_VERSION}.tar.gz"
BGLR_PACKAGE_NAME = f"BGLR_{BGLR_VERSION}.tar.gz"
BGLR_PROJECT_URL = "https://CRAN.R-project.org/package=BGLR"
SOURCE_INSTITUTION = "International Maize and Wheat Improvement Center (CIMMYT), Mexico"
EXPECTED_LINES = 599
EXPECTED_MARKERS = 1279
EXPECTED_ENVIRONMENTS = ("ME1", "ME2", "ME3", "ME4")
SEED = 20260812


def environment_metadata() -> pd.DataFrame:
    """Return only source-supported descriptors for the four mega-environments.

    The BGLR documentation identifies four target sets of environments / main
    agroclimatic regions but does not publish a transferable weather/soil vector.
    Missing physical descriptors are therefore left missing rather than inferred.
    """

    return pd.DataFrame(
        [
            {
                "environment": env,
                "description": f"CIMMYT wheat mega-environment {idx}",
                "environment_type": "target_set_of_environments",
                "continuous_covariates_available": False,
            }
            for idx, env in enumerate(EXPECTED_ENVIRONMENTS, start=1)
        ]
    )


def download_source_package(destination: Path, timeout: int = 180) -> dict[str, str]:
    """Download the version-locked BGLR CRAN source package with provenance."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": "plant-intelligence-lab/0.1 reproducible-research",
        "Accept": "application/gzip,application/octet-stream,*/*;q=0.5",
    }
    digest = hashlib.sha256()
    with requests.get(
        BGLR_PACKAGE_URL,
        headers=headers,
        timeout=(30, timeout),
        stream=True,
    ) as response:
        response.raise_for_status()
        iterator = response.iter_content(chunk_size=1024 * 1024)
        first = next(iterator, b"")
        if not first.startswith(b"\x1f\x8b"):
            content_type = response.headers.get("Content-Type", "unknown")
            raise RuntimeError(
                f"CRAN returned a non-gzip payload ({content_type}, prefix={first[:24]!r})."
            )
        with destination.open("wb") as handle:
            handle.write(first)
            digest.update(first)
            for chunk in iterator:
                if chunk:
                    handle.write(chunk)
                    digest.update(chunk)

    return {
        "source_package": f"BGLR {BGLR_VERSION}",
        "source_url": BGLR_PACKAGE_URL,
        "project_url": BGLR_PROJECT_URL,
        "archive": destination.name,
        "sha256": digest.hexdigest(),
    }


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


def _as_frame(value: object) -> pd.DataFrame:
    frame = value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame(value)
    return frame.apply(pd.to_numeric, errors="coerce")


def load_locked_matrices(extracted_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load ``wheat.Y`` and ``wheat.X`` from BGLR's version-locked R data file."""

    try:
        import pyreadr
    except ImportError as exc:  # pragma: no cover - exercised by workflow installation
        raise RuntimeError(
            "Case Study B acquisition requires optional dependency 'pyreadr'. "
            "Install with: python -m pip install -e '.[case-study-b]'"
        ) from exc

    rdata = _find_unique(extracted_dir, "wheat.RData")
    objects = pyreadr.read_r(str(rdata))

    pheno_obj = objects.get("wheat.Y")
    geno_obj = objects.get("wheat.X")
    if pheno_obj is None:
        candidates = [obj for obj in objects.values() if getattr(obj, "shape", None) == (599, 4)]
        if len(candidates) == 1:
            pheno_obj = candidates[0]
    if geno_obj is None:
        candidates = [obj for obj in objects.values() if getattr(obj, "shape", None) == (599, 1279)]
        if len(candidates) == 1:
            geno_obj = candidates[0]
    if pheno_obj is None or geno_obj is None:
        shapes = {name: getattr(obj, "shape", None) for name, obj in objects.items()}
        raise ValueError(f"Could not resolve wheat.Y/wheat.X from BGLR archive; objects={shapes}")

    pheno = _as_frame(pheno_obj)
    geno = _as_frame(geno_obj)
    ids = [f"W{idx:03d}" for idx in range(1, len(pheno) + 1)]
    pheno.index = ids
    geno.index = ids
    pheno.columns = list(EXPECTED_ENVIRONMENTS)
    geno.columns = [f"M{idx:04d}" for idx in range(1, geno.shape[1] + 1)]
    return pheno, geno


def audit_matrices(pheno: pd.DataFrame, geno: pd.DataFrame) -> pd.DataFrame:
    """Validate the public data lock and return a one-row scientific audit."""

    if pheno.shape != (EXPECTED_LINES, len(EXPECTED_ENVIRONMENTS)):
        raise ValueError(f"Unexpected phenotype shape: {pheno.shape}")
    if geno.shape != (EXPECTED_LINES, EXPECTED_MARKERS):
        raise ValueError(f"Unexpected genotype shape: {geno.shape}")
    if tuple(pheno.columns) != EXPECTED_ENVIRONMENTS:
        raise ValueError(f"Unexpected environments: {tuple(pheno.columns)}")
    if not pheno.index.equals(geno.index):
        raise ValueError("Phenotype and genotype line identifiers do not match exactly.")

    return pd.DataFrame(
        [
            {
                "source_package": f"BGLR {BGLR_VERSION}",
                "source_institution": SOURCE_INSTITUTION,
                "package_license": "GPL-3",
                "n_lines": len(pheno),
                "n_markers": geno.shape[1],
                "n_environments": pheno.shape[1],
                "n_phenotype_cells": int(pheno.size),
                "phenotype_missing_cells": int(pheno.isna().sum().sum()),
                "genotype_missing_cells": int(geno.isna().sum().sum()),
                "p_over_n": float(geno.shape[1] / len(pheno)),
                "primary_validation": "CV-G + CV2 sparse-cell",
                "stress_validation": "CV-E + CV-GE",
                "cold_environment_limitation": (
                    "Four categorical mega-environments lack transferable continuous weather/soil "
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
    return pd.DataFrame(
        [
            {"genotype_id": gid, "test_environment": envs[i % len(envs)]}
            for i, gid in enumerate(ids)
        ]
    )


def build_cv_e(environments: tuple[str, ...]) -> pd.DataFrame:
    """CV-E diagnostic: leave one categorical mega-environment out."""

    return pd.DataFrame(
        [{"environment": env, "fold": fold} for fold, env in enumerate(environments)]
    )


def build_cv_ge_scenarios(
    cv_g: pd.DataFrame,
    environments: tuple[str, ...],
) -> pd.DataFrame:
    """Strict genotype-plus-environment double-cold-start scenarios."""

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

    archive = raw_dir / BGLR_PACKAGE_NAME
    provenance = download_source_package(archive)
    (raw_dir / "source_provenance.json").write_text(
        __import__("json").dumps(provenance, indent=2), encoding="utf-8"
    )

    _safe_extract(archive, interim_dir)
    pheno, geno = load_locked_matrices(interim_dir)
    audit = audit_matrices(pheno, geno)
    cv_g = build_cv_g(pheno.index.tolist())
    cv2 = build_cv2_sparse(pheno.index.tolist(), EXPECTED_ENVIRONMENTS)
    cv_e = build_cv_e(EXPECTED_ENVIRONMENTS)
    cv_ge = build_cv_ge_scenarios(cv_g, EXPECTED_ENVIRONMENTS)
    env_meta = environment_metadata()
    correlations = pheno.corr()

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
