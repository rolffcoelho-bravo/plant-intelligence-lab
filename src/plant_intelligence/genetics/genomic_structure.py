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


def _load_genomewide_snps(
    h5_path: Path,
    inventory: pd.DataFrame,
    accession_count: int,
) -> tuple[np.ndarray, list[str]]:
    numeric = inventory[
        (inventory["ndim"] == 2)
        & inventory["dtype"].str.contains(r"int|float|bool", case=False, regex=True)
    ].copy()

    datasets = []
    for _, row in numeric.iterrows():
        shape = tuple(row["shape"])
        if accession_count not in shape:
            continue
        other_dim = shape[1] if shape[0] == accession_count else shape[0]
        if other_dim < 1000:
            continue
        name = str(row["name"])
        # The official archive commonly stores chromosomes as separate SNP arrays.
        # Prefer arrays whose names explicitly identify SNP/genotype content.
        score = int("snp" in name.lower()) + int("geno" in name.lower())
        datasets.append((score, other_dim, name, shape))

    if not datasets:
        raise RuntimeError("No genome-scale SNP matrices matched the accession dimension.")

    max_score = max(x[0] for x in datasets)
    if max_score > 0:
        datasets = [x for x in datasets if x[0] == max_score]

    # If one matrix is essentially the whole genome and dwarfs all others, use it.
    datasets.sort(key=lambda x: x[1], reverse=True)
    if len(datasets) > 1 and datasets[0][1] >= 0.9 * sum(x[1] for x in datasets):
        datasets = [datasets[0]]

    arrays = []
    names = []
    with h5py.File(h5_path, "r") as h5:
        for _, _, name, _ in datasets:
            arr = np.asarray(h5[name])
            if arr.shape[0] != accession_count:
                arr = arr.T
            if arr.shape[0] != accession_count:
                raise RuntimeError(f"Dataset {name} could not be oriented by accession.")
            arrays.append(arr)
            names.append(name)

    return np.concatenate(arrays, axis=1), names


