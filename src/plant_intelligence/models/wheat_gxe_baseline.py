"""Case Study B classical multi-environment genomic baselines.

The model sequence is intentionally interpretable:

    Environment mean -> G -> G + E -> G + E + GxE

G is represented by a standardized genomic relationship matrix. E is treated as
an environment fixed-effect baseline estimated only from the training partition.
GxE is represented by an environment-specific genomic kernel. Hyperparameters
are selected only inside each outer training partition using genotype-grouped
inner validation.

Primary evidence is CV-G (unseen genotypes) and CV2 sparse-cell prediction.
CV-E and CV-GE are retained as diagnostic stress tests because the locked BGLR
wheat data provide categorical mega-environments but no transferable continuous
weather/soil descriptor vector.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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

SEED = 20260812
ALPHA_GRID = (0.1, 1.0, 10.0, 100.0)
GAMMA_GRID = (0.25, 1.0, 4.0)
INNER_SPLITS = 2
BOOTSTRAP_REPS = 2000

MODEL_ENV = "Environment mean"
MODEL_G = "G"
MODEL_GE = "G+E"
MODEL_GXE = "G+E+GxE"
MODEL_SEQUENCE = (MODEL_ENV, MODEL_G, MODEL_GE, MODEL_GXE)


@dataclass(frozen=True)
class SplitDefinition:
    regime: str
    scenario: str
    train_index: np.ndarray
    test_index: np.ndarray


@dataclass
class FittedKernelModel:
    model: str
    alpha: float | None
    gamma: float
    global_mean: float
    environment_means: dict[int, float]
    train_g: np.ndarray
    train_e: np.ndarray
    coefficients: np.ndarray | None
    cg_iterations: int


def predictive_correlation(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if len(y_true) < 3 or np.std(y_true) == 0 or np.std(y_pred) == 0:
        return float("nan")
    return float(np.corrcoef(y_true, y_pred)[0, 1])


def genomic_relationship(geno: pd.DataFrame) -> tuple[np.ndarray, dict[str, float]]:
    """Build a VanRaden-style standardized marker relationship matrix.

    Markers are centered and scaled within the locked 599-line population. Zero-
    variance markers are removed. K is normalized to mean diagonal one so the
    ridge parameter has a stable scale across executions.
    """

    x = geno.to_numpy(dtype=float)
    means = np.nanmean(x, axis=0)
    sds = np.nanstd(x, axis=0, ddof=0)
    keep = np.isfinite(sds) & (sds > 1e-12)
    if int(keep.sum()) < 10:
        raise ValueError("Too few nonconstant genomic markers remain.")
    z = (x[:, keep] - means[keep]) / sds[keep]
    if not np.isfinite(z).all():
        raise ValueError("Genomic matrix contains non-finite values after standardization.")
    k = (z @ z.T) / z.shape[1]
    k = 0.5 * (k + k.T)
    mean_diag = float(np.mean(np.diag(k)))
    if not np.isfinite(mean_diag) or mean_diag <= 0:
        raise ValueError("Invalid genomic relationship matrix scaling.")
    k /= mean_diag
    return k, {
        "markers_input": float(x.shape[1]),
        "markers_nonconstant": float(keep.sum()),
        "mean_diagonal": float(np.mean(np.diag(k))),
    }


def phenotype_long(pheno: pd.DataFrame) -> pd.DataFrame:
    """Convert the complete line x environment matrix to one row per cell."""

    if tuple(pheno.columns) != EXPECTED_ENVIRONMENTS:
        raise ValueError("Phenotype environments do not match the locked Case Study B order.")
    genotype_ids = list(map(str, pheno.index))
    g_map = {gid: idx for idx, gid in enumerate(genotype_ids)}
    e_map = {env: idx for idx, env in enumerate(EXPECTED_ENVIRONMENTS)}
    rows: list[dict[str, object]] = []
    for gid in genotype_ids:
        for env in EXPECTED_ENVIRONMENTS:
            value = float(pheno.loc[gid, env])
            if not np.isfinite(value):
                raise ValueError("Case Study B baseline requires the locked complete phenotype grid.")
            rows.append(
                {
                    "genotype_id": gid,
                    "environment": env,
                    "g_idx": g_map[gid],
                    "e_idx": e_map[env],
                    "observed": value,
                }
            )
    return pd.DataFrame(rows)


def _environment_baseline(
    y: np.ndarray,
    e_idx: np.ndarray,
    use_environment: bool,
) -> tuple[float, dict[int, float], np.ndarray]:
    global_mean = float(np.mean(y))
    env_means: dict[int, float] = {}
    if use_environment:
        for env in np.unique(e_idx):
            env_means[int(env)] = float(np.mean(y[e_idx == env]))
        baseline = np.asarray([env_means[int(env)] for env in e_idx], dtype=float)
    else:
        baseline = np.full(len(y), global_mean, dtype=float)
    return global_mean, env_means, baseline


def _baseline_predict(
    model: FittedKernelModel,
    test_e: np.ndarray,
) -> np.ndarray:
    if model.model in (MODEL_GE, MODEL_GXE):
        return np.asarray(
            [model.environment_means.get(int(env), model.global_mean) for env in test_e],
            dtype=float,
        )
    return np.full(len(test_e), model.global_mean, dtype=float)


def _kernel_train_matvec(
    vector: np.ndarray,
    train_g: np.ndarray,
    train_e: np.ndarray,
    k_genomic: np.ndarray,
    gamma: float,
) -> np.ndarray:
    """Apply K_G + gamma K_GxE without materializing a cell-level dense kernel."""

    n_genotypes = k_genomic.shape[0]
    v = np.asarray(vector, dtype=float)
    by_g = np.bincount(train_g, weights=v, minlength=n_genotypes)
    out = (k_genomic @ by_g)[train_g]
    if gamma > 0:
        interaction = np.zeros_like(v)
        for env in np.unique(train_e):
            mask = train_e == env
            by_g_env = np.bincount(train_g[mask], weights=v[mask], minlength=n_genotypes)
            interaction[mask] = (k_genomic @ by_g_env)[train_g[mask]]
        out = out + gamma * interaction
    return out


def _kernel_cross_predict(
    coefficients: np.ndarray,
    train_g: np.ndarray,
    train_e: np.ndarray,
    test_g: np.ndarray,
    test_e: np.ndarray,
    k_genomic: np.ndarray,
    gamma: float,
) -> np.ndarray:
    n_genotypes = k_genomic.shape[0]
    by_g = np.bincount(train_g, weights=coefficients, minlength=n_genotypes)
    out = k_genomic[np.asarray(test_g, dtype=int)] @ by_g
    if gamma > 0:
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
        out = out + gamma * interaction
    return np.asarray(out, dtype=float)


def fit_model(
    y: np.ndarray,
    train_g: np.ndarray,
    train_e: np.ndarray,
    k_genomic: np.ndarray,
    model_name: str,
    alpha: float | None = None,
    gamma: float = 0.0,
) -> FittedKernelModel:
    """Fit one baseline on a training partition only."""

    y = np.asarray(y, dtype=float)
    train_g = np.asarray(train_g, dtype=int)
    train_e = np.asarray(train_e, dtype=int)
    if not (len(y) == len(train_g) == len(train_e)):
        raise ValueError("Training vectors must have identical length.")

    use_environment = model_name in (MODEL_GE, MODEL_GXE, MODEL_ENV)
    global_mean, env_means, baseline = _environment_baseline(y, train_e, use_environment)

    if model_name == MODEL_ENV:
        return FittedKernelModel(
            model=model_name,
            alpha=None,
            gamma=0.0,
            global_mean=global_mean,
            environment_means=env_means,
            train_g=train_g,
            train_e=train_e,
            coefficients=None,
            cg_iterations=0,
        )

    if model_name not in (MODEL_G, MODEL_GE, MODEL_GXE):
        raise ValueError(f"Unknown model: {model_name}")
    if alpha is None or alpha <= 0:
        raise ValueError("A positive ridge alpha is required for genomic models.")
    if model_name != MODEL_GXE:
        gamma = 0.0

    residual = y - baseline
    n = len(y)
    diagonal = np.diag(k_genomic)[train_g] * (1.0 + gamma) + float(alpha)

    operator = LinearOperator(
        shape=(n, n),
        dtype=float,
        matvec=lambda v: _kernel_train_matvec(v, train_g, train_e, k_genomic, gamma)
        + float(alpha) * v,
    )
    preconditioner = LinearOperator(
        shape=(n, n),
        dtype=float,
        matvec=lambda v: np.asarray(v, dtype=float) / diagonal,
    )
    iterations = 0

    def _callback(_: np.ndarray) -> None:
        nonlocal iterations
        iterations += 1

    coefficients, info = cg(
        operator,
        residual,
        M=preconditioner,
        rtol=1e-7,
        atol=0.0,
        maxiter=1000,
        callback=_callback,
    )
    if info != 0 or not np.isfinite(coefficients).all():
        raise RuntimeError(
            f"Kernel ridge CG failed for {model_name}: info={info}, iterations={iterations}"
        )

    return FittedKernelModel(
        model=model_name,
        alpha=float(alpha),
        gamma=float(gamma),
        global_mean=global_mean,
        environment_means=env_means,
        train_g=train_g,
        train_e=train_e,
        coefficients=np.asarray(coefficients, dtype=float),
        cg_iterations=iterations,
    )


def predict_model(
    fitted: FittedKernelModel,
    test_g: np.ndarray,
    test_e: np.ndarray,
    k_genomic: np.ndarray,
) -> np.ndarray:
    baseline = _baseline_predict(fitted, np.asarray(test_e, dtype=int))
    if fitted.coefficients is None:
        return baseline
    genomic = _kernel_cross_predict(
        fitted.coefficients,
        fitted.train_g,
        fitted.train_e,
        np.asarray(test_g, dtype=int),
        np.asarray(test_e, dtype=int),
        k_genomic,
        fitted.gamma,
    )
    return baseline + genomic


def _candidate_grid(model_name: str) -> list[tuple[float, float]]:
    if model_name in (MODEL_G, MODEL_GE):
        return [(float(alpha), 0.0) for alpha in ALPHA_GRID]
    if model_name == MODEL_GXE:
        return [
            (float(alpha), float(gamma))
            for alpha in ALPHA_GRID
            for gamma in GAMMA_GRID
        ]
    raise ValueError(f"No tuning grid for {model_name}")


def tune_hyperparameters(
    train: pd.DataFrame,
    k_genomic: np.ndarray,
    model_name: str,
) -> tuple[float, float, float]:
    """Select alpha/gamma with genotype-grouped inner CV inside the outer training data."""

    groups = train["genotype_id"].astype(str).to_numpy()
    unique_groups = np.unique(groups)
    if len(unique_groups) < INNER_SPLITS:
        raise ValueError("Too few genotypes for inner grouped validation.")
    splitter = GroupKFold(n_splits=INNER_SPLITS)
    y_all = train["observed"].to_numpy(dtype=float)
    g_all = train["g_idx"].to_numpy(dtype=int)
    e_all = train["e_idx"].to_numpy(dtype=int)

    best: tuple[float, float, float] | None = None
    for alpha, gamma in _candidate_grid(model_name):
        squared_errors: list[np.ndarray] = []
        for inner_train_idx, inner_val_idx in splitter.split(train, groups=groups):
            fitted = fit_model(
                y_all[inner_train_idx],
                g_all[inner_train_idx],
                e_all[inner_train_idx],
                k_genomic,
                model_name,
                alpha=alpha,
                gamma=gamma,
            )
            pred = predict_model(
                fitted,
                g_all[inner_val_idx],
                e_all[inner_val_idx],
                k_genomic,
            )
            squared_errors.append((y_all[inner_val_idx] - pred) ** 2)
        rmse = float(np.sqrt(np.mean(np.concatenate(squared_errors))))
        candidate = (rmse, alpha, gamma)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise RuntimeError("Hyperparameter tuning produced no candidate.")
    return float(best[1]), float(best[2]), float(best[0])


def build_splits(
    cells: pd.DataFrame,
    cv_g: pd.DataFrame,
    cv2: pd.DataFrame,
    cv_e: pd.DataFrame,
    cv_ge: pd.DataFrame,
) -> list[SplitDefinition]:
    """Materialize the four validation regimes exactly from the locked manifests."""

    fold_map = cv_g.set_index("genotype_id")["fold"].astype(int).to_dict()
    cell_g_fold = cells["genotype_id"].map(fold_map).to_numpy(dtype=int)
    splits: list[SplitDefinition] = []

    for fold in sorted(cv_g["fold"].unique()):
        test = np.where(cell_g_fold == int(fold))[0]
        train = np.where(cell_g_fold != int(fold))[0]
        splits.append(SplitDefinition("CV-G", f"gfold_{int(fold)}", train, test))

    cv2_map = cv2.set_index("genotype_id")["test_environment"].astype(str).to_dict()
    cv2_test_mask = np.asarray(
        [str(env) == cv2_map[str(gid)] for gid, env in zip(cells["genotype_id"], cells["environment"])],
        dtype=bool,
    )
    splits.append(
        SplitDefinition(
            "CV2",
            "sparse_cell",
            np.where(~cv2_test_mask)[0],
            np.where(cv2_test_mask)[0],
        )
    )

    for row in cv_e.itertuples(index=False):
        env = str(row.environment)
        test_mask = cells["environment"].to_numpy(dtype=str) == env
        splits.append(
            SplitDefinition(
                "CV-E",
                f"heldout_{env}",
                np.where(~test_mask)[0],
                np.where(test_mask)[0],
            )
        )

    for row in cv_ge.itertuples(index=False):
        env = str(row.held_out_environment)
        g_fold = int(row.genotype_fold)
        test_mask = (
            (cell_g_fold == g_fold)
            & (cells["environment"].to_numpy(dtype=str) == env)
        )
        train_mask = (
            (cell_g_fold != g_fold)
            & (cells["environment"].to_numpy(dtype=str) != env)
        )
        splits.append(
            SplitDefinition(
                "CV-GE",
                str(row.scenario),
                np.where(train_mask)[0],
                np.where(test_mask)[0],
            )
        )

    expected = {"CV-G": 5, "CV2": 1, "CV-E": 4, "CV-GE": 20}
    observed = pd.Series([split.regime for split in splits]).value_counts().to_dict()
    if observed != expected:
        raise AssertionError(f"Unexpected validation split counts: {observed}")
    return splits


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan"),
        "rho": predictive_correlation(y_true, y_pred),
    }


def evaluate_splits(
    cells: pd.DataFrame,
    k_genomic: np.ndarray,
    splits: Iterable[SplitDefinition],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit the locked ablation sequence on every validation split."""

    prediction_rows: list[dict[str, object]] = []
    scenario_rows: list[dict[str, object]] = []
    for split in splits:
        train = cells.iloc[split.train_index].reset_index(drop=True)
        test = cells.iloc[split.test_index].reset_index(drop=True)
        if train.empty or test.empty:
            raise RuntimeError(f"Empty partition in {split.regime}/{split.scenario}")

        for model_name in MODEL_SEQUENCE:
            if model_name == MODEL_ENV:
                alpha = None
                gamma = 0.0
                inner_rmse = float("nan")
            else:
                alpha, gamma, inner_rmse = tune_hyperparameters(train, k_genomic, model_name)

            fitted = fit_model(
                train["observed"].to_numpy(dtype=float),
                train["g_idx"].to_numpy(dtype=int),
                train["e_idx"].to_numpy(dtype=int),
                k_genomic,
                model_name,
                alpha=alpha,
                gamma=gamma,
            )
            prediction = predict_model(
                fitted,
                test["g_idx"].to_numpy(dtype=int),
                test["e_idx"].to_numpy(dtype=int),
                k_genomic,
            )
            observed = test["observed"].to_numpy(dtype=float)
            metric = _metrics(observed, prediction)
            scenario_rows.append(
                {
                    "regime": split.regime,
                    "scenario": split.scenario,
                    "model": model_name,
                    "n_train": int(len(train)),
                    "n_test": int(len(test)),
                    "alpha": float(alpha) if alpha is not None else np.nan,
                    "gamma_gxe": float(gamma),
                    "inner_grouped_rmse": inner_rmse,
                    "cg_iterations": int(fitted.cg_iterations),
                    **metric,
                }
            )
            for row, pred in zip(test.itertuples(index=False), prediction):
                prediction_rows.append(
                    {
                        "regime": split.regime,
                        "scenario": split.scenario,
                        "model": model_name,
                        "genotype_id": str(row.genotype_id),
                        "environment": str(row.environment),
                        "observed": float(row.observed),
                        "predicted": float(pred),
                        "error": float(row.observed - pred),
                    }
                )

    predictions = pd.DataFrame(prediction_rows)
    scenario_metrics = pd.DataFrame(scenario_rows)
    return predictions, scenario_metrics


