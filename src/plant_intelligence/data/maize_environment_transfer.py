"""Case Study B Step B5: continuous-environment transfer data lock.

This module locks the curated Genomes-to-Fields maize resource published by
Lopez-Cruz et al. (2023) on Figshare (article 22776806). The public article
currently exposes ``curated_data.zip`` containing:

- PHENO.csv: multi-environment phenotypes and environment/genotype identifiers;
- GENO.csv: hybrid SNP marker matrix;
- ECOV.csv: continuous environmental covariates indexed by environment.

The purpose of B5 is not to fit a new predictor. It is to establish a
reproducible G + E_continuous + Y source and freeze environment-level and
combined genotype/environment transfer manifests before modeling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.model_selection import KFold

FIGSHARE_ARTICLE_ID = 22776806
FIGSHARE_API = f"https://api.figshare.com/v2/articles/{FIGSHARE_ARTICLE_ID}"
FIGSHARE_DOI = "10.6084/m9.figshare.22776806"
EXPECTED_FILES = ("PHENO.csv", "GENO.csv", "ECOV.csv")
ARCHIVE_NAME = "curated_data.zip"
SEED = 20260812
N_ENV_FOLDS = 5
N_GENO_FOLDS = 5


def _download(url: str, destination: Path, timeout: int = 300) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    headers = {"User-Agent": "plant-intelligence-lab/0.1 reproducible-research"}
    with requests.get(url, headers=headers, stream=True, timeout=(30, timeout)) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
                    digest.update(chunk)
    return digest.hexdigest()


def resolve_figshare_files(timeout: int = 60) -> dict[str, dict[str, object]]:
    """Resolve exact Figshare file URLs from article metadata."""
    response = requests.get(
        FIGSHARE_API,
        headers={"User-Agent": "plant-intelligence-lab/0.1 reproducible-research"},
        timeout=(20, timeout),
    )
    response.raise_for_status()
    metadata = response.json()
    files = {str(item["name"]): item for item in metadata.get("files", [])}
    if all(name in files for name in EXPECTED_FILES):
        return {name: files[name] for name in EXPECTED_FILES}
    if ARCHIVE_NAME in files:
        return {ARCHIVE_NAME: files[ARCHIVE_NAME]}
    raise FileNotFoundError(
        f"Figshare article {FIGSHARE_ARTICLE_ID} exposes neither the expected CSV files "
        f"nor {ARCHIVE_NAME}; available={sorted(files)}"
    )


def _extract_expected_archive(archive: Path, destination: Path) -> dict[str, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    resolved: dict[str, Path] = {}
    with zipfile.ZipFile(archive) as zf:
        members = zf.namelist()
        for expected in EXPECTED_FILES:
            matches = [m for m in members if Path(m).name == expected]
            if len(matches) != 1:
                raise FileNotFoundError(
                    f"Expected exactly one {expected} inside {archive.name}; matches={matches}"
                )
            member = matches[0]
            target = destination / expected
            with zf.open(member) as src, target.open("wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
            resolved[expected] = target
    return resolved


def acquire_source(root: Path) -> tuple[dict[str, Path], dict[str, object]]:
    raw = root / "data" / "raw" / "case_study_b5_g2f"
    raw.mkdir(parents=True, exist_ok=True)
    resolved = resolve_figshare_files()
    paths: dict[str, Path] = {}
    provenance_files: list[dict[str, object]] = []

    if ARCHIVE_NAME in resolved:
        meta = resolved[ARCHIVE_NAME]
        archive = raw / ARCHIVE_NAME
        sha256 = _download(str(meta["download_url"]), archive)
        provenance_files.append(
            {
                "name": ARCHIVE_NAME,
                "figshare_file_id": meta.get("id"),
                "download_url": meta.get("download_url"),
                "size_bytes": int(archive.stat().st_size),
                "sha256": sha256,
            }
        )
        paths = _extract_expected_archive(archive, raw)
        for name, path in paths.items():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            provenance_files.append(
                {
                    "name": name,
                    "source_archive": ARCHIVE_NAME,
                    "size_bytes": int(path.stat().st_size),
                    "sha256": digest,
                }
            )
    else:
        for name, meta in resolved.items():
            destination = raw / name
            sha256 = _download(str(meta["download_url"]), destination)
            paths[name] = destination
            provenance_files.append(
                {
                    "name": name,
                    "figshare_file_id": meta.get("id"),
                    "download_url": meta.get("download_url"),
                    "size_bytes": int(destination.stat().st_size),
                    "sha256": sha256,
                }
            )

    provenance = {
        "source": "Lopez-Cruz et al. (2023) curated Genomes-to-Fields maize dataset",
        "figshare_article_id": FIGSHARE_ARTICLE_ID,
        "doi": FIGSHARE_DOI,
        "files": provenance_files,
    }
    (raw / "source_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return paths, provenance


def load_source(paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pheno = pd.read_csv(paths["PHENO.csv"], low_memory=False)
    geno = pd.read_csv(paths["GENO.csv"], low_memory=False)
    ecov = pd.read_csv(paths["ECOV.csv"], index_col=0, low_memory=False)
    return pheno, geno, ecov


def _required_columns(pheno: pd.DataFrame) -> tuple[str, str, str]:
    genotype_candidates = ["genotype", "Genotype", "hybrid", "Hybrid"]
    environment_candidates = ["year_loc", "environment", "Environment", "Env"]
    yield_candidates = ["yield", "Yield", "grain_yield", "GY"]
    genotype = next((c for c in genotype_candidates if c in pheno.columns), None)
    environment = next((c for c in environment_candidates if c in pheno.columns), None)
    trait = next((c for c in yield_candidates if c in pheno.columns), None)
    if genotype is None or environment is None or trait is None:
        raise ValueError(
            "Could not resolve genotype/environment/yield columns from PHENO.csv; "
            f"columns={list(pheno.columns)}"
        )
    return genotype, environment, trait


def audit_source(
    pheno: pd.DataFrame,
    geno: pd.DataFrame,
    ecov: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    genotype_col, env_col, trait_col = _required_columns(pheno)
    if geno.shape[1] < 2:
        raise ValueError("GENO.csv must contain an identifier column and at least one marker.")
    geno_id_col = str(geno.columns[0])
    geno_ids = set(geno[geno_id_col].astype(str))
    phenotype_genotypes = set(pheno[genotype_col].dropna().astype(str))
    phenotype_envs = set(pheno[env_col].dropna().astype(str))
    ecov_envs = set(ecov.index.astype(str))

    numeric_ecov = ecov.apply(pd.to_numeric, errors="coerce")
    nonempty_ec = numeric_ecov.columns[numeric_ecov.notna().any(axis=0)]
    nonconstant_ec = [c for c in nonempty_ec if numeric_ecov[c].dropna().nunique() > 1]
    if not nonconstant_ec:
        raise ValueError("No nonconstant continuous environmental covariates were resolved.")

    years = pd.Series(pheno[env_col].dropna().astype(str)).str.extract(r"((?:19|20)\d{2})", expand=False)
    summary = pd.DataFrame(
        [
            {
                "source_doi": FIGSHARE_DOI,
                "n_phenotype_records": int(len(pheno)),
                "n_phenotype_genotypes": int(len(phenotype_genotypes)),
                "n_genotyped_hybrids": int(len(geno_ids)),
                "n_markers": int(geno.shape[1] - 1),
                "n_phenotype_environments": int(len(phenotype_envs)),
                "n_ecov_environments": int(len(ecov_envs)),
                "n_environment_covariates_raw": int(ecov.shape[1]),
                "n_environment_covariates_nonconstant": int(len(nonconstant_ec)),
                "phenotype_environment_ecov_overlap": int(len(phenotype_envs & ecov_envs)),
                "phenotype_genotype_genomic_overlap": int(len(phenotype_genotypes & geno_ids)),
                "yield_nonmissing": int(pd.to_numeric(pheno[trait_col], errors="coerce").notna().sum()),
                "ecov_missing_fraction": float(numeric_ecov[nonconstant_ec].isna().mean().mean()),
                "first_year": years.dropna().min() if years.notna().any() else "unknown",
                "last_year": years.dropna().max() if years.notna().any() else "unknown",
                "primary_transfer_validation": "environment-level 5-fold cold-start with ECs available",
                "strict_transfer_validation": "crossed genotype-fold x environment-fold cold-start",
            }
        ]
    )

    ec_audit = pd.DataFrame(
        {
            "covariate": list(numeric_ecov.columns),
            "nonmissing": [int(numeric_ecov[c].notna().sum()) for c in numeric_ecov.columns],
            "missing_fraction": [float(numeric_ecov[c].isna().mean()) for c in numeric_ecov.columns],
            "n_unique": [int(numeric_ecov[c].dropna().nunique()) for c in numeric_ecov.columns],
            "is_nonconstant_numeric": [c in nonconstant_ec for c in numeric_ecov.columns],
        }
    )
    columns = {
        "genotype": genotype_col,
        "environment": env_col,
        "trait": trait_col,
        "geno_id": geno_id_col,
    }
    return summary, ec_audit, columns


def build_transfer_manifests(pheno: pd.DataFrame, columns: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    genotype_col = columns["genotype"]
    env_col = columns["environment"]
    environments = np.asarray(sorted(pheno[env_col].dropna().astype(str).unique()))
    genotypes = np.asarray(sorted(pheno[genotype_col].dropna().astype(str).unique()))
    if len(environments) < N_ENV_FOLDS or len(genotypes) < N_GENO_FOLDS:
        raise ValueError("Too few environments or genotypes for locked five-fold transfer manifests.")

    env_rows: list[dict[str, object]] = []
    splitter = KFold(n_splits=N_ENV_FOLDS, shuffle=True, random_state=SEED)
    for fold, (_, test_idx) in enumerate(splitter.split(environments)):
        for idx in test_idx:
            env_rows.append({"environment": environments[idx], "environment_fold": fold})
    env_manifest = pd.DataFrame(env_rows).sort_values("environment").reset_index(drop=True)

    geno_rows: list[dict[str, object]] = []
    splitter_g = KFold(n_splits=N_GENO_FOLDS, shuffle=True, random_state=SEED)
    for fold, (_, test_idx) in enumerate(splitter_g.split(genotypes)):
        for idx in test_idx:
            geno_rows.append({"genotype": genotypes[idx], "genotype_fold": fold})
    geno_manifest = pd.DataFrame(geno_rows).sort_values("genotype").reset_index(drop=True)

    crossed = pd.DataFrame(
        [
            {
                "scenario": f"efold_{efold}__gfold_{gfold}",
                "environment_fold": efold,
                "genotype_fold": gfold,
                "admission": "strict_GxE_transfer",
            }
            for efold in range(N_ENV_FOLDS)
            for gfold in range(N_GENO_FOLDS)
        ]
    )
    return env_manifest, geno_manifest, crossed


def run_data_lock(output_root: Path) -> dict[str, Path]:
    root = output_root.resolve()
    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)
    paths, _ = acquire_source(root)
    pheno, geno, ecov = load_source(paths)
    summary, ec_audit, columns = audit_source(pheno, geno, ecov)
    env_manifest, geno_manifest, crossed = build_transfer_manifests(pheno, columns)

    outputs = {
        "summary": results / "case_study_b5_data_lock_summary.csv",
        "ecov_audit": results / "case_study_b5_environment_covariate_audit.csv",
        "environment_folds": results / "case_study_b5_environment_transfer_folds.csv",
        "genotype_folds": results / "case_study_b5_genotype_transfer_folds.csv",
        "crossed_scenarios": results / "case_study_b5_gxe_transfer_scenarios.csv",
    }
    summary.to_csv(outputs["summary"], index=False)
    ec_audit.to_csv(outputs["ecov_audit"], index=False)
    env_manifest.to_csv(outputs["environment_folds"], index=False)
    geno_manifest.to_csv(outputs["genotype_folds"], index=False)
    crossed.to_csv(outputs["crossed_scenarios"], index=False)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Lock G2F continuous-environment transfer data for Case Study B5.")
    parser.add_argument("--output-root", default=".")
    args = parser.parse_args()
    outputs = run_data_lock(Path(args.output_root))
    print("Case Study B Step B5 continuous-environment data lock complete")
    for key, value in outputs.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
