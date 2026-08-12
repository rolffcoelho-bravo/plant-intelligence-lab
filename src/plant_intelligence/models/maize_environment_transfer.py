"""Case Study B Step B6: genomic + continuous-environment transfer benchmark.

This module consumes the locked Genomes-to-Fields maize source and the frozen
B5 environment/genotype manifests.  It asks whether continuous environmental
information supports true cold-environment prediction.

The implementation is deliberately scalable.  The 98,026-marker genome is
compressed with a train-partition CountSketch followed by train-partition PCA,
which defines a low-rank approximation to a linear genomic kernel.  The 202
continuous environmental covariates are standardized on training environments
and mapped through an exact RBF environment kernel followed by a Nyström
feature map.  The row-wise tensor product of genomic and environmental feature
maps is therefore a low-rank feature map for the product kernel

    K_GE = K_G * K_E.

All outer validation manifests were frozen in Step B5 before this model was
implemented.  A common fixed ridge penalty is used across information-ablation
specifications so the first B6 experiment measures information value rather
than hyperparameter-search advantage.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import PCA
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from plant_intelligence.data.maize_environment_transfer import (
    SEED,
    _required_columns,
    acquire_source,
    load_source,
)

G_SKETCH_DIM = 192
G_PCA_DIM = 20
E_KERNEL_DIM = 16
MARKER_CHUNK = 2048
RIDGE_ALPHA = 10.0
BOOTSTRAP_REPS = 2000
MODEL_SPECS = ("Mean", "G", "E", "G+E", "G+E+GxE")


@dataclass(frozen=True)
class FeatureMap:
    ids: tuple[str, ...]
    values: np.ndarray
    metadata: dict[str, float | int | str]

    def lookup(self) -> dict[str, int]:
        return {value: i for i, value in enumerate(self.ids)}


def _safe_corr(y: np.ndarray, pred: np.ndarray) -> float:
    if len(y) < 2 or np.std(y) == 0.0 or np.std(pred) == 0.0:
        return float("nan")
    return float(np.corrcoef(y, pred)[0, 1])


def _metric_row(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    return {
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
        "mae": float(mean_absolute_error(y, pred)),
        "r2": float(r2_score(y, pred)),
        "correlation": _safe_corr(y, pred),
    }


def prepare_cells(
    pheno: pd.DataFrame,
    geno: pd.DataFrame,
    ecov: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    genotype_col, environment_col, trait_col = _required_columns(pheno)
    geno_id_col = str(geno.columns[0])
    work = pheno[[genotype_col, environment_col, trait_col]].copy()
    work.columns = ["genotype", "environment", "yield"]
    work["genotype"] = work["genotype"].astype(str)
    work["environment"] = work["environment"].astype(str)
    work["yield"] = pd.to_numeric(work["yield"], errors="coerce")
    work = work.dropna(subset=["yield"])

    geno_ids = set(geno[geno_id_col].astype(str))
    env_ids = set(ecov.index.astype(str))
    work = work[work["genotype"].isin(geno_ids) & work["environment"].isin(env_ids)]
    # Genotype-environment mean is the forecasting unit; replicate plot rows are
    # not treated as independent genomic/environmental deployments.
    cells = (
        work.groupby(["genotype", "environment"], as_index=False)
        .agg(observed=("yield", "mean"), n_records=("yield", "size"))
    )
    if cells.empty:
        raise ValueError("No genotype-environment cells remain after source intersection.")
    ecov_numeric = ecov.apply(pd.to_numeric, errors="coerce")
    if ecov_numeric.isna().any().any():
        raise ValueError("B5 locked environmental covariates are expected to be complete.")
    columns = {
        "geno_id": geno_id_col,
        "genotype": genotype_col,
        "environment": environment_col,
        "trait": trait_col,
    }
    return cells, geno, ecov_numeric, columns


def _countsketch_assignments(n_markers: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(SEED)
    buckets = rng.integers(0, G_SKETCH_DIM, size=n_markers, dtype=np.int32)
    signs = rng.choice(np.asarray([-1.0, 1.0], dtype=np.float32), size=n_markers)
    return buckets, signs.astype(np.float32)


def genomic_feature_map(
    geno: pd.DataFrame,
    geno_id_col: str,
    training_ids: set[str],
) -> FeatureMap:
    ids = tuple(geno[geno_id_col].astype(str).tolist())
    id_to_row = {gid: i for i, gid in enumerate(ids)}
    train_rows = np.asarray([id_to_row[g] for g in sorted(training_ids) if g in id_to_row], dtype=int)
    if len(train_rows) < G_PCA_DIM + 2:
        raise ValueError("Too few training genotypes for the genomic feature map.")

    n_markers = geno.shape[1] - 1
    buckets, signs = _countsketch_assignments(n_markers)
    sketch = np.zeros((len(ids), G_SKETCH_DIM), dtype=np.float32)

    for start in range(0, n_markers, MARKER_CHUNK):
        stop = min(start + MARKER_CHUNK, n_markers)
        block = geno.iloc[:, 1 + start : 1 + stop].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float32)
        train_block = block[train_rows]
        means = np.nanmean(train_block, axis=0)
        stds = np.nanstd(train_block, axis=0)
        means = np.where(np.isfinite(means), means, 0.0).astype(np.float32)
        stds = np.where(np.isfinite(stds) & (stds > 1e-6), stds, 1.0).astype(np.float32)
        missing = ~np.isfinite(block)
        if missing.any():
            row_idx, col_idx = np.where(missing)
            block[row_idx, col_idx] = means[col_idx]
        block = (block - means) / stds
        local_buckets = buckets[start:stop]
        local_signs = signs[start:stop]
        projection = csr_matrix(
            (local_signs, (np.arange(stop - start), local_buckets)),
            shape=(stop - start, G_SKETCH_DIM),
            dtype=np.float32,
        )
        sketch += np.asarray(block @ projection, dtype=np.float32)

    scaler = StandardScaler().fit(sketch[train_rows])
    z = scaler.transform(sketch).astype(np.float32)
    n_components = min(G_PCA_DIM, len(train_rows) - 1, G_SKETCH_DIM)
    pca = PCA(n_components=n_components, random_state=SEED).fit(z[train_rows])
    values = pca.transform(z).astype(np.float32)
    values /= np.sqrt(max(1, values.shape[1]))
    return FeatureMap(
        ids=ids,
        values=values,
        metadata={
            "kind": "countsketch+pca_linear_genomic_kernel",
            "n_train_entities": int(len(train_rows)),
            "input_markers": int(n_markers),
            "sketch_dim": int(G_SKETCH_DIM),
            "feature_dim": int(values.shape[1]),
            "pca_explained_variance": float(np.sum(pca.explained_variance_ratio_)),
        },
    )


def _sqeuclidean(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aa = np.sum(a * a, axis=1)[:, None]
    bb = np.sum(b * b, axis=1)[None, :]
    return np.maximum(aa + bb - 2.0 * (a @ b.T), 0.0)


def environment_feature_map(ecov: pd.DataFrame, training_ids: set[str]) -> FeatureMap:
    ids = tuple(ecov.index.astype(str).tolist())
    id_to_row = {eid: i for i, eid in enumerate(ids)}
    train_rows = np.asarray([id_to_row[e] for e in sorted(training_ids) if e in id_to_row], dtype=int)
    if len(train_rows) < E_KERNEL_DIM + 2:
        raise ValueError("Too few training environments for environmental kernel construction.")

    x = ecov.to_numpy(dtype=np.float64)
    scaler = StandardScaler().fit(x[train_rows])
    z = scaler.transform(x)
    train_z = z[train_rows]
    d2_train = _sqeuclidean(train_z, train_z)
    upper = d2_train[np.triu_indices_from(d2_train, k=1)]
    positive = upper[upper > 1e-12]
    median_d2 = float(np.median(positive)) if len(positive) else 1.0
    gamma = 1.0 / max(median_d2, 1e-12)
    k_train = np.exp(-gamma * d2_train)
    evals, evecs = np.linalg.eigh(k_train)
    order = np.argsort(evals)[::-1]
    evals = evals[order]
    evecs = evecs[:, order]
    keep = min(E_KERNEL_DIM, int(np.sum(evals > 1e-10)))
    evals = evals[:keep]
    evecs = evecs[:, :keep]
    k_all_train = np.exp(-gamma * _sqeuclidean(z, train_z))
    values = (k_all_train @ (evecs / np.sqrt(evals)[None, :])).astype(np.float32)
    values /= np.sqrt(max(1, values.shape[1]))
    return FeatureMap(
        ids=ids,
        values=values,
        metadata={
            "kind": "rbf_environment_kernel_nystrom",
            "n_train_entities": int(len(train_rows)),
            "input_covariates": int(ecov.shape[1]),
            "feature_dim": int(values.shape[1]),
            "rbf_gamma": float(gamma),
            "retained_kernel_eigenvalue_fraction": float(np.sum(evals) / np.trace(k_train)),
        },
    )


def tensor_features(g: np.ndarray, e: np.ndarray) -> np.ndarray:
    if len(g) != len(e):
        raise ValueError("Genomic and environmental feature rows must align.")
    return (g[:, :, None] * e[:, None, :]).reshape(len(g), -1).astype(np.float32)


def _cell_features(cells: pd.DataFrame, gmap: FeatureMap, emap: FeatureMap) -> tuple[np.ndarray, np.ndarray]:
    gi = gmap.lookup()
    ei = emap.lookup()
    g = np.vstack([gmap.values[gi[str(value)]] for value in cells["genotype"]]).astype(np.float32)
    e = np.vstack([emap.values[ei[str(value)]] for value in cells["environment"]]).astype(np.float32)
    return g, e


def _fit_predict(spec: str, train_g: np.ndarray, train_e: np.ndarray, y: np.ndarray, test_g: np.ndarray, test_e: np.ndarray) -> np.ndarray:
    if spec == "Mean":
        model = DummyRegressor(strategy="mean").fit(np.zeros((len(y), 1)), y)
        return model.predict(np.zeros((len(test_g), 1)))
    if spec == "G":
        x_train, x_test = train_g, test_g
    elif spec == "E":
        x_train, x_test = train_e, test_e
    elif spec == "G+E":
        x_train = np.hstack([train_g, train_e])
        x_test = np.hstack([test_g, test_e])
    elif spec == "G+E+GxE":
        x_train = np.hstack([train_g, train_e, tensor_features(train_g, train_e)])
        x_test = np.hstack([test_g, test_e, tensor_features(test_g, test_e)])
    else:
        raise ValueError(f"Unknown model specification: {spec}")
    scaler = StandardScaler().fit(x_train)
    x_train = scaler.transform(x_train)
    x_test = scaler.transform(x_test)
    model = Ridge(alpha=RIDGE_ALPHA, solver="lsqr", fit_intercept=True).fit(x_train, y)
    return model.predict(x_test)


def _load_manifests(results: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    env_path = results / "case_study_b5_environment_transfer_folds.csv"
    geno_path = results / "case_study_b5_genotype_transfer_folds.csv"
    if not env_path.exists() or not geno_path.exists():
        raise FileNotFoundError("Step B5 frozen transfer manifests are required before B6.")
    env = pd.read_csv(env_path)
    geno = pd.read_csv(geno_path)
    return env, geno


def _attach_folds(cells: pd.DataFrame, env_manifest: pd.DataFrame, geno_manifest: pd.DataFrame) -> pd.DataFrame:
    env_map = env_manifest.set_index("environment")["environment_fold"].astype(int).to_dict()
    geno_map = geno_manifest.set_index("genotype")["genotype_fold"].astype(int).to_dict()
    out = cells.copy()
    out["environment_fold"] = out["environment"].map(env_map)
    out["genotype_fold"] = out["genotype"].map(geno_map)
    if out[["environment_fold", "genotype_fold"]].isna().any().any():
        raise ValueError("Frozen B5 manifests do not cover all modeled cells.")
    out["environment_fold"] = out["environment_fold"].astype(int)
    out["genotype_fold"] = out["genotype_fold"].astype(int)
    return out


def run_benchmark(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    results = root / "reports" / "results"
    paths, _ = acquire_source(root)
    pheno, geno, ecov = load_source(paths)
    cells, geno, ecov, columns = prepare_cells(pheno, geno, ecov)
    env_manifest, geno_manifest = _load_manifests(results)
    cells = _attach_folds(cells, env_manifest, geno_manifest)

    prediction_rows: list[pd.DataFrame] = []
    audit_rows: list[dict[str, object]] = []

    # Primary environment cold start: every held-out environment has a measured
    # EC vector.  Genomic preprocessing uses only genotypes occurring in the
    # phenotype training partition for that outer fold.
    for efold in sorted(env_manifest["environment_fold"].unique()):
        train = cells[cells["environment_fold"] != efold].copy()
        test = cells[cells["environment_fold"] == efold].copy()
        gmap = genomic_feature_map(geno, columns["geno_id"], set(train["genotype"]))
        emap = environment_feature_map(ecov, set(train["environment"]))
        train_g, train_e = _cell_features(train, gmap, emap)
        test_g, test_e = _cell_features(test, gmap, emap)
        y = train["observed"].to_numpy(float)
        for spec in MODEL_SPECS:
            pred = _fit_predict(spec, train_g, train_e, y, test_g, test_e)
            frame = test[["genotype", "environment", "observed", "environment_fold", "genotype_fold"]].copy()
            frame["regime"] = "CV-E-continuous"
            frame["scenario"] = f"efold_{efold}"
            frame["model"] = spec
            frame["predicted"] = pred
            prediction_rows.append(frame)
        audit_rows.append({"regime": "CV-E-continuous", "scenario": f"efold_{efold}", **{f"G_{k}": v for k, v in gmap.metadata.items()}, **{f"E_{k}": v for k, v in emap.metadata.items()}, "n_train_cells": len(train), "n_test_cells": len(test)})

    # Strict double cold start: the test cell must have both a held-out
    # environment and a held-out genotype.  Each observed cell belongs to one
    # of the 25 crossed scenarios, so pooled strict predictions remain OOF.
    strict_gmaps: dict[int, FeatureMap] = {}
    for gfold in sorted(geno_manifest["genotype_fold"].unique()):
        train_ids = set(geno_manifest.loc[geno_manifest["genotype_fold"] != gfold, "genotype"].astype(str))
        strict_gmaps[int(gfold)] = genomic_feature_map(geno, columns["geno_id"], train_ids)
    strict_emaps: dict[int, FeatureMap] = {}
    for efold in sorted(env_manifest["environment_fold"].unique()):
        train_envs = set(env_manifest.loc[env_manifest["environment_fold"] != efold, "environment"].astype(str))
        strict_emaps[int(efold)] = environment_feature_map(ecov, train_envs)

    for efold in sorted(env_manifest["environment_fold"].unique()):
        for gfold in sorted(geno_manifest["genotype_fold"].unique()):
            train = cells[(cells["environment_fold"] != efold) & (cells["genotype_fold"] != gfold)].copy()
            test = cells[(cells["environment_fold"] == efold) & (cells["genotype_fold"] == gfold)].copy()
            if test.empty:
                continue
            gmap = strict_gmaps[int(gfold)]
            emap = strict_emaps[int(efold)]
            train_g, train_e = _cell_features(train, gmap, emap)
            test_g, test_e = _cell_features(test, gmap, emap)
            y = train["observed"].to_numpy(float)
            scenario = f"efold_{efold}__gfold_{gfold}"
            for spec in MODEL_SPECS:
                pred = _fit_predict(spec, train_g, train_e, y, test_g, test_e)
                frame = test[["genotype", "environment", "observed", "environment_fold", "genotype_fold"]].copy()
                frame["regime"] = "CV-GE-continuous"
                frame["scenario"] = scenario
                frame["model"] = spec
                frame["predicted"] = pred
                prediction_rows.append(frame)
            audit_rows.append({"regime": "CV-GE-continuous", "scenario": scenario, **{f"G_{k}": v for k, v in gmap.metadata.items()}, **{f"E_{k}": v for k, v in emap.metadata.items()}, "n_train_cells": len(train), "n_test_cells": len(test)})

    predictions = pd.concat(prediction_rows, ignore_index=True)
    audit = pd.DataFrame(audit_rows)
    fold_metrics = []
    for (regime, scenario, model), part in predictions.groupby(["regime", "scenario", "model"]):
        metrics = _metric_row(part["observed"].to_numpy(float), part["predicted"].to_numpy(float))
        fold_metrics.append({"regime": regime, "scenario": scenario, "model": model, "n": len(part), **metrics})
    return predictions, pd.DataFrame(fold_metrics), audit


def pooled_summary(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (regime, model), part in predictions.groupby(["regime", "model"]):
        metrics = _metric_row(part["observed"].to_numpy(float), part["predicted"].to_numpy(float))
        rows.append({"regime": regime, "model": model, "n": len(part), **metrics})
    return pd.DataFrame(rows).sort_values(["regime", "rmse"]).reset_index(drop=True)


def paired_environment_bootstrap(predictions: pd.DataFrame, reps: int = BOOTSTRAP_REPS) -> pd.DataFrame:
    comparisons = (("G+E", "G"), ("G+E+GxE", "G+E"), ("G+E+GxE", "G"))
    rng = np.random.default_rng(SEED)
    rows: list[dict[str, object]] = []
    for regime, part in predictions.groupby("regime"):
        pivot = part.pivot_table(index=["genotype", "environment", "observed"], columns="model", values="predicted", aggfunc="first").reset_index()
        envs = np.asarray(sorted(pivot["environment"].unique()))
        for challenger, reference in comparisons:
            sq_ch = (pivot["observed"] - pivot[challenger]) ** 2
            sq_ref = (pivot["observed"] - pivot[reference]) ** 2
            stats = pd.DataFrame({"environment": pivot["environment"], "sq_ch": sq_ch, "sq_ref": sq_ref}).groupby("environment").agg(sum_ch=("sq_ch", "sum"), sum_ref=("sq_ref", "sum"), n=("sq_ch", "size"))
            observed_delta = float(np.sqrt(sq_ch.mean()) - np.sqrt(sq_ref.mean()))
            deltas = np.empty(reps, dtype=float)
            for b in range(reps):
                sampled = rng.choice(envs, size=len(envs), replace=True)
                sampled_stats = stats.loc[sampled]
                n = sampled_stats["n"].sum()
                deltas[b] = np.sqrt(sampled_stats["sum_ch"].sum() / n) - np.sqrt(sampled_stats["sum_ref"].sum() / n)
            rows.append({
                "regime": regime,
                "challenger": challenger,
                "reference": reference,
                "metric": "RMSE",
                "delta_challenger_minus_reference": observed_delta,
                "ci95_low": float(np.quantile(deltas, 0.025)),
                "ci95_high": float(np.quantile(deltas, 0.975)),
                "improvement_frequency": float(np.mean(deltas < 0.0)),
                "bootstrap_clusters": "environment",
                "bootstrap_reps": int(reps),
            })
    return pd.DataFrame(rows)


def make_figure(summary: pd.DataFrame, path: Path) -> None:
    order = list(MODEL_SPECS)
    regimes = [r for r in ("CV-E-continuous", "CV-GE-continuous") if r in set(summary["regime"])]
    x = np.arange(len(regimes), dtype=float)
    width = 0.14
    fig, ax = plt.subplots(figsize=(12.5, 6.2))
    for j, model in enumerate(order):
        values = []
        for regime in regimes:
            row = summary[(summary["regime"] == regime) & (summary["model"] == model)]
            values.append(float(row.iloc[0]["rmse"]) if len(row) else np.nan)
        bars = ax.bar(x + (j - (len(order) - 1) / 2) * width, values, width, label=model)
        ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    ax.set_xticks(x, ["Unseen environment", "Unseen genotype + environment"][: len(regimes)])
    ax.set_ylabel("RMSE")
    ax.set_title("Case Study B6 — continuous-environment transfer information ablation")
    ax.grid(axis="y", alpha=0.22)
    fig.legend(loc="lower center", ncol=len(order), frameon=False, bbox_to_anchor=(0.5, 0.01))
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def run(output_root: Path) -> dict[str, Path]:
    root = output_root.resolve()
    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    results.mkdir(parents=True, exist_ok=True)
    predictions, fold_metrics, audit = run_benchmark(root)
    summary = pooled_summary(predictions)
    bootstrap = paired_environment_bootstrap(predictions)

    outputs = {
        "summary": results / "case_study_b6_transfer_summary.csv",
        "fold_metrics": results / "case_study_b6_transfer_fold_metrics.csv",
        "bootstrap": results / "case_study_b6_transfer_bootstrap.csv",
        "feature_audit": results / "case_study_b6_feature_audit.csv",
        "figure": figures / "case_study_b6_environment_transfer.png",
    }
    summary.to_csv(outputs["summary"], index=False)
    fold_metrics.to_csv(outputs["fold_metrics"], index=False)
    bootstrap.to_csv(outputs["bootstrap"], index=False)
    audit.to_csv(outputs["feature_audit"], index=False)
    make_figure(summary, outputs["figure"])
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Case Study B6 continuous-environment transfer benchmark.")
    parser.add_argument("--output-root", default=".")
    args = parser.parse_args()
    outputs = run(Path(args.output_root))
    print("Case Study B Step B6 continuous-environment transfer benchmark complete")
    for key, value in outputs.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
