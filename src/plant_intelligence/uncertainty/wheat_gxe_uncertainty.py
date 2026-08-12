"""Case Study B Step B4: uncertainty, reliability, and deployment-boundary diagnostics.

The analysis consumes the frozen out-of-sample classical champions rather than
refitting a new predictive model:

* CV-G: normalized GxE-mixture predictions from Step B2-R;
* CV2: pre-registered G+E+GxE predictions from Step B2.

Prediction intervals use environment-specific cross-fitted residual calibration.
No arbitrary operational abstention threshold is imposed inside the supported
CV-G/CV2 regimes. Instead, selective-risk curves quantify whether uncertainty
or genomic-support diagnostics actually concentrate forecast error. CV-E and
CV-GE are encoded as unsupported-environment deployment states because the
source data provide only categorical environment identifiers.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler

from plant_intelligence.data.wheat_gxe import load_locked_matrices

COVERAGES = (0.80, 0.90, 0.95)
CV_G_MODEL = "G+E+normalized-GxE-mixture"
CV2_MODEL = "G+E+GxE"
CALIBRATION_FOLDS = 5
SEED = 20260812


def finite_sample_quantile(residuals: np.ndarray, coverage: float) -> float:
    """Finite-sample split-conformal absolute-residual quantile."""
    values = np.sort(np.asarray(residuals, dtype=float))
    if len(values) == 0:
        raise ValueError("Residual calibration requires at least one residual.")
    if not (0.0 < coverage < 1.0):
        raise ValueError("Coverage must lie strictly between zero and one.")
    rank = int(np.ceil((len(values) + 1) * coverage))
    rank = min(max(rank, 1), len(values))
    return float(values[rank - 1])


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{label} is missing required columns: {sorted(missing)}")


def load_frozen_predictions(root: Path) -> pd.DataFrame:
    """Load the strongest already-observed classical prediction source per regime."""
    results = root / "reports" / "results"
    cvg_path = results / "case_study_b_gxe_mixture_predictions.csv"
    cv2_path = results / "case_study_b_model_predictions.csv"
    if not cvg_path.exists() or not cv2_path.exists():
        raise FileNotFoundError("Frozen Case Study B prediction files are required before Step B4.")

    cvg = pd.read_csv(cvg_path)
    cv2 = pd.read_csv(cv2_path)
    required = {"regime", "scenario", "model", "genotype_id", "environment", "observed", "predicted"}
    _require_columns(cvg, required, "B2-R predictions")
    _require_columns(cv2, required, "B2 predictions")

    cvg = cvg[(cvg["regime"] == "CV-G") & (cvg["model"] == CV_G_MODEL)].copy()
    cv2 = cv2[(cv2["regime"] == "CV2") & (cv2["model"] == CV2_MODEL)].copy()
    if cvg.empty or cv2.empty:
        raise ValueError("Could not resolve the frozen CV-G/CV2 classical champions.")

    # CV-G calibration folds are the locked outer genotype folds. CV2 has one
    # outer sparse-cell fit, so create deterministic genotype-only calibration
    # folds solely for residual cross-fitting; this never changes model fitting.
    cvg["calibration_fold"] = cvg["scenario"].astype(str)
    genotype_order = {gid: i for i, gid in enumerate(sorted(cv2["genotype_id"].astype(str).unique()))}
    cv2["calibration_fold"] = cv2["genotype_id"].astype(str).map(
        lambda gid: f"cal_{genotype_order[gid] % CALIBRATION_FOLDS}"
    )
    out = pd.concat([cvg, cv2], ignore_index=True)
    out["abs_error"] = np.abs(out["observed"].to_numpy(float) - out["predicted"].to_numpy(float))
    return out


def calibrate_intervals(predictions: pd.DataFrame) -> pd.DataFrame:
    """Cross-fit environment-specific residual intervals for every OOF prediction."""
    required = {
        "regime", "environment", "calibration_fold", "observed", "predicted", "abs_error"
    }
    _require_columns(predictions, required, "frozen predictions")
    rows: list[dict[str, object]] = []
    for row in predictions.itertuples(index=False):
        pool = predictions[
            (predictions["regime"] == row.regime)
            & (predictions["environment"] == row.environment)
            & (predictions["calibration_fold"] != row.calibration_fold)
        ]
        if len(pool) < 30:
            pool = predictions[
                (predictions["regime"] == row.regime)
                & (predictions["calibration_fold"] != row.calibration_fold)
            ]
        if len(pool) < 30:
            raise ValueError("Insufficient cross-fitted calibration residuals.")
        record = row._asdict()
        record["calibration_n"] = int(len(pool))
        for coverage in COVERAGES:
            label = int(round(coverage * 100))
            q = finite_sample_quantile(pool["abs_error"].to_numpy(float), coverage)
            record[f"q_{label}"] = q
            record[f"lower_{label}"] = float(row.predicted - q)
            record[f"upper_{label}"] = float(row.predicted + q)
            record[f"covered_{label}"] = bool(abs(float(row.observed) - float(row.predicted)) <= q)
            record[f"width_{label}"] = float(2.0 * q)
        rows.append(record)
    return pd.DataFrame(rows)


def coverage_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    scopes = [("pooled", frame)]
    scopes.extend((f"environment_{env}", part) for env, part in frame.groupby("environment"))
    for regime, regime_frame in frame.groupby("regime"):
        for scope, part0 in scopes:
            part = part0[part0["regime"] == regime]
            if part.empty:
                continue
            for coverage in COVERAGES:
                label = int(round(coverage * 100))
                rows.append(
                    {
                        "regime": regime,
                        "scope": scope,
                        "nominal_coverage": coverage,
                        "empirical_coverage": float(part[f"covered_{label}"].mean()),
                        "mean_width": float(part[f"width_{label}"].mean()),
                        "median_width": float(part[f"width_{label}"].median()),
                        "n": int(len(part)),
                    }
                )
    return pd.DataFrame(rows)


def genomic_support_distance(
    frame: pd.DataFrame,
    geno: pd.DataFrame,
    cv_g_folds: pd.DataFrame,
) -> pd.DataFrame:
    """Attach train-only PCA nearest-neighbor genomic support for CV-G.

    CV2 genotypes are observed in the training partition through their other
    environments, so their support state is explicitly recorded as seen-genotype
    rather than assigning an artificial nonzero distance.
    """
    out = frame.copy()
    out["genotype_seen_in_training"] = out["regime"].eq("CV2")
    out["genomic_support_distance"] = 0.0

    fold_map = cv_g_folds.set_index("genotype_id")["fold"].astype(int).to_dict()
    all_ids = geno.index.astype(str)
    for scenario, part in out[out["regime"] == "CV-G"].groupby("scenario"):
        fold = int(str(scenario).split("_")[-1])
        test_ids = sorted(part["genotype_id"].astype(str).unique())
        train_ids = [gid for gid in all_ids if fold_map[str(gid)] != fold]
        x_train = geno.loc[train_ids].to_numpy(float)
        x_test = geno.loc[test_ids].to_numpy(float)
        scaler = StandardScaler().fit(x_train)
        z_train = scaler.transform(x_train)
        z_test = scaler.transform(x_test)
        n_components = min(20, z_train.shape[0] - 1, z_train.shape[1])
        pca = PCA(n_components=n_components, random_state=SEED).fit(z_train)
        train_pc = pca.transform(z_train)
        test_pc = pca.transform(z_test)
        # 120 x 479 x <=20 per fold: small and exact.
        distances = np.sqrt(((test_pc[:, None, :] - train_pc[None, :, :]) ** 2).sum(axis=2))
        nearest = distances.min(axis=1)
        distance_map = dict(zip(test_ids, nearest))
        mask = (out["regime"] == "CV-G") & (out["scenario"] == scenario)
        out.loc[mask, "genomic_support_distance"] = out.loc[mask, "genotype_id"].astype(str).map(distance_map)
    return out


def support_diagnostics(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for regime, part in frame.groupby("regime"):
        signals = ["width_90"]
        if regime == "CV-G":
            signals.append("genomic_support_distance")
        for signal in signals:
            x = part[signal].to_numpy(float)
            y = part["abs_error"].to_numpy(float)
            rho, pvalue = spearmanr(x, y)
            rows.append(
                {
                    "regime": regime,
                    "signal": signal,
                    "n": int(len(part)),
                    "spearman_rho_abs_error": float(rho),
                    "p_value": float(pvalue),
                }
            )
    return pd.DataFrame(rows)


def _percentile_rank(values: pd.Series) -> pd.Series:
    return values.rank(method="average", pct=True)


def selective_risk(frame: pd.DataFrame) -> pd.DataFrame:
    """Quantify selective risk without choosing an arbitrary deployment cutoff."""
    rows: list[dict[str, object]] = []
    for regime, part0 in frame.groupby("regime"):
        part = part0.copy()
        risk = _percentile_rank(part["width_90"])
        if regime == "CV-G":
            risk = 0.5 * risk + 0.5 * _percentile_rank(part["genomic_support_distance"])
        part["risk_score"] = risk
        for removed_fraction in (0.0, 0.05, 0.10, 0.20):
            if removed_fraction == 0.0:
                retained = part
            else:
                cutoff = float(part["risk_score"].quantile(1.0 - removed_fraction))
                retained = part[part["risk_score"] < cutoff]
                if retained.empty:
                    retained = part.nsmallest(max(1, int(round(len(part) * (1.0 - removed_fraction)))), "risk_score")
            rows.append(
                {
                    "regime": regime,
                    "removed_fraction_target": removed_fraction,
                    "retained_n": int(len(retained)),
                    "retained_fraction": float(len(retained) / len(part)),
                    "rmse": float(np.sqrt(mean_squared_error(retained["observed"], retained["predicted"]))),
                    "mae": float(mean_absolute_error(retained["observed"], retained["predicted"])),
                }
            )
    return pd.DataFrame(rows)


def deployment_boundary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "regime": "CV-G",
                "deployment_state": "FORECAST_SUPPORTED",
                "reason": "Unseen genotype in a represented categorical environment.",
            },
            {
                "regime": "CV2",
                "deployment_state": "FORECAST_SUPPORTED",
                "reason": "Sparse genotype-environment response with genotype observed in other represented environments.",
            },
            {
                "regime": "CV-E",
                "deployment_state": "UNSUPPORTED_ENVIRONMENT",
                "reason": "Held-out environment has no transferable continuous environmental descriptors.",
            },
            {
                "regime": "CV-GE",
                "deployment_state": "UNSUPPORTED_ENVIRONMENT",
                "reason": "Both genotype and categorical environment are unseen; environment similarity cannot be inferred.",
            },
        ]
    )


def make_figure(coverage: pd.DataFrame, selective: pd.DataFrame, path: Path) -> None:
    pooled = coverage[coverage["scope"] == "pooled"].copy()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for regime, part in pooled.groupby("regime"):
        axes[0].plot(part["nominal_coverage"], part["empirical_coverage"], marker="o", label=regime)
    axes[0].plot([0.78, 0.97], [0.78, 0.97], linestyle="--", linewidth=1, label="ideal")
    axes[0].set_xlabel("Nominal coverage")
    axes[0].set_ylabel("Empirical coverage")
    axes[0].set_title("Cross-fitted interval calibration")
    axes[0].legend(frameon=False)
    axes[0].grid(alpha=0.25)

    for regime, part in selective.groupby("regime"):
        axes[1].plot(part["retained_fraction"], part["rmse"], marker="o", label=regime)
    axes[1].set_xlabel("Retained fraction")
    axes[1].set_ylabel("RMSE")
    axes[1].set_title("Selective-risk diagnostic")
    axes[1].invert_xaxis()
    axes[1].legend(frameon=False)
    axes[1].grid(alpha=0.25)
    fig.suptitle("Case Study B — uncertainty, genomic support, and reliability")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def run(output_root: Path) -> dict[str, Path]:
    root = output_root.resolve()
    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    predictions = load_frozen_predictions(root)
    calibrated = calibrate_intervals(predictions)

    interim = root / "data" / "interim" / "case_study_b"
    if not interim.exists():
        raise FileNotFoundError(
            "Case Study B extracted data are required for genomic-support diagnostics. "
            "Run plant_intelligence.data.wheat_gxe first."
        )
    _, geno = load_locked_matrices(interim)
    cv_g_path = results / "case_study_b_cv_g_folds.csv"
    if not cv_g_path.exists():
        raise FileNotFoundError("Locked CV-G manifest is required.")
    cv_g = pd.read_csv(cv_g_path)
    calibrated = genomic_support_distance(calibrated, geno, cv_g)

    coverage = coverage_summary(calibrated)
    diagnostics = support_diagnostics(calibrated)
    selective = selective_risk(calibrated)
    boundary = deployment_boundary()

    paths = {
        "predictions": results / "case_study_b_uncertainty_predictions.csv",
        "coverage": results / "case_study_b_uncertainty_coverage.csv",
        "support": results / "case_study_b_support_diagnostics.csv",
        "selective_risk": results / "case_study_b_selective_risk.csv",
        "deployment_boundary": results / "case_study_b_deployment_boundary.csv",
        "figure": figures / "case_study_b_uncertainty_reliability.png",
    }
    calibrated.to_csv(paths["predictions"], index=False)
    coverage.to_csv(paths["coverage"], index=False)
    diagnostics.to_csv(paths["support"], index=False)
    selective.to_csv(paths["selective_risk"], index=False)
    boundary.to_csv(paths["deployment_boundary"], index=False)
    make_figure(coverage, selective, paths["figure"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Case Study B Step B4 uncertainty and reliability.")
    parser.add_argument("--output-root", default=".")
    args = parser.parse_args()
    paths = run(Path(args.output_root))
    print("Case Study B Step B4 uncertainty/reliability complete")
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