def run(root: str | Path = ".") -> dict:
    root = Path(root).resolve()
    interim = root / "data" / "interim" / "case_study_a"
    processed = root / "data" / "processed" / "case_study_a"
    genomic_raw = root / "data" / "raw" / "1001genomes" / "1135"
    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    for p in (interim, processed, genomic_raw, results, figures):
        p.mkdir(parents=True, exist_ok=True)

    phenotype_path = interim / "shoot_regeneration_accession_summary.csv"
    if not phenotype_path.exists():
        raise FileNotFoundError("Run Notebook 01 first: phenotype summary is missing.")
    phenotype = pd.read_csv(phenotype_path)
    phenotype["accession_id"] = phenotype["accession_id"].astype(str)
    phenotype_ids = set(phenotype["accession_id"].dropna().unique())

    archive = genomic_raw / "1001_SNP_MATRIX.tar.gz"
    if not archive.exists():
        print("Downloading official 1001 Genomes SNP matrix...")
        urllib.request.urlretrieve(SNP_ARCHIVE_URL, archive)

    extract_dir = genomic_raw / "SNP_matrix_imputed_hdf5"
    extract_dir.mkdir(parents=True, exist_ok=True)
    h5_candidates = list(extract_dir.rglob("*.h5")) + list(extract_dir.rglob("*.hdf5"))
    if not h5_candidates:
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(extract_dir)
        h5_candidates = list(extract_dir.rglob("*.h5")) + list(extract_dir.rglob("*.hdf5"))
    if not h5_candidates:
        raise FileNotFoundError("No HDF5 file was found in the official SNP archive.")

    # Prefer the canonical imputed SNP file when present.
    h5_path = next((p for p in h5_candidates if p.name == "imputed_snps_binary.hdf5"), h5_candidates[0])
    inventory = _inventory_hdf5(h5_path)
    inventory.to_csv(results / "case_study_a_hdf5_inventory.csv", index=False)

    accession_dataset, accession_ids, n_overlap_probe = _choose_accession_vector(
        h5_path, inventory, phenotype_ids
    )
    G, matrix_datasets = _load_genomewide_snps(h5_path, inventory, len(accession_ids))

    genomic_ids = pd.Index(accession_ids.astype(str))
    model_accessions = pd.Index(sorted(phenotype_ids)).intersection(genomic_ids)
    if len(model_accessions) < 30:
        raise RuntimeError(f"Only {len(model_accessions)} phenotype accessions matched genomic accessions.")

    row_map = {str(a): i for i, a in enumerate(accession_ids)}
    rows = np.array([row_map[str(a)] for a in model_accessions], dtype=int)
    G_model = np.asarray(G[rows, :], dtype=float)
    p_raw = int(G_model.shape[1])

    # Imputed matrix should have no missing values, but keep transparent safeguards.
    G_model[G_model < 0] = np.nan
    missing_rate = np.mean(np.isnan(G_model), axis=0)
    keep = missing_rate <= 0.10
    G_qc = G_model[:, keep]
    means = np.nanmean(G_qc, axis=0)
    rr, cc = np.where(np.isnan(G_qc))
    if len(rr):
        G_qc[rr, cc] = means[cc]

    allele_freq = np.mean(G_qc, axis=0) / 2.0
    maf = np.minimum(allele_freq, 1.0 - allele_freq)
    variable = np.nanstd(G_qc, axis=0) > 0
    keep2 = variable & (maf >= 0.05)
    G_qc = G_qc[:, keep2]
    p_qc = int(G_qc.shape[1])
    if p_qc < 100:
        raise RuntimeError(f"Marker QC retained only {p_qc} markers.")

    p = np.mean(G_qc, axis=0) / 2.0
    M = G_qc - 2.0 * p
    denom = 2.0 * np.sum(p * (1.0 - p))
    if denom <= 0:
        raise RuntimeError("Genomic relationship matrix denominator is non-positive.")
    K = (M @ M.T) / denom
    K = (K + K.T) / 2.0

    np.save(processed / "genomic_relationship_matrix.npy", K)
    np.save(processed / "genotype_matrix_qc.npy", G_qc.astype(np.float32))
    pd.DataFrame({"accession_id": model_accessions.astype(str)}).to_csv(
        processed / "model_accessions.csv", index=False
    )

    n_components = min(10, len(model_accessions) - 1, G_qc.shape[1])
    pca = PCA(n_components=n_components, random_state=42)
    pcs = pca.fit_transform(G_qc)
    n_folds = min(5, max(3, len(model_accessions) // 30))
    clusters = KMeans(n_clusters=n_folds, random_state=42, n_init=20).fit_predict(pcs[:, : min(5, n_components)])
    fold_df = pd.DataFrame({"accession_id": model_accessions.astype(str), "fold": clusters})
    fold_df.to_csv(processed / "genotype_aware_folds.csv", index=False)

    pca_df = pd.DataFrame({"accession_id": model_accessions.astype(str)})
    for i in range(min(5, n_components)):
        pca_df[f"PC{i+1}"] = pcs[:, i]
    pca_df["fold"] = clusters
    pca_df.to_csv(results / "case_study_a_genomic_pca.csv", index=False)

    summary = {
        "phenotype_accessions": int(len(phenotype_ids)),
        "genomic_accessions": int(len(accession_ids)),
        "matched_accessions": int(len(model_accessions)),
        "p_raw": p_raw,
        "p_qc": p_qc,
        "maf_threshold": 0.05,
        "max_marker_missingness": 0.10,
        "accession_dataset": accession_dataset,
        "matrix_datasets": matrix_datasets,
        "hdf5_file": h5_path.name,
        "archive_sha256": _sha256(archive),
        "n_validation_folds": int(n_folds),
        "accession_overlap_probe": int(n_overlap_probe),
    }
    pd.DataFrame([summary]).to_csv(results / "case_study_a_genomic_summary.csv", index=False)
    (results / "case_study_a_genomic_metadata.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(8.5, 6.0))
    scatter = ax.scatter(pcs[:, 0], pcs[:, 1], c=clusters, s=34, alpha=0.85)
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)")
    ax.set_title("Case Study A — Genomic structure of matched accessions")
    ax.grid(alpha=0.18)
    fig.tight_layout()
    fig.savefig(figures / "case_study_a_genomic_structure.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    run(Path.cwd())
