from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize_scalar
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


LOG_DELTA_BOUNDS = (-12.0, 12.0)
BOUNDARY_TOL = 0.10


def predictive_correlation(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) < 3 or np.std(y_true) == 0 or np.std(y_pred) == 0:
        return float("nan")
    return float(np.corrcoef(y_true, y_pred)[0, 1])


def reml_profile_fit(y: np.ndarray, K: np.ndarray, jitter: float = 1e-8) -> dict:
    """Fit an intercept-only GBLUP variance ratio by one-dimensional profile REML.

    Parameterizing V = sigma_g^2 (K + delta I) makes the optimization numerically stable
    for small genotype-aware folds. The returned h2 is the genomic variance ratio under the
    scaling of K used by this repository; estimates at the search boundary are explicitly flagged.
    """
    y = np.asarray(y, dtype=float).reshape(-1, 1)
    K = np.asarray(K, dtype=float)
    n = len(y)
    if K.shape != (n, n):
        raise ValueError("K must be square and aligned with y.")
    if n < 3:
        raise ValueError("At least three observations are required for REML.")

    X = np.ones((n, 1), dtype=float)
    p = X.shape[1]

    def objective(log_delta: float) -> float:
        delta = float(np.exp(log_delta))
        H = K + (delta + jitter) * np.eye(n)
        try:
            cf = cho_factor(H, lower=True, check_finite=False)
            Hiy = cho_solve(cf, y, check_finite=False)
            HiX = cho_solve(cf, X, check_finite=False)
            XtHiX = X.T @ HiX
            beta = np.linalg.solve(XtHiX, X.T @ Hiy)
            residual = y - X @ beta
            Hires = cho_solve(cf, residual, check_finite=False)
            rss = float((residual.T @ Hires).item())
            sigma_g2 = max(rss / (n - p), 1e-12)
            logdet_H = float(2.0 * np.sum(np.log(np.diag(cf[0]))))
            sign, logdet_X = np.linalg.slogdet(XtHiX)
            if sign <= 0 or not np.isfinite(logdet_H):
                return float("inf")
            return float(
                0.5
                * (
                    (n - p) * (np.log(2.0 * np.pi * sigma_g2) + 1.0)
                    + logdet_H
                    + logdet_X
                )
            )
        except np.linalg.LinAlgError:
            return float("inf")

    opt = minimize_scalar(
        objective,
        bounds=LOG_DELTA_BOUNDS,
        method="bounded",
        options={"xatol": 1e-5},
    )
    if not opt.success or not np.isfinite(opt.fun):
        raise RuntimeError("Profile REML optimization failed.")

    log_delta = float(opt.x)
    delta = float(np.exp(log_delta))
    H = K + (delta + jitter) * np.eye(n)
    cf = cho_factor(H, lower=True, check_finite=False)
    Hiy = cho_solve(cf, y, check_finite=False)
    HiX = cho_solve(cf, X, check_finite=False)
    beta = float(np.linalg.solve(X.T @ HiX, X.T @ Hiy).item())
    residual = y - X * beta
    rss = float((residual.T @ cho_solve(cf, residual, check_finite=False)).item())
    sigma_g2 = max(rss / (n - p), 1e-12)
    sigma_e2 = delta * sigma_g2
    h2 = float(1.0 / (1.0 + delta))
    boundary = bool(
        abs(log_delta - LOG_DELTA_BOUNDS[0]) < BOUNDARY_TOL
        or abs(log_delta - LOG_DELTA_BOUNDS[1]) < BOUNDARY_TOL
    )
    return {
        "sigma_g2": float(sigma_g2),
        "sigma_e2": float(sigma_e2),
        "lambda": delta,
        "h2": h2,
        "intercept": beta,
        "log_delta": log_delta,
        "variance_boundary": boundary,
    }


def gblup_predict(
    y_train: np.ndarray,
    K_train: np.ndarray,
    K_test_train: np.ndarray,
) -> tuple[np.ndarray, dict]:
    fit = reml_profile_fit(y_train, K_train)
    mu = fit["intercept"]
    delta = fit["lambda"]
    A = K_train + (delta + 1e-8) * np.eye(len(y_train))
    alpha = cho_solve(
        cho_factor(A, lower=True, check_finite=False),
        np.asarray(y_train, dtype=float) - mu,
        check_finite=False,
    )
    prediction = mu + np.asarray(K_test_train, dtype=float) @ alpha
    return np.asarray(prediction, dtype=float), fit


