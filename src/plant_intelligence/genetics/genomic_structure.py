from __future__ import annotations

from pathlib import Path
import hashlib
import json
import tarfile
import urllib.request

import h5py
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA


SNP_ARCHIVE_URL = (
    "https://1001genomes.org/data/GMI-MPI/releases/v3.1/"
    "SNP_matrix_imputed_hdf5/1001_SNP_MATRIX.tar.gz"
)
CHUNK_MARKERS = 50_000
MAX_ML_MARKERS = 50_000


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _decode(values) -> np.ndarray:
    out = []
    for value in values:
        if isinstance(value, (bytes, np.bytes_)):
            out.append(value.decode("utf-8"))
        else:
            out.append(str(value))
    return np.asarray(out, dtype=object)


def _inventory_hdf5(path: Path) -> pd.DataFrame:
    rows: list[dict] = []
    with h5py.File(path, "r") as h5:
        def visitor(name, obj):
            if isinstance(obj, h5py.Dataset):
                rows.append(
                    {
                        "name": name,
                        "shape": tuple(obj.shape),
                        "dtype": str(obj.dtype),
                        "ndim": obj.ndim,
                    }
                )
        h5.visititems(visitor)
    return pd.DataFrame(rows)


def _choose_accession_vector(
    h5_path: Path,
    inventory: pd.DataFrame,
    phenotype_ids: set[str],
) -> tuple[str, np.ndarray, int]:
    candidates = inventory[inventory["ndim"] == 1].copy()
    scored = []
    with h5py.File(h5_path, "r") as h5:
        for _, row in candidates.iterrows():
            name = row["name"]
            try:
                values = _decode(np.asarray(h5[name]))
            except Exception:
                continue
            if len(values) < 100:
                continue
            overlap = len(set(values.astype(str)) & phenotype_ids)
            name_bonus = int(any(k in name.lower() for k in ("accession", "sample", "strain", "ecotype", "id")))
            scored.append((overlap, name_bonus, len(values), name, values))
    if not scored:
        raise RuntimeError("No plausible accession identifier vector was found in the SNP HDF5 file.")
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    overlap, _, _, name, values = scored[0]
    if overlap < 30:
        raise RuntimeError(
            f"Best accession identifier vector overlaps only {overlap} phenotype accessions. "
            "Identifier compatibility must be checked before modelling."
        )
    return name, values, overlap


def _genotype_datasets(
    inventory: pd.DataFrame,
    accession_count: int,
) -> list[tuple[str, tuple[int, int], bool, int]]:
    numeric = inventory[
        (inventory["ndim"] == 2)
        & inventory["dtype"].str.contains(r"int|float|bool", case=False, regex=True)
    ].copy()
    candidates = []
    for _, row in numeric.iterrows():
        shape = tuple(row["shape"])
        if accession_count not in shape:
            continue
        accession_first = shape[0] == accession_count
        marker_count = shape[1] if accession_first else shape[0]
        if marker_count < 1000:
            continue
        name = str(row["name"])
        score = int("snp" in name.lower()) + int("geno" in name.lower())
        candidates.append((score, marker_count, name, shape, accession_first))
    if not candidates:
        raise RuntimeError("No genome-scale SNP matrices matched the accession dimension.")
    max_score = max(x[0] for x in candidates)
    if max_score > 0:
        candidates = [x for x in candidates if x[0] == max_score]
    candidates.sort(key=lambda x: x[1], reverse=True)
    if len(candidates) > 1 and candidates[0][1] >= 0.9 * sum(x[1] for x in candidates):
        candidates = [candidates[0]]
    return [(name, shape, accession_first, marker_count) for _, marker_count, name, shape, accession_first in candidates]


def _read_rows_chunk(ds, rows: np.ndarray, accession_first: bool, start: int, stop: int) -> np.ndarray:
    # h5py advanced indexing is most reliable with sorted row indices.
    order = np.argsort(rows)
    sorted_rows = rows[order]
    if accession_first:
        block = np.asarray(ds[sorted_rows, start:stop], dtype=np.float64)
    else:
        block = np.asarray(ds[start:stop, sorted_rows], dtype=np.float64).T
    inverse = np.argsort(order)
    return block[inverse]


