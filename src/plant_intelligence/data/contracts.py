from __future__ import annotations

from pathlib import Path
import json
import shutil

import pandas as pd


CANONICAL_PHENOTYPE_SUMMARY = "shoot_regeneration_accession_summary.csv"
LEGACY_PHENOTYPE_SUMMARY = "accession_summary.csv"
PHENOTYPE_ACCESSIONS = "phenotype_accessions.csv"


def validate_case_study_a_interim(interim_dir: str | Path) -> dict:
    """Validate the Notebook 01 -> Notebook 02 artifact contract.

    The canonical accession-level summary produced by Notebook 01 is preserved.
    A compatibility alias is created for Notebook 02 until its loader is migrated
    to the canonical name. The function fails loudly when required identifiers or
    data columns are missing.
    """
    interim = Path(interim_dir)
    canonical = interim / CANONICAL_PHENOTYPE_SUMMARY
    accessions = interim / PHENOTYPE_ACCESSIONS
    legacy = interim / LEGACY_PHENOTYPE_SUMMARY

    missing = [str(p) for p in (canonical, accessions) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Case Study A artifact contract failed. Missing required outputs: "
            + ", ".join(missing)
        )

    summary = pd.read_csv(canonical)
    accession_frame = pd.read_csv(accessions)

    if "accession_id" not in summary.columns:
        raise KeyError(f"{canonical} must contain accession_id")
    if "accession_id" not in accession_frame.columns:
        raise KeyError(f"{accessions} must contain accession_id")

    if summary.empty:
        raise ValueError(f"{canonical} is empty")
    if accession_frame.empty:
        raise ValueError(f"{accessions} is empty")

    summary_ids = set(summary["accession_id"].astype(str).dropna())
    accession_ids = set(accession_frame["accession_id"].astype(str).dropna())

    if not summary_ids:
        raise ValueError("No accession identifiers were found in the phenotype summary")
    if not summary_ids.issubset(accession_ids):
        missing_ids = sorted(summary_ids - accession_ids)[:10]
        raise ValueError(
            "Phenotype summary contains accessions absent from phenotype_accessions.csv: "
            f"{missing_ids}"
        )

    # Compatibility bridge for the current Notebook 02 loader. This is a derived
    # copy only; the canonical file remains the source of truth.
    shutil.copy2(canonical, legacy)

    manifest = {
        "contract": "case_study_a_notebook_01_to_02",
        "canonical_summary": str(canonical),
        "compatibility_alias": str(legacy),
        "accession_file": str(accessions),
        "n_summary_rows": int(len(summary)),
        "n_unique_accessions": int(len(summary_ids)),
        "status": "PASS",
    }

    manifest_path = interim / "artifact_contract.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