def run(root: str | Path = ".") -> dict:
    root = Path(root).resolve()
    interim = root / "data" / "interim" / "case_study_a"
    processed = root / "data" / "processed" / "case_study_a"
    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)

    phenotype_path = interim / "shoot_regeneration_accession_summary.csv"
    accessions_path = processed / "model_accessions.csv"
    folds_path = processed / "genotype_aware_folds.csv"
    k_path = processed / "genomic_relationship_matrix.npy"
    for path in (phenotype_path, accessions_path, folds_path, k_path):
        if not path.exists():
            raise FileNotFoundError(f"Required Model 1 input is missing: {path}")

    phenotype = pd.read_csv(phenotype_path)
    accessions = pd.read_csv(accessions_path)
    folds = pd.read_csv(folds_path)
    K = np.load(k_path)

    phenotype["accession_id"] = phenotype["accession_id"].astype(str)
    accessions["accession_id"] = accessions["accession_id"].astype(str)
    folds["accession_id"] = folds["accession_id"].astype(str)
    model_accessions = accessions["accession_id"].tolist()
    fold_map = folds.set_index("accession_id")["fold"].to_dict()

    if K.shape != (len(model_accessions), len(model_accessions)):
        raise ValueError("Genomic relationship matrix is not aligned with model accessions.")
    if any(a not in fold_map for a in model_accessions):
        raise ValueError("At least one model accession is missing a genotype-aware fold.")

    targets = phenotype.pivot_table(
        index="accession_id",
        columns="phenotype_name",
        values="phenotype_mean",
        aggfunc="mean",
    ).reindex(model_accessions)
    fold_vector = np.asarray([fold_map[a] for a in model_accessions])

    fold_rows: list[dict] = []
    prediction_rows: list[dict] = []
    for target in targets.columns:
        y = targets[target].to_numpy(dtype=float)
        available = np.isfinite(y)
        if int(available.sum()) < 30:
            continue
        for fold in pd.unique(fold_vector[available]):
            test_idx = np.where(available & (fold_vector == fold))[0]
            train_idx = np.where(available & (fold_vector != fold))[0]
            if len(test_idx) == 0 or len(train_idx) < 20:
                continue
            pred, fit = gblup_predict(
                y[train_idx],
                K[np.ix_(train_idx, train_idx)],
                K[np.ix_(test_idx, train_idx)],
            )
            fold_rows.append(
                {
                    "target": target,
                    "fold": int(fold),
                    "n_train": int(len(train_idx)),
                    "n_test": int(len(test_idx)),
                    "rmse": float(np.sqrt(mean_squared_error(y[test_idx], pred))),
                    "mae": float(mean_absolute_error(y[test_idx], pred)),
                    "r2": float(r2_score(y[test_idx], pred)) if len(test_idx) > 1 else float("nan"),
                    "rho": predictive_correlation(y[test_idx], pred),
                    "sigma_g2": fit["sigma_g2"],
                    "sigma_e2": fit["sigma_e2"],
                    "lambda": fit["lambda"],
                    "h2": fit["h2"],
                    "variance_boundary": fit["variance_boundary"],
                }
            )
            prediction_rows.extend(
                {
                    "target": target,
                    "fold": int(fold),
                    "accession_id": model_accessions[i],
                    "observed": float(y[i]),
                    "predicted": float(p),
                }
                for i, p in zip(test_idx, pred)
            )

    fold_metrics = pd.DataFrame(fold_rows)
    predictions = pd.DataFrame(prediction_rows)
    if fold_metrics.empty or predictions.empty:
        raise RuntimeError("No valid GBLUP predictions were produced.")

    summary_rows: list[dict] = []
    for target, frame in predictions.groupby("target", sort=False):
        y_true = frame["observed"].to_numpy(dtype=float)
        y_pred = frame["predicted"].to_numpy(dtype=float)
        fm = fold_metrics[fold_metrics["target"] == target]
        summary_rows.append(
            {
                "target": target,
                "n_predictions": int(len(frame)),
                "n_folds": int(fm["fold"].nunique()),
                "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
                "mae": float(mean_absolute_error(y_true, y_pred)),
                "r2": float(r2_score(y_true, y_pred)),
                "rho": predictive_correlation(y_true, y_pred),
                "mean_h2": float(fm["h2"].mean()),
                "h2_sd": float(fm["h2"].std(ddof=1)),
                "boundary_folds": int(fm["variance_boundary"].sum()),
                "mean_fold_rmse": float(fm["rmse"].mean()),
                "sd_fold_rmse": float(fm["rmse"].std(ddof=1)),
            }
        )
    summary = pd.DataFrame(summary_rows)

    fold_metrics.to_csv(results / "case_study_a_gblup_fold_metrics.csv", index=False)
    predictions.to_csv(results / "case_study_a_gblup_predictions.csv", index=False)
    summary.to_csv(results / "case_study_a_gblup_summary.csv", index=False)
    metadata = {
        "model": "GBLUP",
        "variance_estimation": "profile REML within each training fold",
        "validation": "genotype-aware folds from genomic PCA/KMeans structure",
        "n_model_accessions": int(len(model_accessions)),
        "targets": list(summary["target"]),
        "variance_boundary_note": (
            "Boundary estimates are reported rather than hidden; they indicate weak variance-component "
            "identification and must not be interpreted as precise heritability estimates."
        ),
    }
    (results / "case_study_a_gblup_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(summary.to_string(index=False), flush=True)
    return {"summary": summary, "fold_metrics": fold_metrics, "predictions": predictions}


if __name__ == "__main__":
    run(Path.cwd())
