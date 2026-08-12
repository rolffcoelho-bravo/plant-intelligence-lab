"""Normalized-kernel robustness refinement for Case Study B Step B2-R.

A raw interaction weight gamma and ridge alpha are jointly scale-dependent. The
first B2-R expansion therefore exposed a second high-gamma/high-alpha ridge. To
resolve that parameterization artifact, this module uses an interpretable bounded
kernel mixture

    K_eta = (1 - eta) K_G + eta K_GxE,   eta in [0, 1],

with an independent ridge lambda. eta=0 is genomic main-effect sharing across
environments; eta=1 is a pure environment-specific genomic kernel. The endpoint
eta=1 is part of the parameter space, so selecting it is a scientific result,
not an unresolved numerical search boundary.

Champion selection remains restricted to the locked primary CV-G and CV2
regimes. No nonlinear ML is introduced here.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse.linalg import LinearOperator, cg
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold

from plant_intelligence.data.wheat_gxe import (
    EXPECTED_ENVIRONMENTS,
    build_cv2_sparse,
    build_cv_e,
    build_cv_g,
    build_cv_ge_scenarios,
    load_locked_matrices,
    run_data_lock,
)
from plant_intelligence.models.wheat_gxe_baseline import (
    BOOTSTRAP_REPS,
    INNER_SPLITS,
    SEED,
    build_splits,
    genomic_relationship,
    phenotype_long,
    predictive_correlation,
)

ETA_GRID = (0.0, 0.5, 0.67, 0.8, 0.9, 0.95, 0.975, 0.98, 0.99, 0.995, 1.0)
LAMBDA_GRID = (0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 10.0, 20.0)

MODEL_REFERENCE = "G+E normalized-reference"
MODEL_MIXTURE = "G+E+normalized-GxE-mixture"


@dataclass
class FittedMixtureModel:
    eta: float
    ridge_lambda: float
    global_mean: float
    environment_means: dict[int, float]
    train_g: np.ndarray
    train_e: np.ndarray
    coefficients: np.ndarray
    cg_iterations: int


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan"),
        "rho": predictive_correlation(y_true, y_pred),
    }


def _environment_baseline(
    y: np.ndarray, e_idx: np.ndarray
) -> tuple[float, dict[int, float], np.ndarray]:
    global_mean = float(np.mean(y))
    environment_means = {
        int(env): float(np.mean(y[e_idx == env])) for env in np.unique(e_idx)
    }
    baseline = np.asarray(
        [environment_means[int(env)] for env in e_idx], dtype=float
    )
    return global_mean, environment_means, baseline


def _mixture_train_matvec(
    vector: np.ndarray,
    train_g: np.ndarray,
    train_e: np.ndarray,
    k_genomic: np.ndarray,
    eta: float,
) -> np.ndarray:
    if not 0.0 <= eta <= 1.0:
        raise ValueError("eta must lie in [0, 1].")
    n_genotypes = k_genomic.shape[0]
    v = np.asarray(vector, dtype=float)
    by_g = np.bincount(train_g, weights=v, minlength=n_genotypes)
    main = (k_genomic @ by_g)[train_g]
    interaction = np.zeros_like(v)
    for env in np.unique(train_e):
        mask = train_e == env
        by_g_env = np.bincount(
            train_g[mask], weights=v[mask], minlength=n_genotypes
        )
        interaction[mask] = (k_genomic @ by_g_env)[train_g[mask]]
    return (1.0 - eta) * main + eta * interaction


def _mixture_cross_predict(
    coefficients: np.ndarray,
    train_g: np.ndarray,
    train_e: np.ndarray,
    test_g: np.ndarray,
    test_e: np.ndarray,
    k_genomic: np.ndarray,
    eta: float,
) -> np.ndarray:
    n_genotypes = k_genomic.shape[0]
    by_g = np.bincount(train_g, weights=coefficients, minlength=n_genotypes)
    main = k_genomic[np.asarray(test_g, dtype=int)] @ by_g
    interaction = np.zeros(len(test_g), dtype=float)
    for env in np.unique(test_e):
        test_mask = test_e == env
        train_mask = train_e == env
        if not np.any(train_mask):
            continue
        by_g_env = np.bincount(
            train_g[train_mask],
            weights=coefficients[train_mask],
            minlength=n_genotypes,
        )
        interaction[test_mask] = k_genomic[test_g[test_mask]] @ by_g_env
    return np.asarray((1.0 - eta) * main + eta * interaction, dtype=float)


def fit_mixture(
    y: np.ndarray,
    train_g: np.ndarray,
    train_e: np.ndarray,
    k_genomic: np.ndarray,
    eta: float,
    ridge_lambda: float,
) -> FittedMixtureModel:
    y = np.asarray(y, dtype=float)
    train_g = np.asarray(train_g, dtype=int)
    train_e = np.asarray(train_e, dtype=int)
    if not 0.0 <= eta <= 1.0:
        raise ValueError("eta must lie in [0, 1].")
    if ridge_lambda <= 0:
        raise ValueError("ridge_lambda must be positive.")
    if not (len(y) == len(train_g) == len(train_e)):
        raise ValueError("Training vectors must have equal length.")

    global_mean, environment_means, baseline = _environment_baseline(y, train_e)
    residual = y - baseline
    n = len(y)
    diagonal = np.diag(k_genomic)[train_g] + float(ridge_lambda)
    operator = LinearOperator(
        (n, n),
        matvec=lambda v: _mixture_train_matvec(
            v, train_g, train_e, k_genomic, eta
        )
        + float(ridge_lambda) * v,
        dtype=float,
    )
    preconditioner = LinearOperator(
        (n, n),
        matvec=lambda v: np.asarray(v, dtype=float) / diagonal,
        dtype=float,
    )
    iterations = 0

    def callback(_: np.ndarray) -> None:
        nonlocal iterations
        iterations += 1

    coefficients, info = cg(
        operator,
        residual,
        M=preconditioner,
        rtol=1e-7,
        atol=0.0,
        maxiter=1000,
        callback=callback,
    )
    if info != 0 or not np.isfinite(coefficients).all():
        raise RuntimeError(
            f"CG failed for eta={eta}, lambda={ridge_lambda}: "
            f"info={info}, iterations={iterations}"
        )
    return FittedMixtureModel(
        eta=float(eta),
        ridge_lambda=float(ridge_lambda),
        global_mean=global_mean,
        environment_means=environment_means,
        train_g=train_g,
        train_e=train_e,
        coefficients=np.asarray(coefficients, dtype=float),
        cg_iterations=iterations,
    )


def predict_mixture(
    fitted: FittedMixtureModel,
    test_g: np.ndarray,
    test_e: np.ndarray,
    k_genomic: np.ndarray,
) -> np.ndarray:
    test_g = np.asarray(test_g, dtype=int)
    test_e = np.asarray(test_e, dtype=int)
    baseline = np.asarray(
        [
            fitted.environment_means.get(int(env), fitted.global_mean)
            for env in test_e
        ],
        dtype=float,
    )
    return baseline + _mixture_cross_predict(
        fitted.coefficients,
        fitted.train_g,
        fitted.train_e,
        test_g,
        test_e,
        k_genomic,
        fitted.eta,
    )


def tuning_surface(train: pd.DataFrame, k_genomic: np.ndarray) -> pd.DataFrame:
    groups = train["genotype_id"].astype(str).to_numpy()
    if len(np.unique(groups)) < INNER_SPLITS:
        raise ValueError("Too few genotype groups for inner validation.")
    splitter = GroupKFold(n_splits=INNER_SPLITS)
    y = train["observed"].to_numpy(dtype=float)
    g = train["g_idx"].to_numpy(dtype=int)
    e = train["e_idx"].to_numpy(dtype=int)
    rows: list[dict[str, float]] = []

    for eta in ETA_GRID:
        for ridge_lambda in LAMBDA_GRID:
            sq_errors: list[np.ndarray] = []
            for inner_train, inner_val in splitter.split(train, groups=groups):
                fitted = fit_mixture(
                    y[inner_train],
                    g[inner_train],
                    e[inner_train],
                    k_genomic,
                    eta=float(eta),
                    ridge_lambda=float(ridge_lambda),
                )
                pred = predict_mixture(
                    fitted, g[inner_val], e[inner_val], k_genomic
                )
                sq_errors.append((y[inner_val] - pred) ** 2)
            rows.append(
                {
                    "eta": float(eta),
                    "ridge_lambda": float(ridge_lambda),
                    "inner_grouped_rmse": float(
                        np.sqrt(np.mean(np.concatenate(sq_errors)))
                    ),
                }
            )

    surface = pd.DataFrame(rows).sort_values(
        ["inner_grouped_rmse", "ridge_lambda", "eta"], ignore_index=True
    )
    surface["rank"] = np.arange(1, len(surface) + 1)
    surface["selected"] = surface["rank"] == 1
    return surface


def evaluate_primary(
    cells: pd.DataFrame,
    k_genomic: np.ndarray,
    primary_splits: list,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_rows: list[dict[str, object]] = []
    selection_rows: list[dict[str, object]] = []
    profile_rows: list[pd.DataFrame] = []

    for split in primary_splits:
        train = cells.iloc[split.train_index].reset_index(drop=True)
        test = cells.iloc[split.test_index].reset_index(drop=True)
        surface = tuning_surface(train, k_genomic)
        selected = surface.iloc[0]

        reference_surface = surface[surface["eta"] == 0.0].sort_values(
            ["inner_grouped_rmse", "ridge_lambda"], ignore_index=True
        )
        reference_selected = reference_surface.iloc[0]

        fitted_mix = fit_mixture(
            train["observed"].to_numpy(dtype=float),
            train["g_idx"].to_numpy(dtype=int),
            train["e_idx"].to_numpy(dtype=int),
            k_genomic,
            eta=float(selected["eta"]),
            ridge_lambda=float(selected["ridge_lambda"]),
        )
        fitted_ref = fit_mixture(
            train["observed"].to_numpy(dtype=float),
            train["g_idx"].to_numpy(dtype=int),
            train["e_idx"].to_numpy(dtype=int),
            k_genomic,
            eta=0.0,
            ridge_lambda=float(reference_selected["ridge_lambda"]),
        )
        test_g = test["g_idx"].to_numpy(dtype=int)
        test_e = test["e_idx"].to_numpy(dtype=int)
        pred_mix = predict_mixture(fitted_mix, test_g, test_e, k_genomic)
        pred_ref = predict_mixture(fitted_ref, test_g, test_e, k_genomic)

        best_by_eta = (
            surface.groupby("eta", as_index=False)["inner_grouped_rmse"].min()
            .sort_values("eta")
            .reset_index(drop=True)
        )
        selected_rmse = float(selected["inner_grouped_rmse"])
        best_by_eta["rmse_minus_selected"] = (
            best_by_eta["inner_grouped_rmse"] - selected_rmse
        )
        best_by_eta["regime"] = split.regime
        best_by_eta["scenario"] = split.scenario
        profile_rows.append(best_by_eta)

        selection_rows.append(
            {
                "regime": split.regime,
                "scenario": split.scenario,
                "n_train": int(len(train)),
                "n_test": int(len(test)),
                "selected_eta": float(selected["eta"]),
                "selected_lambda": float(selected["ridge_lambda"]),
                "selected_inner_rmse": selected_rmse,
                "pure_gxe_endpoint": bool(float(selected["eta"]) == 1.0),
                "near_pure_gxe": bool(float(selected["eta"]) >= 0.95),
                "reference_lambda": float(reference_selected["ridge_lambda"]),
                "reference_inner_rmse": float(reference_selected["inner_grouped_rmse"]),
                "inner_rmse_gain_vs_reference": float(
                    reference_selected["inner_grouped_rmse"] - selected_rmse
                ),
                "mixture_cg_iterations": int(fitted_mix.cg_iterations),
                "reference_cg_iterations": int(fitted_ref.cg_iterations),
            }
        )

        for model_name, pred in (
            (MODEL_REFERENCE, pred_ref),
            (MODEL_MIXTURE, pred_mix),
        ):
            prediction_rows.extend(
                {
                    "regime": split.regime,
                    "scenario": split.scenario,
                    "model": model_name,
                    "genotype_id": str(row.genotype_id),
                    "environment": str(row.environment),
                    "observed": float(row.observed),
                    "predicted": float(p),
                    "error": float(row.observed - p),
                }
                for row, p in zip(test.itertuples(index=False), pred)
            )

    return (
        pd.DataFrame(prediction_rows),
        pd.DataFrame(selection_rows),
        pd.concat(profile_rows, ignore_index=True),
    )


def summarize_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for regime in ("CV-G", "CV2"):
        for model_name in (MODEL_REFERENCE, MODEL_MIXTURE):
            frame = predictions[
                (predictions["regime"] == regime)
                & (predictions["model"] == model_name)
            ]
            rows.append(
                {
                    "regime": regime,
                    "model": model_name,
                    "n_predictions": int(len(frame)),
                    "n_genotypes": int(frame["genotype_id"].nunique()),
                    "n_environments": int(frame["environment"].nunique()),
                    **_metrics(frame["observed"], frame["predicted"]),
                }
            )
    return pd.DataFrame(rows)


def paired_cluster_bootstrap(
    predictions: pd.DataFrame,
    regime: str,
    n_bootstrap: int = BOOTSTRAP_REPS,
    seed: int = SEED,
) -> list[dict[str, object]]:
    ref = predictions[
        (predictions["regime"] == regime)
        & (predictions["model"] == MODEL_REFERENCE)
    ][["genotype_id", "environment", "observed", "predicted"]].rename(
        columns={"predicted": "pred_ref"}
    )
    cand = predictions[
        (predictions["regime"] == regime)
        & (predictions["model"] == MODEL_MIXTURE)
    ][["genotype_id", "environment", "observed", "predicted"]].rename(
        columns={"observed": "observed_cand", "predicted": "pred_cand"}
    )
    merged = ref.merge(cand, on=["genotype_id", "environment"], how="inner")
    if len(merged) != len(ref) or len(merged) != len(cand):
        raise ValueError("Paired prediction rows do not align.")
    if not np.allclose(merged["observed"], merged["observed_cand"]):
        raise ValueError("Observed outcomes differ between paired model rows.")

    merged["sq_ref"] = (merged["observed"] - merged["pred_ref"]) ** 2
    merged["sq_cand"] = (merged["observed"] - merged["pred_cand"]) ** 2
    merged["abs_ref"] = np.abs(merged["observed"] - merged["pred_ref"])
    merged["abs_cand"] = np.abs(merged["observed"] - merged["pred_cand"])
    grouped = merged.groupby("genotype_id", sort=True).agg(
        n=("observed", "size"),
        sq_ref=("sq_ref", "sum"),
        sq_cand=("sq_cand", "sum"),
        abs_ref=("abs_ref", "sum"),
        abs_cand=("abs_cand", "sum"),
    )
    arrays = {column: grouped[column].to_numpy(dtype=float) for column in grouped.columns}
    rng = np.random.default_rng(seed)
    n_groups = len(grouped)
    rmse_delta = np.empty(n_bootstrap, dtype=float)
    mae_delta = np.empty(n_bootstrap, dtype=float)

    for b in range(n_bootstrap):
        sample = rng.integers(0, n_groups, size=n_groups)
        n = float(np.sum(arrays["n"][sample]))
        rmse_delta[b] = (
            np.sqrt(np.sum(arrays["sq_cand"][sample]) / n)
            - np.sqrt(np.sum(arrays["sq_ref"][sample]) / n)
        )
        mae_delta[b] = (
            np.sum(arrays["abs_cand"][sample]) / n
            - np.sum(arrays["abs_ref"][sample]) / n
        )

    obs = merged["observed"].to_numpy(dtype=float)
    ref_pred = merged["pred_ref"].to_numpy(dtype=float)
    cand_pred = merged["pred_cand"].to_numpy(dtype=float)
    observed = {
        "rmse": _metrics(obs, cand_pred)["rmse"] - _metrics(obs, ref_pred)["rmse"],
        "mae": _metrics(obs, cand_pred)["mae"] - _metrics(obs, ref_pred)["mae"],
    }
    rows: list[dict[str, object]] = []
    for metric_name, samples in (("rmse", rmse_delta), ("mae", mae_delta)):
        rows.append(
            {
                "regime": regime,
                "reference_model": MODEL_REFERENCE,
                "candidate_model": MODEL_MIXTURE,
                "metric": metric_name,
                "delta_candidate_minus_reference": float(observed[metric_name]),
                "bootstrap_ci_low": float(np.quantile(samples, 0.025)),
                "bootstrap_ci_high": float(np.quantile(samples, 0.975)),
                "bootstrap_probability_improvement": float(np.mean(samples < 0)),
                "n_genotype_clusters": int(n_groups),
                "n_bootstrap": int(n_bootstrap),
            }
        )
    return rows


def build_audit(selection: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "n_primary_scenarios": int(len(selection)),
                "eta_domain_complete": True,
                "eta_grid_min": float(min(ETA_GRID)),
                "eta_grid_max": float(max(ETA_GRID)),
                "selected_eta_min": float(selection["selected_eta"].min()),
                "selected_eta_median": float(selection["selected_eta"].median()),
                "selected_eta_max": float(selection["selected_eta"].max()),
                "pure_gxe_endpoint_scenarios": int(selection["pure_gxe_endpoint"].sum()),
                "near_pure_gxe_scenarios": int(selection["near_pure_gxe"].sum()),
                "selected_lambda_min": float(selection["selected_lambda"].min()),
                "selected_lambda_median": float(selection["selected_lambda"].median()),
                "selected_lambda_max": float(selection["selected_lambda"].max()),
                "lambda_upper_boundary_scenarios": int(
                    (selection["selected_lambda"] == max(LAMBDA_GRID)).sum()
                ),
                "lambda_lower_boundary_scenarios": int(
                    (selection["selected_lambda"] == min(LAMBDA_GRID)).sum()
                ),
                "search_resolved": bool(
                    not (selection["selected_lambda"] == max(LAMBDA_GRID)).any()
                    and not (selection["selected_lambda"] == min(LAMBDA_GRID)).any()
                ),
            }
        ]
    )


def plot_eta_profile(profile: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for (regime, scenario), frame in profile.groupby(["regime", "scenario"], sort=True):
        ax.plot(
            frame["eta"],
            frame["inner_grouped_rmse"],
            marker="o",
            linewidth=1.2,
            markersize=3.5,
            label=f"{regime} {scenario}",
        )
    ax.set_xlabel("Normalized GxE interaction share eta")
    ax.set_ylabel("Best genotype-grouped inner-CV RMSE at eta")
    ax.set_title("Case Study B — normalized GxE mixture robustness")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(destination, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(root: str | Path = ".") -> dict[str, pd.DataFrame]:
    root = Path(root).resolve()
    results_dir = root / "reports" / "results"
    figures_dir = root / "reports" / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    run_data_lock(root)
    pheno, geno = load_locked_matrices(root / "data" / "interim" / "case_study_b")
    cells = phenotype_long(pheno)
    k_genomic, _ = genomic_relationship(geno)
    cv_g = build_cv_g(pheno.index.tolist())
    cv2 = build_cv2_sparse(pheno.index.tolist(), EXPECTED_ENVIRONMENTS)
    cv_e = build_cv_e(EXPECTED_ENVIRONMENTS)
    cv_ge = build_cv_ge_scenarios(cv_g, EXPECTED_ENVIRONMENTS)
    primary_splits = [
        split
        for split in build_splits(cells, cv_g, cv2, cv_e, cv_ge)
        if split.regime in ("CV-G", "CV2")
    ]
    if len(primary_splits) != 6:
        raise AssertionError(f"Expected six primary scenarios; got {len(primary_splits)}")

    predictions, selection, profile = evaluate_primary(cells, k_genomic, primary_splits)
    summary = summarize_predictions(predictions)
    bootstrap = pd.DataFrame(
        paired_cluster_bootstrap(predictions, "CV-G")
        + paired_cluster_bootstrap(predictions, "CV2")
    )
    audit = build_audit(selection)

    predictions.to_csv(
        results_dir / "case_study_b_gxe_mixture_predictions.csv", index=False
    )
    selection.to_csv(
        results_dir / "case_study_b_gxe_mixture_selection.csv", index=False
    )
    profile.to_csv(
        results_dir / "case_study_b_gxe_mixture_profile.csv", index=False
    )
    summary.to_csv(
        results_dir / "case_study_b_gxe_mixture_summary.csv", index=False
    )
    bootstrap.to_csv(
        results_dir / "case_study_b_gxe_mixture_bootstrap.csv", index=False
    )
    audit.to_csv(
        results_dir / "case_study_b_gxe_mixture_audit.csv", index=False
    )
    plot_eta_profile(profile, figures_dir / "case_study_b_gxe_mixture_robustness.png")

    print("Case Study B normalized GxE mixture robustness complete", flush=True)
    print("\nSearch audit", flush=True)
    print(audit.to_string(index=False), flush=True)
    print("\nSelected mixture parameters", flush=True)
    print(selection.to_string(index=False), flush=True)
    print("\nPrimary out-of-sample summary", flush=True)
    print(summary.to_string(index=False), flush=True)
    print("\nPaired genotype-cluster bootstrap", flush=True)
    print(bootstrap.to_string(index=False), flush=True)
    return {
        "predictions": predictions,
        "selection": selection,
        "profile": profile,
        "summary": summary,
        "bootstrap": bootstrap,
        "audit": audit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run normalized GxE mixture robustness for Case Study B."
    )
    parser.add_argument("--output-root", default=".")
    args = parser.parse_args()
    run(args.output_root)


if __name__ == "__main__":
    main()