def summarize_predictions(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    environment_rows: list[dict[str, object]] = []
    regime_order = ("CV-G", "CV2", "CV-E", "CV-GE")
    for regime in regime_order:
        for model_name in MODEL_SEQUENCE:
            frame = predictions[
                (predictions["regime"] == regime) & (predictions["model"] == model_name)
            ]
            if frame.empty:
                continue
            summary_rows.append(
                {
                    "regime": regime,
                    "model": model_name,
                    "n_predictions": int(len(frame)),
                    "n_genotypes": int(frame["genotype_id"].nunique()),
                    "n_environments": int(frame["environment"].nunique()),
                    **_metrics(frame["observed"].to_numpy(), frame["predicted"].to_numpy()),
                }
            )
            for env, env_frame in frame.groupby("environment", sort=True):
                environment_rows.append(
                    {
                        "regime": regime,
                        "model": model_name,
                        "environment": env,
                        "n_predictions": int(len(env_frame)),
                        **_metrics(
                            env_frame["observed"].to_numpy(),
                            env_frame["predicted"].to_numpy(),
                        ),
                    }
                )
    return pd.DataFrame(summary_rows), pd.DataFrame(environment_rows)


def paired_cluster_bootstrap(
    predictions: pd.DataFrame,
    regime: str,
    reference_model: str,
    candidate_model: str,
    n_bootstrap: int = BOOTSTRAP_REPS,
    seed: int = SEED,
) -> list[dict[str, object]]:
    """Cluster-bootstrap paired RMSE/MAE deltas over genotype IDs.

    Delta is candidate minus reference; negative values favor the candidate.
    """

    ref = predictions[
        (predictions["regime"] == regime) & (predictions["model"] == reference_model)
    ][["genotype_id", "environment", "observed", "predicted"]].rename(
        columns={"predicted": "pred_ref"}
    )
    cand = predictions[
        (predictions["regime"] == regime) & (predictions["model"] == candidate_model)
    ][["genotype_id", "environment", "observed", "predicted"]].rename(
        columns={"predicted": "pred_cand", "observed": "observed_cand"}
    )
    merged = ref.merge(cand, on=["genotype_id", "environment"], how="inner")
    if len(merged) != len(ref) or len(merged) != len(cand):
        raise ValueError("Paired bootstrap predictions are not aligned exactly.")
    if not np.allclose(merged["observed"], merged["observed_cand"]):
        raise ValueError("Observed values differ across paired models.")

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
    n_groups = len(grouped)
    rng = np.random.default_rng(seed)
    rmse_delta = np.empty(n_bootstrap, dtype=float)
    mae_delta = np.empty(n_bootstrap, dtype=float)
    for b in range(n_bootstrap):
        sample = rng.integers(0, n_groups, size=n_groups)
        n = float(np.sum(arrays["n"][sample]))
        rmse_ref = float(np.sqrt(np.sum(arrays["sq_ref"][sample]) / n))
        rmse_cand = float(np.sqrt(np.sum(arrays["sq_cand"][sample]) / n))
        mae_ref = float(np.sum(arrays["abs_ref"][sample]) / n)
        mae_cand = float(np.sum(arrays["abs_cand"][sample]) / n)
        rmse_delta[b] = rmse_cand - rmse_ref
        mae_delta[b] = mae_cand - mae_ref

    observed_ref = merged["observed"].to_numpy(dtype=float)
    pred_ref = merged["pred_ref"].to_numpy(dtype=float)
    pred_cand = merged["pred_cand"].to_numpy(dtype=float)
    observed_deltas = {
        "rmse": _metrics(observed_ref, pred_cand)["rmse"] - _metrics(observed_ref, pred_ref)["rmse"],
        "mae": _metrics(observed_ref, pred_cand)["mae"] - _metrics(observed_ref, pred_ref)["mae"],
    }
    rows: list[dict[str, object]] = []
    for metric_name, samples in (("rmse", rmse_delta), ("mae", mae_delta)):
        rows.append(
            {
                "regime": regime,
                "reference_model": reference_model,
                "candidate_model": candidate_model,
                "metric": metric_name,
                "delta_candidate_minus_reference": float(observed_deltas[metric_name]),
                "bootstrap_ci_low": float(np.quantile(samples, 0.025)),
                "bootstrap_ci_high": float(np.quantile(samples, 0.975)),
                "bootstrap_probability_improvement": float(np.mean(samples < 0.0)),
                "n_genotype_clusters": int(n_groups),
                "n_bootstrap": int(n_bootstrap),
            }
        )
    return rows


def build_bootstrap_table(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for regime in ("CV-G", "CV2"):
        rows.extend(paired_cluster_bootstrap(predictions, regime, MODEL_G, MODEL_GE))
        rows.extend(paired_cluster_bootstrap(predictions, regime, MODEL_GE, MODEL_GXE))
    return pd.DataFrame(rows)


def plot_ablation(summary: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    regimes = [regime for regime in ("CV-G", "CV2", "CV-E", "CV-GE") if regime in set(summary["regime"])]
    models = list(MODEL_SEQUENCE)
    x = np.arange(len(regimes), dtype=float)
    width = 0.18
    fig, ax = plt.subplots(figsize=(11, 6.5))
    for idx, model_name in enumerate(models):
        values = []
        for regime in regimes:
            row = summary[(summary["regime"] == regime) & (summary["model"] == model_name)]
            values.append(float(row["rmse"].iloc[0]))
        offset = (idx - (len(models) - 1) / 2.0) * width
        bars = ax.bar(x + offset, values, width=width, label=model_name)
        ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=8)
    ax.set_xticks(x, regimes)
    ax.set_ylabel("Out-of-sample RMSE")
    ax.set_title("Case Study B — genomic / environment / G×E information ablation")
    ax.legend(frameon=False, ncol=2)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(destination, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(root: str | Path = ".") -> dict[str, pd.DataFrame]:
    root = Path(root).resolve()
    results_dir = root / "reports" / "results"
    figures_dir = root / "reports" / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Rebuild the locked public data locally so modelling never depends on a manually
    # copied matrix. The acquisition outputs remain under ignored data directories.
    run_data_lock(root)
    interim_dir = root / "data" / "interim" / "case_study_b"
    pheno, geno = load_locked_matrices(interim_dir)
    cells = phenotype_long(pheno)
    k_genomic, k_audit = genomic_relationship(geno)

    cv_g = build_cv_g(pheno.index.tolist())
    cv2 = build_cv2_sparse(pheno.index.tolist(), EXPECTED_ENVIRONMENTS)
    cv_e = build_cv_e(EXPECTED_ENVIRONMENTS)
    cv_ge = build_cv_ge_scenarios(cv_g, EXPECTED_ENVIRONMENTS)
    splits = build_splits(cells, cv_g, cv2, cv_e, cv_ge)

    predictions, scenario_metrics = evaluate_splits(cells, k_genomic, splits)
    summary, environment_metrics = summarize_predictions(predictions)
    bootstrap = build_bootstrap_table(predictions)

    summary_path = results_dir / "case_study_b_model_summary.csv"
    scenario_path = results_dir / "case_study_b_model_scenario_metrics.csv"
    env_path = results_dir / "case_study_b_model_environment_metrics.csv"
    pred_path = results_dir / "case_study_b_model_predictions.csv"
    bootstrap_path = results_dir / "case_study_b_gxe_bootstrap.csv"
    kernel_path = results_dir / "case_study_b_genomic_kernel_audit.csv"
    figure_path = figures_dir / "case_study_b_gxe_ablation.png"

    summary.to_csv(summary_path, index=False)
    scenario_metrics.to_csv(scenario_path, index=False)
    environment_metrics.to_csv(env_path, index=False)
    predictions.to_csv(pred_path, index=False)
    bootstrap.to_csv(bootstrap_path, index=False)
    pd.DataFrame([k_audit]).to_csv(kernel_path, index=False)
    plot_ablation(summary, figure_path)

    print("Case Study B classical GxE baseline complete", flush=True)
    print(summary.to_string(index=False), flush=True)
    print("\nPaired genotype-cluster bootstrap", flush=True)
    print(bootstrap.to_string(index=False), flush=True)
    return {
        "summary": summary,
        "scenario_metrics": scenario_metrics,
        "environment_metrics": environment_metrics,
        "predictions": predictions,
        "bootstrap": bootstrap,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Case Study B classical GxE baselines.")
    parser.add_argument("--output-root", default=".", help="Repository root for outputs.")
    args = parser.parse_args()
    run(args.output_root)


if __name__ == "__main__":
    main()
