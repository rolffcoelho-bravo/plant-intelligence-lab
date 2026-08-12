"""Resolve the Case Study B GxE interaction-weight boundary under locked CV.

Step B2-R keeps the classical model family fixed and asks whether the original
GxE interaction-weight grid (gamma <= 4) truncated the predictive optimum.
Only the pre-registered primary regimes are used for champion selection:
CV-G (whole unseen genotypes) and CV2 (one masked environment per genotype).

The module compares the original grid with a deliberately wider, denser grid,
records the full training-only tuning surface, re-evaluates the selected models
out of sample, and uses paired genotype-cluster bootstrap uncertainty. It does
not introduce nonlinear ML or change the validation manifests.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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
    ALPHA_GRID,
    BOOTSTRAP_REPS,
    INNER_SPLITS,
    MODEL_GE,
    MODEL_GXE,
    SEED,
    build_splits,
    fit_model,
    genomic_relationship,
    phenotype_long,
    predict_model,
    predictive_correlation,
)

LEGACY_GAMMA_GRID = (0.25, 1.0, 4.0)
EXPANDED_GAMMA_GRID = (
    0.25,
    0.5,
    1.0,
    2.0,
    3.0,
    4.0,
    6.0,
    8.0,
    12.0,
    16.0,
    24.0,
    32.0,
    48.0,
    64.0,
    96.0,
    128.0,
)

MODEL_GXE_LEGACY = "G+E+GxE legacy-grid"
MODEL_GXE_EXPANDED = "G+E+GxE expanded-grid"


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan"),
        "rho": predictive_correlation(y_true, y_pred),
    }


def _tuning_surface(
    train: pd.DataFrame,
    k_genomic: np.ndarray,
    gamma_grid: tuple[float, ...],
) -> pd.DataFrame:
    """Evaluate alpha/gamma candidates using genotype-grouped inner CV only."""

    groups = train["genotype_id"].astype(str).to_numpy()
    if len(np.unique(groups)) < INNER_SPLITS:
        raise ValueError("Too few genotype groups for inner validation.")
    splitter = GroupKFold(n_splits=INNER_SPLITS)
    y = train["observed"].to_numpy(dtype=float)
    g = train["g_idx"].to_numpy(dtype=int)
    e = train["e_idx"].to_numpy(dtype=int)

    rows: list[dict[str, float]] = []
    for alpha in ALPHA_GRID:
        for gamma in gamma_grid:
            sq_errors: list[np.ndarray] = []
            for inner_train, inner_val in splitter.split(train, groups=groups):
                fitted = fit_model(
                    y[inner_train],
                    g[inner_train],
                    e[inner_train],
                    k_genomic,
                    MODEL_GXE,
                    alpha=float(alpha),
                    gamma=float(gamma),
                )
                pred = predict_model(
                    fitted,
                    g[inner_val],
                    e[inner_val],
                    k_genomic,
                )
                sq_errors.append((y[inner_val] - pred) ** 2)
            rows.append(
                {
                    "alpha": float(alpha),
                    "gamma": float(gamma),
                    "inner_grouped_rmse": float(
                        np.sqrt(np.mean(np.concatenate(sq_errors)))
                    ),
                }
            )

    surface = pd.DataFrame(rows).sort_values(
        ["inner_grouped_rmse", "alpha", "gamma"], ignore_index=True
    )
    surface["rank"] = np.arange(1, len(surface) + 1)
    surface["selected"] = surface["rank"] == 1
    return surface


def _fit_selected_gxe(
    train: pd.DataFrame,
    test: pd.DataFrame,
    k_genomic: np.ndarray,
    surface: pd.DataFrame,
) -> tuple[np.ndarray, float, float, float, int]:
    selected = surface.iloc[0]
    alpha = float(selected["alpha"])
    gamma = float(selected["gamma"])
    fitted = fit_model(
        train["observed"].to_numpy(dtype=float),
        train["g_idx"].to_numpy(dtype=int),
        train["e_idx"].to_numpy(dtype=int),
        k_genomic,
        MODEL_GXE,
        alpha=alpha,
        gamma=gamma,
    )
    pred = predict_model(
        fitted,
        test["g_idx"].to_numpy(dtype=int),
        test["e_idx"].to_numpy(dtype=int),
        k_genomic,
    )
    return pred, alpha, gamma, float(selected["inner_grouped_rmse"]), fitted.cg_iterations


def _tune_ge(train: pd.DataFrame, k_genomic: np.ndarray) -> tuple[float, float]:
    """Tune the fixed G+E reference under the same grouped inner split rule."""

    groups = train["genotype_id"].astype(str).to_numpy()
    splitter = GroupKFold(n_splits=INNER_SPLITS)
    y = train["observed"].to_numpy(dtype=float)
    g = train["g_idx"].to_numpy(dtype=int)
    e = train["e_idx"].to_numpy(dtype=int)
    candidates: list[tuple[float, float]] = []
    for alpha in ALPHA_GRID:
        sq_errors: list[np.ndarray] = []
        for inner_train, inner_val in splitter.split(train, groups=groups):
            fitted = fit_model(
                y[inner_train],
                g[inner_train],
                e[inner_train],
                k_genomic,
                MODEL_GE,
                alpha=float(alpha),
            )
            pred = predict_model(fitted, g[inner_val], e[inner_val], k_genomic)
            sq_errors.append((y[inner_val] - pred) ** 2)
        candidates.append(
            (float(np.sqrt(np.mean(np.concatenate(sq_errors)))), float(alpha))
        )
    best_rmse, best_alpha = min(candidates)
    return best_alpha, best_rmse


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

        legacy = _tuning_surface(train, k_genomic, LEGACY_GAMMA_GRID)
        expanded = _tuning_surface(train, k_genomic, EXPANDED_GAMMA_GRID)
        legacy_pred, legacy_alpha, legacy_gamma, legacy_inner, legacy_cg = _fit_selected_gxe(
            train, test, k_genomic, legacy
        )
        expanded_pred, expanded_alpha, expanded_gamma, expanded_inner, expanded_cg = _fit_selected_gxe(
            train, test, k_genomic, expanded
        )

        ge_alpha, ge_inner = _tune_ge(train, k_genomic)
        ge_fitted = fit_model(
            train["observed"].to_numpy(dtype=float),
            train["g_idx"].to_numpy(dtype=int),
            train["e_idx"].to_numpy(dtype=int),
            k_genomic,
            MODEL_GE,
            alpha=ge_alpha,
        )
        ge_pred = predict_model(
            ge_fitted,
            test["g_idx"].to_numpy(dtype=int),
            test["e_idx"].to_numpy(dtype=int),
            k_genomic,
        )

        best_by_gamma = (
            expanded.groupby("gamma", as_index=False)["inner_grouped_rmse"].min()
            .sort_values("gamma")
            .reset_index(drop=True)
        )
        selected_rmse = float(expanded.iloc[0]["inner_grouped_rmse"])
        best_by_gamma["rmse_minus_selected"] = (
            best_by_gamma["inner_grouped_rmse"] - selected_rmse
        )
        best_by_gamma["regime"] = split.regime
        best_by_gamma["scenario"] = split.scenario
        profile_rows.append(best_by_gamma)

        selection_rows.append(
            {
                "regime": split.regime,
                "scenario": split.scenario,
                "n_train": int(len(train)),
                "n_test": int(len(test)),
                "legacy_alpha": legacy_alpha,
                "legacy_gamma": legacy_gamma,
                "legacy_inner_rmse": legacy_inner,
                "legacy_upper_boundary": bool(legacy_gamma == max(LEGACY_GAMMA_GRID)),
                "expanded_alpha": expanded_alpha,
                "expanded_gamma": expanded_gamma,
                "expanded_inner_rmse": expanded_inner,
                "expanded_upper_boundary": bool(
                    expanded_gamma == max(EXPANDED_GAMMA_GRID)
                ),
                "inner_rmse_gain_expanded_vs_legacy": legacy_inner - expanded_inner,
                "ge_alpha": ge_alpha,
                "ge_inner_rmse": ge_inner,
                "legacy_cg_iterations": int(legacy_cg),
                "expanded_cg_iterations": int(expanded_cg),
                "ge_cg_iterations": int(ge_fitted.cg_iterations),
            }
        )

        obs = test["observed"].to_numpy(dtype=float)
        for model_name, pred in (
            (MODEL_GE, ge_pred),
            (MODEL_GXE_LEGACY, legacy_pred),
            (MODEL_GXE_EXPANDED, expanded_pred),
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
        for model_name in (MODEL_GE, MODEL_GXE_LEGACY, MODEL_GXE_EXPANDED):
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


def _paired_cluster_bootstrap(
    predictions: pd.DataFrame,
    regime: str,
    reference_model: str,
    candidate_model: str,
    n_bootstrap: int = BOOTSTRAP_REPS,
    seed: int = SEED,
) -> list[dict[str, object]]:
    ref = predictions[
        (predictions["regime"] == regime)
        & (predictions["model"] == reference_model)
    ][["genotype_id", "environment", "observed", "predicted"]].rename(
        columns={"predicted": "pred_ref"}
    )
    cand = predictions[
        (predictions["regime"] == regime)
        & (predictions["model"] == candidate_model)
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
                "reference_model": reference_model,
                "candidate_model": candidate_model,
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


def build_bootstrap_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for regime in ("CV-G", "CV2"):
        rows.extend(
            _paired_cluster_bootstrap(
                predictions, regime, MODEL_GE, MODEL_GXE_EXPANDED
            )
        )
        rows.extend(
            _paired_cluster_bootstrap(
                predictions, regime, MODEL_GXE_LEGACY, MODEL_GXE_EXPANDED
            )
        )
    return pd.DataFrame(rows)


def build_boundary_audit(selection: pd.DataFrame) -> pd.DataFrame:
    expanded_upper = int(selection["expanded_upper_boundary"].sum())
    legacy_upper = int(selection["legacy_upper_boundary"].sum())
    return pd.DataFrame(
        [
            {
                "n_primary_scenarios": int(len(selection)),
                "legacy_upper_boundary_scenarios": legacy_upper,
                "expanded_upper_boundary_scenarios": expanded_upper,
                "boundary_resolved": bool(expanded_upper == 0),
                "expanded_gamma_min_selected": float(selection["expanded_gamma"].min()),
                "expanded_gamma_median_selected": float(selection["expanded_gamma"].median()),
                "expanded_gamma_max_selected": float(selection["expanded_gamma"].max()),
                "expanded_grid_max": float(max(EXPANDED_GAMMA_GRID)),
                "mean_inner_rmse_gain_expanded_vs_legacy": float(
                    selection["inner_rmse_gain_expanded_vs_legacy"].mean()
                ),
            }
        ]
    )


def plot_gamma_profile(profile: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for (regime, scenario), frame in profile.groupby(["regime", "scenario"], sort=True):
        ax.plot(
            frame["gamma"],
            frame["inner_grouped_rmse"],
            marker="o",
            linewidth=1.2,
            markersize=3.5,
            label=f"{regime} {scenario}",
        )
    ax.set_xscale("log", base=2)
    ax.set_xlabel("GxE interaction-kernel weight gamma (log2 scale)")
    ax.set_ylabel("Best genotype-grouped inner-CV RMSE at gamma")
    ax.set_title("Case Study B — GxE interaction-weight robustness")
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
    bootstrap = build_bootstrap_table(predictions)
    boundary_audit = build_boundary_audit(selection)

    predictions.to_csv(
        results_dir / "case_study_b_gxe_robustness_predictions.csv", index=False
    )
    selection.to_csv(
        results_dir / "case_study_b_gxe_robustness_selection.csv", index=False
    )
    profile.to_csv(
        results_dir / "case_study_b_gxe_robustness_tuning_profile.csv", index=False
    )
    summary.to_csv(
        results_dir / "case_study_b_gxe_robustness_summary.csv", index=False
    )
    bootstrap.to_csv(
        results_dir / "case_study_b_gxe_robustness_bootstrap.csv", index=False
    )
    boundary_audit.to_csv(
        results_dir / "case_study_b_gxe_robustness_audit.csv", index=False
    )
    plot_gamma_profile(
        profile, figures_dir / "case_study_b_gxe_gamma_robustness.png"
    )

    print("Case Study B GxE robustness analysis complete", flush=True)
    print("\nBoundary audit", flush=True)
    print(boundary_audit.to_string(index=False), flush=True)
    print("\nSelected hyperparameters", flush=True)
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
        "boundary_audit": boundary_audit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve the Case Study B classical GxE interaction-weight boundary."
    )
    parser.add_argument("--output-root", default=".")
    args = parser.parse_args()
    run(args.output_root)


if __name__ == "__main__":
    main()
