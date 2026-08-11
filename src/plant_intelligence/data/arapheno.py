"""AraPheno acquisition utilities for Case Study A.

The module keeps public-source acquisition separate from modelling. It is designed
for reproducible retrieval of phenotype records and preserves source metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


ARAPHENO_BASE = "https://arapheno.1001genomes.org"


@dataclass(frozen=True)
class PhenotypeTarget:
    phenotype_id: int
    trait: str
    day: int
    protocol: str


# First outcome family specified by the repository blueprint.
PRIMARY_TARGETS = (
    PhenotypeTarget(1267, "shoots", 15, "a"),
    PhenotypeTarget(1288, "shoots", 21, "b"),
)


def sha256_bytes(payload: bytes) -> str:
    """Return a SHA-256 checksum for provenance tracking."""
    return hashlib.sha256(payload).hexdigest()


def phenotype_page_url(phenotype_id: int) -> str:
    """Return the canonical public AraPheno phenotype page."""
    return f"{ARAPHENO_BASE}/phenotype/{phenotype_id}/"


def phenotype_json_url(phenotype_id: int) -> str:
    """Return the AraPheno JSON download endpoint used by the public UI.

    AraPheno exposes JSON downloads from each phenotype page. Endpoint behaviour
    should be verified during acquisition because upstream services can change.
    """
    return f"{ARAPHENO_BASE}/phenotype/{phenotype_id}/download/json/"


def fetch_bytes(url: str, timeout: int = 60) -> bytes:
    """Retrieve a public resource using an explicit user agent."""
    request = Request(
        url,
        headers={"User-Agent": "plant-intelligence-lab/0.1 (+public research project)"},
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed public HTTPS sources
        return response.read()


def fetch_phenotype_json(phenotype_id: int, timeout: int = 60) -> tuple[Any, dict[str, str]]:
    """Retrieve a phenotype JSON payload and return data plus provenance metadata."""
    url = phenotype_json_url(phenotype_id)
    payload = fetch_bytes(url, timeout=timeout)
    data = json.loads(payload.decode("utf-8"))
    provenance = {
        "phenotype_id": str(phenotype_id),
        "source_url": url,
        "canonical_page": phenotype_page_url(phenotype_id),
        "sha256": sha256_bytes(payload),
    }
    return data, provenance


def save_phenotype_json(
    phenotype_id: int,
    output_dir: str | Path,
    timeout: int = 60,
) -> tuple[Path, Path]:
    """Save immutable source JSON plus a provenance sidecar."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data, provenance = fetch_phenotype_json(phenotype_id, timeout=timeout)
    data_path = output_dir / f"arapheno_phenotype_{phenotype_id}.json"
    provenance_path = output_dir / f"arapheno_phenotype_{phenotype_id}.provenance.json"

    data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    provenance_path.write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return data_path, provenance_path
