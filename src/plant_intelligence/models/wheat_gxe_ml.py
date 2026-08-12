"""Case Study B Step B3: high-dimensional ML challengers for wheat GxE.

The classical benchmark envelope is frozen before this module runs. Challengers
are evaluated only on the pre-registered primary CV-G and CV2 deployments.
Each challenger is fit separately within environment, matching the empirical B2-R
finding that predictive covariance is predominantly environment-specific.

All preprocessing and hyperparameter selection are fitted inside the outer
training partition. PCA is therefore never fitted on an outer-test genotype.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from plant_intelligence.data.wheat_gxe import (
    EXPECTED_ENVIRONMENTS,
    build_cv2_sparse,
    build_cv_e,
    build_cv_g,
    build_cv_ge_scenarios,
    load_locked_matrices,
    run_data_lock,
)
from plant_intelligence.models.wheat_gxe_baseline import build_splits, phenotype_long

SEED = 20260812
INNER_SPLITS = 2
BOOTSTRAP_REPS = 2000

MODEL_PCA_KERNEL = "PCA+Kernel"
MODEL_RF = "Random Forest"
MODEL_XGB = "XGBoost"
MODEL_LGBM = "LightGBM"
CHALLENGERS = (MODEL_PCA_KERNEL, MODEL_RF, MODEL_XGB, MODEL_LGBM)


def predictive_correlation(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) < 3 or np.std(y_true) == 0 or np.std(y_pred) == 0:
        return float("nan")
    return float(np.corrcoef(y_true, y_pred)[0, 1])


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan"),
        "rho": predictive_correlation(y_true, y_pred),
    }


def candidate_grid(model_name: str) -> list[dict[str, Any]]:
    """Compact, pre-specified grids to prevent post-result model chasing."""
    if model_name == MODEL_PCA_KERNEL:
        return [
            {"n_components": 20, "alpha": 1.0},
            {"n_components": 20, "alpha": 10.0},
            {"n_components": 50, "alpha": 1.0},
            {"n_components": 50, "alpha": 10.0},
        ]
    if model_name == MODEL_RF:
        return [
            {"max_features": "sqrt", "min_samples_leaf": 2},
            {"max_features": "sqrt", "min_samples_leaf": 5},
            {"max_features": 0.2, "min_samples_leaf": 2},
        ]
    if model_name == MODEL_XGB:
        return [
            {"max_depth": 2, "min_child_weight": 3},
            {"max_depth": 4, "min_child_weight": 3},
        ]
    if model_name == MODEL_LGBM:
        return [
            {"num_leaves": 15, "min_child_samples": 15},
            {"num_leaves": 31, "min_child_samples": 20},
        ]
    raise ValueError(f"Unknown challenger: {model_name}")


def build_estimator(model_name: str, params: dict[str, Any], seed: int = SEED):
    """Build one deterministic challenger; optional boosting imports remain lazy."""
    if model_name == MODEL_PCA_KERNEL:
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("pca", PCA(n_components=int(params["n_components"]), random_state=seed)),
                ("pc_scale", StandardScaler()),
                ("model", KernelRidge(kernel="rbf", alpha=float(params["alpha"]), gamma=None)),
            ]
        )
    if model_name == MODEL_RF:
        return RandomForestRegressor(
            n_estimators=300,
            max_features=params["max_features"],
            min_samples_leaf=int(params["min_samples_leaf"]),
            random_state=seed,
            n_jobs=2,
        )
    if model_name == MODEL_XGB:
        from xgboost import XGBRegressor

        return XGBRegressor(
            n_estimators=300,
            learning_rate=0.03,
            max_depth=int(params["max_depth"]),
            min_child_weight=float(params["min_child_weight"]),
            subsample=0.8,
            colsample_bytree=0.5,
            reg_lambda=5.0,
            objective="reg:squarederror",
            tree_method="hist",
            random_state=seed,
            n_jobs=2,
            verbosity=0,
        )
    if model_name == MODEL_LGBM:
        from lightgbm import LGBMRegressor

        return LGBMRegressor(
            n_estimators=300,
            learning_rate=0.03,
            num_leaves=int(params["num_leaves"]),
            min_child_samples=int(params["min_child_samples"]),
            subsample=0.8,
            colsample_bytree=0.5,
            reg_lambda=5.0,
            random_state=seed,
            n_jobs=2,
            verbosity=-1,
        )
    raise ValueError(f"Unknown challenger: {model_name}")


def tune_environment_model(
    x: np.ndarray,
    y: np.ndarray,
    model_name: str,
    seed: int,
) -> tuple[dict[str, Any], float]:
    """Select hyperparameters only inside one outer-training environment."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    splitter = KFold(n_splits=INNER_SPLITS, shuffle=True, random_state=seed)
    best: tuple[float, str, dict[str, Any]] | None = None
    for params in candidate_grid(model_name):
        sq_errors: list[np.ndarray] = []
        for inner_train, inner_val in splitter.split(x):
            estimator = build_estimator(model_name, params, seed=seed)
            estimator.fit(x[inner_train], y[inner_train])
            pred = np.asarray(estimator.predict(x[inner_val]), dtype=float)
            sq_errors.append((y[inner_val] - pred) ** 2)
        rmse = float(np.sqrt(np.mean(np.concatenate(sq_errors))))
        key = json.dumps(params, sort_keys=True)
        candidate = (rmse, key, params)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    if best is None:
        raise RuntimeError("No ML hyperparameter candidate was evaluated.")
    return dict(best[2]), float(best[0])