def _stream_genomic_qc(
    h5_path: Path,
    datasets: list[tuple[str, tuple[int, int], bool, int]],
    matched_rows: np.ndarray,
    maf_threshold: float = 0.05,
    max_missingness: float = 0.10,
    max_ml_markers: int = MAX_ML_MARKERS,
) -> tuple[np.ndarray, np.ndarray, int, int, int]:
    """Build K from all QC-passing markers while storing only a bounded ML feature matrix.

    The genomic relationship matrix uses every marker that passes missingness, variability and
    MAF filters. A deterministic reservoir of at most ``max_ml_markers`` QC markers is retained
    for later high-dimensional ML so the public workflow remains memory-safe and reproducible.
    """
    n = len(matched_rows)
    k_numerator = np.zeros((n, n), dtype=np.float64)
    denom = 0.0
    p_raw = 0
    p_qc = 0
    selected_blocks: list[np.ndarray] = []
    selected_total = 0

    with h5py.File(h5_path, "r") as h5:
        for name, _, accession_first, marker_count in datasets:
            ds = h5[name]
            print(f"Processing {name}: {marker_count:,} markers", flush=True)
            for start in range(0, marker_count, CHUNK_MARKERS):
                stop = min(start + CHUNK_MARKERS, marker_count)
                block = _read_rows_chunk(ds, matched_rows, accession_first, start, stop)
                p_raw += block.shape[1]

                block[block < 0] = np.nan
                missing_rate = np.mean(np.isnan(block), axis=0)
                keep = missing_rate <= max_missingness
                block = block[:, keep]
                if block.shape[1] == 0:
                    continue

                means = np.nanmean(block, axis=0)
                rr, cc = np.where(np.isnan(block))
                if len(rr):
                    block[rr, cc] = means[cc]

                allele_freq = np.mean(block, axis=0) / 2.0
                maf = np.minimum(allele_freq, 1.0 - allele_freq)
                variable = np.std(block, axis=0) > 0
                keep2 = variable & (maf >= maf_threshold)
                block = block[:, keep2]
                allele_freq = allele_freq[keep2]
                if block.shape[1] == 0:
                    continue

                p_qc += block.shape[1]
                centered = block - 2.0 * allele_freq
                k_numerator += centered @ centered.T
                denom += float(2.0 * np.sum(allele_freq * (1.0 - allele_freq)))

                if selected_total < max_ml_markers:
                    remaining = max_ml_markers - selected_total
                    # Evenly sample within each passing chunk instead of taking only early chromosomes.
                    take = min(remaining, block.shape[1])
                    idx = np.linspace(0, block.shape[1] - 1, num=take, dtype=int)
                    selected_blocks.append(block[:, idx].astype(np.float32, copy=False))
                    selected_total += take

                if start == 0 or stop == marker_count or (start // CHUNK_MARKERS) % 20 == 0:
                    print(
                        f"  {stop:,}/{marker_count:,} read | {p_qc:,} QC markers retained so far",
                        flush=True,
                    )

    if p_qc < 100:
        raise RuntimeError(f"Marker QC retained only {p_qc} markers.")
    if denom <= 0:
        raise RuntimeError("Genomic relationship matrix denominator is non-positive.")

    K = k_numerator / denom
    K = (K + K.T) / 2.0
    G_ml = np.concatenate(selected_blocks, axis=1) if selected_blocks else np.empty((n, 0), dtype=np.float32)
    return K, G_ml, p_raw, p_qc, G_ml.shape[1]


def run(root: str | Path = ".") -> dict:
    root = Path(root).resolve()
    interim = root / "data" / "interim" / "case_study_a"
    processed = root / "data" / "processed" / "case_study_a"
    genomic_raw = root / "data" / "raw" / "1001genomes" / "1135"
    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    for path in (interim, processed, genomic_raw, results, figures):
        path.mkdir(parents=True, exist_ok=True)

    phenotype_path = interim / "shoot_regeneration_accession_summary.csv"
    if not phenotype_path.exists():
        raise FileNotFoundError("Run Notebook 01 first: phenotype summary is missing.")
    phenotype = pd.read_csv(phenotype_path)
    phenotype["accession_id"] = phenotype["accession_id"].astype(str)
    phenotype_ids = set(phenotype["accession_id"].dropna().unique())

    archive = genomic_raw / "1001_SNP_MATRIX.tar.gz"
    if not archive.exists():
        print("Downloading official 1001 Genomes SNP matrix...", flush=True)
        urllib.request.urlretrieve(SNP_ARCHIVE_URL, archive)
        print(f"Downloaded {archive.stat().st_size / 1024**2:.1f} MiB", flush=True)

    extract_dir = genomic_raw / "SNP_matrix_imputed_hdf5"
    extract_dir.mkdir(parents=True, exist_ok=True)
    h5_candidates = list(extract_dir.rglob("*.h5")) + list(extract_dir.rglob("*.hdf5"))
    if not h5_candidates:
        print("Extracting SNP archive...", flush=True)
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(extract_dir)
        h5_candidates = list(extract_dir.rglob("*.h5")) + list(extract_dir.rglob("*.hdf5"))
    if not h5_candidates:
        raise FileNotFoundError("No HDF5 file was found in the official SNP archive.")

    h5_path = next((p for p in h5_candidates if p.name == "imputed_snps_binary.hdf5"), h5_candidates[0])
    print(f"Using HDF5: {h5_path.name}", flush=True)
    inventory = _inventory_hdf5(h5_path)
    inventory.to_csv(results / "case_study_a_hdf5_inventory.csv", index=False)

    accession_dataset, accession_ids, n_overlap_probe = _choose_accession_vector(
        h5_path, inventory, phenotype_ids
    )
    genotype_datasets = _genotype_datasets(inventory, len(accession_ids))

    genomic_ids = pd.Index(accession_ids.astype(str))
    model_accessions = pd.Index(sorted(phenotype_ids)).intersection(genomic_ids)
    if len(model_accessions) < 30:
        raise RuntimeError(f"Only {len(model_accessions)} phenotype accessions matched genomic accessions.")
    print(
        f"Matched {len(model_accessions)} phenotype accessions to {len(accession_ids)} genomic accessions.",
        flush=True,
    )

    row_map = {str(a): i for i, a in enumerate(accession_ids)}
    rows = np.array([row_map[str(a)] for a in model_accessions], dtype=int)

    K, G_ml, p_raw, p_qc, p_ml = _stream_genomic_qc(
        h5_path=h5_path,
        datasets=genotype_datasets,
        matched_rows=rows,
        maf_threshold=0.05,
        max_missingness=0.10,
        max_ml_markers=MAX_ML_MARKERS,
    )

    np.save(processed / "genomic_relationship_matrix.npy", K)
    np.save(processed / "genotype_matrix_qc.npy", G_ml)
    pd.DataFrame({"accession_id": model_accessions.astype(str)}).to_csv(
        processed / "model_accessions.csv", index=False
    )

    # PCA on the bounded QC feature matrix is sufficient for structure-aware splitting;
    # K itself still uses all QC-passing markers.
    n_components = min(10, len(model_accessions) - 1, G_ml.shape[1])
    pca = PCA(n_components=n_components, random_state=42)
    pcs = pca.fit_transform(G_ml)
    n_folds = min(5, max(3, len(model_accessions) // 30))
    clusters = KMeans(n_clusters=n_folds, random_state=42, n_init=20).fit_predict(
        pcs[:, : min(5, n_components)]
    )
    pd.DataFrame({"accession_id": model_accessions.astype(str), "fold": clusters}).to_csv(
        processed / "genotype_aware_folds.csv", index=False
    )

    pca_df = pd.DataFrame({"accession_id": model_accessions.astype(str)})
    for i in range(min(5, n_components)):
        pca_df[f"PC{i+1}"] = pcs[:, i]
    pca_df["fold"] = clusters
    pca_df.to_csv(results / "case_study_a_genomic_pca.csv", index=False)

    matrix_names = [name for name, _, _, _ in genotype_datasets]
    summary = {
        "phenotype_accessions": int(len(phenotype_ids)),
        "genomic_accessions": int(len(accession_ids)),
        "matched_accessions": int(len(model_accessions)),
        "p_raw": int(p_raw),
        "p_qc": int(p_qc),
        "p_ml": int(p_ml),
        "maf_threshold": 0.05,
        "max_marker_missingness": 0.10,
        "accession_dataset": accession_dataset,
        "matrix_datasets": matrix_names,
        "hdf5_file": h5_path.name,
        "archive_sha256": _sha256(archive),
        "n_validation_folds": int(n_folds),
        "accession_overlap_probe": int(n_overlap_probe),
        "relationship_matrix_markers": "all QC-passing markers",
        "ml_feature_policy": f"deterministic maximum {MAX_ML_MARKERS:,} QC markers",
    }
    pd.DataFrame([summary]).to_csv(results / "case_study_a_genomic_summary.csv", index=False)
    (results / "case_study_a_genomic_metadata.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(8.5, 6.0))
    ax.scatter(pcs[:, 0], pcs[:, 1], c=clusters, s=34, alpha=0.85)
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)")
    ax.set_title("Case Study A — Genomic structure of matched accessions")
    ax.grid(alpha=0.18)
    fig.tight_layout()
    fig.savefig(figures / "case_study_a_genomic_structure.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    print(json.dumps(summary, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    run(Path.cwd())