def primary_splits(cells: pd.DataFrame, pheno: pd.DataFrame):
    cv_g = build_cv_g(pheno.index.tolist())
    cv2 = build_cv2_sparse(pheno.index.tolist(), EXPECTED_ENVIRONMENTS)
    cv_e = build_cv_e(EXPECTED_ENVIRONMENTS)
    cv_ge = build_cv_ge_scenarios(cv_g, EXPECTED_ENVIRONMENTS)
    return [
        split
        for split in build_splits(cells, cv_g, cv2, cv_e, cv_ge)
        if split.regime in {"CV-G", "CV2"}
    ]


def evaluate_challengers(
    pheno: pd.DataFrame,
    geno: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cells = phenotype_long(pheno)
    splits = primary_splits(cells, pheno)
    x_by_g = geno.to_numpy(dtype=float)
    predictions: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []

    for split_idx, split in enumerate(splits):
        train = cells.iloc[split.train_index].reset_index(drop=True)
        test = cells.iloc[split.test_index].reset_index(drop=True)
        for model_idx, model_name in enumerate(CHALLENGERS):
            for env_idx, env in enumerate(EXPECTED_ENVIRONMENTS):
                train_env = train[train["environment"] == env].reset_index(drop=True)
                test_env = test[test["environment"] == env].reset_index(drop=True)
                if test_env.empty:
                    continue
                if train_env.empty:
                    raise RuntimeError(f"No training observations for represented environment {env}.")

                x_train = x_by_g[train_env["g_idx"].to_numpy(dtype=int)]
                y_train = train_env["observed"].to_numpy(dtype=float)
                x_test = x_by_g[test_env["g_idx"].to_numpy(dtype=int)]
                local_seed = SEED + 1000 * split_idx + 100 * model_idx + env_idx
                params, inner_rmse = tune_environment_model(
                    x_train, y_train, model_name, local_seed
                )
                estimator = build_estimator(model_name, params, seed=local_seed)
                estimator.fit(x_train, y_train)
                pred = np.asarray(estimator.predict(x_test), dtype=float)

                selections.append(
                    {
                        "regime": split.regime,
                        "scenario": split.scenario,
                        "environment": env,
                        "model": model_name,
                        "n_train": int(len(train_env)),
                        "n_test": int(len(test_env)),
                        "inner_rmse": inner_rmse,
                        "selected_params": json.dumps(params, sort_keys=True),
                    }
                )
                for row, value in zip(test_env.itertuples(index=False), pred):
                    predictions.append(
                        {
                            "regime": split.regime,
                            "scenario": split.scenario,
                            "model": model_name,
                            "genotype_id": str(row.genotype_id),
                            "environment": str(row.environment),
                            "observed": float(row.observed),
                            "predicted": float(value),
                            "error": float(row.observed - value),
                        }
                    )

    return pd.DataFrame(predictions), pd.DataFrame(selections)


def summarize(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for regime in ("CV-G", "CV2"):
        for model_name in CHALLENGERS:
            frame = predictions[
                (predictions["regime"] == regime) & (predictions["model"] == model_name)
            ]
            rows.append(
                {
                    "regime": regime,
                    "model": model_name,
                    "n_predictions": int(len(frame)),
                    "n_genotypes": int(frame["genotype_id"].nunique()),
                    "n_environments": int(frame["environment"].nunique()),
                    **metrics(frame["observed"], frame["predicted"]),
                }
            )
    return pd.DataFrame(rows)


def load_frozen_champion_predictions(root: Path) -> pd.DataFrame:
    """Load the already-published champion for each primary deployment regime."""
    mixture = pd.read_csv(root / "reports/results/case_study_b_gxe_mixture_predictions.csv")
    legacy = pd.read_csv(root / "reports/results/case_study_b_model_predictions.csv")
    cvg = mixture[
        (mixture["regime"] == "CV-G")
        & (mixture["model"] == "G+E+normalized-GxE-mixture")
    ].copy()
    cvg["model"] = "Frozen classical champion"
    cv2 = legacy[
        (legacy["regime"] == "CV2") & (legacy["model"] == "G+E+GxE")
    ].copy()
    cv2["model"] = "Frozen classical champion"
    out = pd.concat([cvg, cv2], ignore_index=True)
    if len(cvg) != 2396 or len(cv2) != 599:
        raise ValueError(
            f"Unexpected frozen champion rows: CV-G={len(cvg)}, CV2={len(cv2)}"
        )
    return out


def paired_cluster_bootstrap(
    champion: pd.DataFrame,
    candidate: pd.DataFrame,
    regime: str,
    model_name: str,
    n_bootstrap: int = BOOTSTRAP_REPS,
) -> list[dict[str, Any]]:
    ref = champion[champion["regime"] == regime][
        ["genotype_id", "environment", "observed", "predicted"]
    ].rename(columns={"predicted": "pred_ref"})
    cand = candidate[
        (candidate["regime"] == regime) & (candidate["model"] == model_name)
    ][["genotype_id", "environment", "observed", "predicted"]].rename(
        columns={"observed": "observed_cand", "predicted": "pred_cand"}
    )
    merged = ref.merge(cand, on=["genotype_id", "environment"], how="inner")
    if len(merged) != len(ref) or len(merged) != len(cand):
        raise ValueError(f"Prediction alignment failed for {regime}/{model_name}.")
    if not np.allclose(merged["observed"], merged["observed_cand"]):
        raise ValueError("Observed outcomes differ between champion and challenger.")

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
    arrays = {c: grouped[c].to_numpy(dtype=float) for c in grouped.columns}
    rng = np.random.default_rng(SEED)
    n_groups = len(grouped)
    rmse_delta = np.empty(n_bootstrap)
    mae_delta = np.empty(n_bootstrap)
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

    obs = merged["observed"].to_numpy(float)
    pred_ref = merged["pred_ref"].to_numpy(float)
    pred_cand = merged["pred_cand"].to_numpy(float)
    observed = {
        "rmse": metrics(obs, pred_cand)["rmse"] - metrics(obs, pred_ref)["rmse"],
        "mae": metrics(obs, pred_cand)["mae"] - metrics(obs, pred_ref)["mae"],
    }
    rows: list[dict[str, Any]] = []
    for metric_name, values in (("rmse", rmse_delta), ("mae", mae_delta)):
        rows.append(
            {
                "regime": regime,
                "reference_model": "Frozen classical champion",
                "candidate_model": model_name,
                "metric": metric_name,
                "delta_candidate_minus_reference": float(observed[metric_name]),
                "bootstrap_ci_low": float(np.quantile(values, 0.025)),
                "bootstrap_ci_high": float(np.quantile(values, 0.975)),
                "bootstrap_probability_improvement": float(np.mean(values < 0)),
                "n_genotype_clusters": int(n_groups),
                "n_bootstrap": int(n_bootstrap),
            }
        )
    return rows


def benchmark_table(
    summary: pd.DataFrame,
    envelope: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> pd.DataFrame:
    thresholds = envelope.set_index("regime")["frozen_rmse_threshold"].to_dict()
    rows: list[dict[str, Any]] = []
    for row in summary.itertuples(index=False):
        threshold = float(thresholds[row.regime])
        boot = bootstrap[
            (bootstrap["regime"] == row.regime)
            & (bootstrap["candidate_model"] == row.model)
            & (bootstrap["metric"] == "rmse")
        ].iloc[0]
        rows.append(
            {
                "regime": row.regime,
                "model": row.model,
                "rmse": float(row.rmse),
                "frozen_classical_rmse": threshold,
                "rmse_delta_vs_frozen": float(row.rmse - threshold),
                "beats_frozen_point_estimate": bool(row.rmse < threshold),
                "bootstrap_ci_low": float(boot.bootstrap_ci_low),
                "bootstrap_ci_high": float(boot.bootstrap_ci_high),
                "bootstrap_probability_improvement": float(
                    boot.bootstrap_probability_improvement
                ),
                "robustly_beats_frozen": bool(boot.bootstrap_ci_high < 0),
            }
        )
    return pd.DataFrame(rows)


def plot_results(summary: pd.DataFrame, envelope: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    regimes = ["CV-G", "CV2"]
    x = np.arange(len(regimes), dtype=float)
    width = 0.18
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    for idx, model_name in enumerate(CHALLENGERS):
        values = [
            float(summary[(summary["regime"] == regime) & (summary["model"] == model_name)]["rmse"].iloc[0])
            for regime in regimes
        ]
        bars = ax.bar(x + (idx - 1.5) * width, values, width, label=model_name)
        ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=8)
    thresholds = envelope.set_index("regime")["frozen_rmse_threshold"]
    for idx, regime in enumerate(regimes):
        ax.hlines(float(thresholds[regime]), idx - 0.42, idx + 0.42, linestyles="--", linewidth=1.5)
    ax.set_xticks(x, regimes)
    ax.set_ylabel("Out-of-sample RMSE")
    ax.set_title("Case Study B — ML challengers vs frozen classical G×E envelope")
    ax.legend(frameon=False, ncol=2)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(destination, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(root: str | Path = ".") -> dict[str, pd.DataFrame]:
    root = Path(root).resolve()
    results_dir = root / "reports/results"
    figures_dir = root / "reports/figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    run_data_lock(root)
    pheno, geno = load_locked_matrices(root / "data/interim/case_study_b")
    predictions, selections = evaluate_challengers(pheno, geno)
    summary = summarize(predictions)
    champion = load_frozen_champion_predictions(root)
    envelope = pd.read_csv(results_dir / "case_study_b_classical_benchmark_envelope.csv")

    boot_rows: list[dict[str, Any]] = []
    for regime in ("CV-G", "CV2"):
        for model_name in CHALLENGERS:
            boot_rows.extend(
                paired_cluster_bootstrap(champion, predictions, regime, model_name)
            )
    bootstrap = pd.DataFrame(boot_rows)
    comparison = benchmark_table(summary, envelope, bootstrap)

    predictions.to_csv(results_dir / "case_study_b_ml_predictions.csv", index=False)
    selections.to_csv(results_dir / "case_study_b_ml_selection.csv", index=False)
    summary.to_csv(results_dir / "case_study_b_ml_summary.csv", index=False)
    bootstrap.to_csv(results_dir / "case_study_b_ml_challenger_bootstrap.csv", index=False)
    comparison.to_csv(results_dir / "case_study_b_ml_envelope_comparison.csv", index=False)
    plot_results(summary, envelope, figures_dir / "case_study_b_ml_challengers.png")

    print("Case Study B Step B3 ML challenger benchmark complete", flush=True)
    print("\nChallenger summary", flush=True)
    print(summary.to_string(index=False), flush=True)
    print("\nFrozen-envelope comparison", flush=True)
    print(comparison.to_string(index=False), flush=True)
    return {
        "predictions": predictions,
        "selections": selections,
        "summary": summary,
        "bootstrap": bootstrap,
        "comparison": comparison,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Case Study B Step B3 ML challengers.")
    parser.add_argument("--output-root", default=".")
    args = parser.parse_args()
    run(args.output_root)


if __name__ == "__main__":
    main()
