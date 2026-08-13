"""Case Study B10-R: support-aware forward-time environmental diagnostics.

B10-R does not change the B9 horizons and does not select a new deployment
model. It diagnoses why the B10 T2 state can fail under chronological
forward-year validation.

The analysis has two deliberately separated layers:

1. Outcome-free support diagnostics computed only from each outer training
   environment set and the forecast-time-safe environmental state available at
   T0, T1, or T2.
2. Retrospective error association and a predeclared geometry sensitivity grid
   used to understand the observed B10 T2 failure. The grid is diagnostic only:
   no configuration is promoted as a new champion.

Primary diagnostics include nearest training-environment distance, local kernel
support, maximum training-kernel similarity, a Nyström projection-support
measure, training-kernel effective rank, weather-only novelty, geographic
novelty, and whether city/soil identities have appeared previously.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler

from plant_intelligence.models.maize_environment_transfer import _sqeuclidean, prepare_cells
from plant_intelligence.models.maize_environment_transfer_robustness import (
    TransferConfig,
    environment_map,
    genomic_map,
    load_materialized,
    metrics,
    predict,
)
from plant_intelligence.models.maize_forecast_time_prediction import (
    FROZEN_CONFIG,
    STATE_BY_MODEL,
    WEATHER_COLUMNS,
    build_environment_state_matrices,
    validate_b9_inputs,
)

SEED = 20260813
K_NEIGHBORS = 5

# Diagnostic sensitivity only. The frozen B10 configuration remains the
# reference and no B10-R configuration is selected for deployment.
DIAGNOSTIC_GAMMA_MULTIPLIERS = (0.5, 1.0, 2.0, 4.0)
DIAGNOSTIC_E_RANKS = (8, 16, 32)
DIAGNOSTIC_GRID = tuple(
    TransferConfig(
        name=f"diagnostic_rank{rank}_gamma{gamma:g}",
        g_rank=FROZEN_CONFIG.g_rank,
        e_rank=rank,
        gamma_multiplier=gamma,
        alpha=FROZEN_CONFIG.alpha,
    )
    for rank in DIAGNOSTIC_E_RANKS
    for gamma in DIAGNOSTIC_GAMMA_MULTIPLIERS
)


@dataclass(frozen=True)
class SupportGeometry:
    gamma: float
    effective_rank: float
    retained_rank: int
    median_train_pair_d2: float


def _safe_spearman(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> float:
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    mask = np.isfinite(a) & np.isfinite(b)
    if int(mask.sum()) < 3 or np.std(a[mask]) == 0.0 or np.std(b[mask]) == 0.0:
        return float("nan")
    return float(spearmanr(a[mask], b[mask]).statistic)


def _rank_percentile(reference: np.ndarray, values: np.ndarray) -> np.ndarray:
    ref = np.asarray(reference, dtype=float)
    val = np.asarray(values, dtype=float)
    ref = ref[np.isfinite(ref)]
    if len(ref) == 0:
        return np.full(len(val), np.nan, dtype=float)
    ordered = np.sort(ref)
    return np.searchsorted(ordered, val, side="right") / float(len(ordered))


def support_geometry(
    frame: pd.DataFrame,
    train_ids: set[str],
    test_ids: set[str],
    gamma_multiplier: float = FROZEN_CONFIG.gamma_multiplier,
    retained_rank: int = FROZEN_CONFIG.e_rank,
    prefix: str = "full",
) -> tuple[pd.DataFrame, SupportGeometry]:
    """Compute outcome-free support geometry using training-only scaling.

    Distances are Euclidean in the training-standardized state space. Kernel
    quantities use the same median-distance RBF convention as B6-R/B10.
    Projection support is k_xT K_r^+ k_x for the retained kernel eigenspace,
    clipped to [0,1] for numerical stability; its complement is reported as a
    residual support deficit rather than interpreted as a formal leverage score.
    """

    ids = frame.index.astype(str)
    lookup = {value: i for i, value in enumerate(ids)}
    train = sorted(str(v) for v in train_ids)
    test = sorted(str(v) for v in test_ids)
    missing = [v for v in train + test if v not in lookup]
    if missing:
        raise ValueError(f"Support diagnostic IDs missing from state matrix: {missing[:5]}")
    tr = np.asarray([lookup[v] for v in train], dtype=int)
    ts = np.asarray([lookup[v] for v in test], dtype=int)
    if len(tr) < 2 or len(ts) < 1:
        raise ValueError("Support diagnostics require at least two training and one test environment.")

    x = frame.to_numpy(dtype=float)
    scaler = StandardScaler().fit(x[tr])
    ztr = scaler.transform(x[tr])
    zts = scaler.transform(x[ts])

    d2_train = _sqeuclidean(ztr, ztr)
    upper = d2_train[np.triu_indices_from(d2_train, k=1)]
    positive = upper[upper > 1e-12]
    median_d2 = float(np.median(positive)) if len(positive) else 1.0
    gamma = float(gamma_multiplier / max(median_d2, 1e-12))

    d2 = _sqeuclidean(zts, ztr)
    distances = np.sqrt(d2)
    k = min(K_NEIGHBORS, distances.shape[1])
    nearest = distances.min(axis=1)
    mean5 = np.mean(np.partition(distances, k - 1, axis=1)[:, :k], axis=1)

    train_d = np.sqrt(d2_train.copy())
    np.fill_diagonal(train_d, np.inf)
    train_nearest = train_d.min(axis=1)

    similarities = np.exp(-gamma * d2)
    top_sim = np.partition(similarities, similarities.shape[1] - k, axis=1)[:, -k:]
    max_similarity = similarities.max(axis=1)
    local_density = np.mean(top_sim, axis=1)
    local_mass = np.sum(similarities, axis=1)

    k_train = np.exp(-gamma * d2_train)
    eigenvalues, eigenvectors = np.linalg.eigh(k_train)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    positive_mask = eigenvalues > 1e-10
    positive_values = eigenvalues[positive_mask]
    effective_rank = (
        float(np.square(positive_values.sum()) / np.square(positive_values).sum())
        if len(positive_values)
        else 0.0
    )
    keep = min(int(retained_rank), int(positive_mask.sum()))
    if keep < 1:
        projected = np.zeros(len(test), dtype=float)
    else:
        vals = eigenvalues[:keep]
        vecs = eigenvectors[:, :keep]
        coords = similarities @ vecs
        projected = np.sum(np.square(coords) / vals[None, :], axis=1)
        projected = np.clip(projected, 0.0, 1.0)

    out = pd.DataFrame(
        {
            "environment": test,
            f"{prefix}_nearest_z": nearest,
            f"{prefix}_mean5_z": mean5,
            f"{prefix}_nearest_percentile": _rank_percentile(train_nearest, nearest),
            f"{prefix}_max_training_kernel_similarity": max_similarity,
            f"{prefix}_local_kernel_density5": local_density,
            f"{prefix}_kernel_mass": local_mass,
            f"{prefix}_kernel_projection_support": projected,
            f"{prefix}_kernel_projection_residual": 1.0 - projected,
        }
    )
    geometry = SupportGeometry(
        gamma=gamma,
        effective_rank=effective_rank,
        retained_rank=keep,
        median_train_pair_d2=median_d2,
    )
    return out, geometry


def _haversine_matrix_km(test_latlon: np.ndarray, train_latlon: np.ndarray) -> np.ndarray:
    radius_km = 6371.0088
    lat1 = np.radians(test_latlon[:, 0])[:, None]
    lon1 = np.radians(test_latlon[:, 1])[:, None]
    lat2 = np.radians(train_latlon[:, 0])[None, :]
    lon2 = np.radians(train_latlon[:, 1])[None, :]
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2.0 * radius_km * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def context_support(
    environment_manifest: pd.DataFrame,
    states: pd.DataFrame,
    train_ids: set[str],
    test_ids: set[str],
) -> pd.DataFrame:
    env = environment_manifest.copy()
    env["environment"] = env["environment"].astype(str)
    env = env.set_index("environment")
    train = sorted(str(v) for v in train_ids)
    test = sorted(str(v) for v in test_ids)

    train_latlon = env.loc[train, ["latitude", "longitude"]].to_numpy(float)
    test_latlon = env.loc[test, ["latitude", "longitude"]].to_numpy(float)
    geographic = _haversine_matrix_km(test_latlon, train_latlon)

    train_city = set(env.loc[train, "city"].astype(str).str.strip().str.lower())
    test_city = env.loc[test, "city"].astype(str).str.strip().str.lower()

    static = states.sort_values(["environment", "horizon"]).drop_duplicates("environment").copy()
    static["environment"] = static["environment"].astype(str)
    static = static.set_index("environment")
    train_soil = set(static.loc[train, "ssurgo_mukey"].astype(str))
    test_soil = static.loc[test, "ssurgo_mukey"].astype(str)

    rounded_train = set(
        zip(
            np.round(env.loc[train, "latitude"].to_numpy(float), 4),
            np.round(env.loc[train, "longitude"].to_numpy(float), 4),
        )
    )
    rounded_test = list(
        zip(
            np.round(env.loc[test, "latitude"].to_numpy(float), 4),
            np.round(env.loc[test, "longitude"].to_numpy(float), 4),
        )
    )

    return pd.DataFrame(
        {
            "environment": test,
            "nearest_training_location_km": geographic.min(axis=1),
            "city_seen_previously": [value in train_city for value in test_city],
            "coordinate_seen_previously": [value in rounded_train for value in rounded_test],
            "soil_mukey_seen_previously": [value in train_soil for value in test_soil],
        }
    )


def _forward_partitions(
    environment_manifest: pd.DataFrame,
    forward_manifest: pd.DataFrame,
) -> list[tuple[int, int, set[str], set[str]]]:
    env = environment_manifest.copy()
    env["environment"] = env["environment"].astype(str)
    env["year"] = env["year"].astype(int)
    partitions: list[tuple[int, int, set[str], set[str]]] = []
    for test_year in sorted(forward_manifest["test_year"].astype(int).unique()):
        part = forward_manifest[forward_manifest["test_year"].astype(int).eq(test_year)]
        maxima = part["train_year_max"].astype(int).unique()
        if len(maxima) != 1:
            raise ValueError(f"Inconsistent B9 train_year_max for {test_year}.")
        train_year_max = int(maxima[0])
        if train_year_max >= test_year:
            raise ValueError("B10-R refuses a nonchronological B9 manifest.")
        train_ids = set(env.loc[env["year"] <= train_year_max, "environment"].astype(str))
        test_ids = set(part["environment"].astype(str))
        partitions.append((test_year, train_year_max, train_ids, test_ids))
    return partitions


def build_support_table(
    states: pd.DataFrame,
    environment_manifest: pd.DataFrame,
    forward_manifest: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrices, _ = build_environment_state_matrices(states, environment_manifest)
    rows: list[pd.DataFrame] = []
    geometry_rows: list[dict[str, object]] = []

    for test_year, train_year_max, train_ids, test_ids in _forward_partitions(environment_manifest, forward_manifest):
        context = context_support(environment_manifest, states, train_ids, test_ids)
        for model, horizon in STATE_BY_MODEL.items():
            matrix = matrices[horizon]
            full, full_geometry = support_geometry(
                matrix,
                train_ids,
                test_ids,
                gamma_multiplier=FROZEN_CONFIG.gamma_multiplier,
                retained_rank=FROZEN_CONFIG.e_rank,
                prefix="full",
            )
            weather, weather_geometry = support_geometry(
                matrix.loc[:, list(WEATHER_COLUMNS)],
                train_ids,
                test_ids,
                gamma_multiplier=FROZEN_CONFIG.gamma_multiplier,
                retained_rank=min(FROZEN_CONFIG.e_rank, len(WEATHER_COLUMNS)),
                prefix="weather",
            )
            merged = full.merge(weather, on="environment", validate="one_to_one").merge(
                context,
                on="environment",
                validate="one_to_one",
            )
            merged["test_year"] = test_year
            merged["train_year_max"] = train_year_max
            merged["n_train_environments"] = len(train_ids)
            merged["n_test_environments"] = len(test_ids)
            merged["model"] = model
            merged["horizon"] = horizon
            rows.append(merged)
            geometry_rows.append(
                {
                    "test_year": test_year,
                    "train_year_max": train_year_max,
                    "n_train_environments": len(train_ids),
                    "horizon": horizon,
                    "full_rbf_gamma": full_geometry.gamma,
                    "full_training_kernel_effective_rank": full_geometry.effective_rank,
                    "full_retained_rank": full_geometry.retained_rank,
                    "full_median_train_pair_d2": full_geometry.median_train_pair_d2,
                    "weather_rbf_gamma": weather_geometry.gamma,
                    "weather_training_kernel_effective_rank": weather_geometry.effective_rank,
                    "weather_retained_rank": weather_geometry.retained_rank,
                    "weather_median_train_pair_d2": weather_geometry.median_train_pair_d2,
                }
            )
    return pd.concat(rows, ignore_index=True), pd.DataFrame(geometry_rows)


def merge_b10_errors(support: pd.DataFrame, b10_environment_metrics: pd.DataFrame) -> pd.DataFrame:
    primary = b10_environment_metrics[b10_environment_metrics["regime"].eq("FORWARD-YEAR-B10")].copy()
    wanted = primary[primary["model"].isin(["G+E_T0", "G+E_T1", "G+E_T2"])].copy()
    columns = ["environment", "model", "rmse", "mae", "r2", "correlation"]
    out = support.merge(wanted[columns], on=["environment", "model"], how="left", validate="one_to_one")
    if out[["rmse", "mae"]].isna().any().any():
        raise ValueError("B10-R could not align support diagnostics with B10 environment errors.")
    return out


def build_t2_failure_table(support_with_errors: pd.DataFrame) -> pd.DataFrame:
    t1 = support_with_errors[support_with_errors["model"].eq("G+E_T1")].copy()
    t2 = support_with_errors[support_with_errors["model"].eq("G+E_T2")].copy()
    key = ["environment", "test_year", "train_year_max", "n_train_environments", "n_test_environments"]

    metric_cols = [
        "rmse",
        "mae",
        "full_nearest_z",
        "full_mean5_z",
        "full_nearest_percentile",
        "full_max_training_kernel_similarity",
        "full_local_kernel_density5",
        "full_kernel_mass",
        "full_kernel_projection_support",
        "full_kernel_projection_residual",
        "weather_nearest_z",
        "weather_mean5_z",
        "weather_nearest_percentile",
        "weather_max_training_kernel_similarity",
        "weather_local_kernel_density5",
        "weather_kernel_projection_support",
        "weather_kernel_projection_residual",
        "nearest_training_location_km",
        "city_seen_previously",
        "coordinate_seen_previously",
        "soil_mukey_seen_previously",
    ]
    left = t1[key + metric_cols].rename(columns={c: f"t1_{c}" for c in metric_cols})
    right = t2[key + metric_cols].rename(columns={c: f"t2_{c}" for c in metric_cols})
    out = left.merge(right, on=key, validate="one_to_one")
    out["rmse_t2_minus_t1"] = out["t2_rmse"] - out["t1_rmse"]
    out["mae_t2_minus_t1"] = out["t2_mae"] - out["t1_mae"]

    for name in (
        "full_nearest_z",
        "full_mean5_z",
        "full_nearest_percentile",
        "full_max_training_kernel_similarity",
        "full_local_kernel_density5",
        "full_kernel_mass",
        "full_kernel_projection_support",
        "full_kernel_projection_residual",
        "weather_nearest_z",
        "weather_mean5_z",
        "weather_nearest_percentile",
        "weather_max_training_kernel_similarity",
        "weather_local_kernel_density5",
        "weather_kernel_projection_support",
        "weather_kernel_projection_residual",
    ):
        out[f"delta_{name}_t2_minus_t1"] = out[f"t2_{name}"] - out[f"t1_{name}"]

    out["t2_worse_than_t1"] = out["rmse_t2_minus_t1"] > 0.0
    out["t2_extreme_support_percentile"] = out["t2_full_nearest_percentile"] >= 0.95
    return out


def association_table(failure: pd.DataFrame) -> pd.DataFrame:
    candidates = [
        "n_train_environments",
        "t2_full_nearest_z",
        "t2_full_mean5_z",
        "t2_full_nearest_percentile",
        "t2_full_max_training_kernel_similarity",
        "t2_full_local_kernel_density5",
        "t2_full_kernel_mass",
        "t2_full_kernel_projection_support",
        "t2_full_kernel_projection_residual",
        "t2_weather_nearest_z",
        "t2_weather_mean5_z",
        "t2_weather_nearest_percentile",
        "t2_weather_max_training_kernel_similarity",
        "t2_weather_local_kernel_density5",
        "t2_weather_kernel_projection_support",
        "t2_weather_kernel_projection_residual",
        "t2_nearest_training_location_km",
        "delta_full_nearest_z_t2_minus_t1",
        "delta_full_mean5_z_t2_minus_t1",
        "delta_full_nearest_percentile_t2_minus_t1",
        "delta_full_max_training_kernel_similarity_t2_minus_t1",
        "delta_full_local_kernel_density5_t2_minus_t1",
        "delta_full_kernel_projection_support_t2_minus_t1",
        "delta_full_kernel_projection_residual_t2_minus_t1",
        "delta_weather_nearest_z_t2_minus_t1",
        "delta_weather_nearest_percentile_t2_minus_t1",
        "delta_weather_max_training_kernel_similarity_t2_minus_t1",
        "delta_weather_local_kernel_density5_t2_minus_t1",
        "delta_weather_kernel_projection_support_t2_minus_t1",
        "delta_weather_kernel_projection_residual_t2_minus_t1",
    ]
    rows: list[dict[str, object]] = []
    target = failure["rmse_t2_minus_t1"]
    years = sorted(failure["test_year"].unique())
    for feature in candidates:
        pooled = _safe_spearman(failure[feature], target)
        within = []
        for year in years:
            part = failure[failure["test_year"].eq(year)]
            value = _safe_spearman(part[feature], part["rmse_t2_minus_t1"])
            if np.isfinite(value):
                within.append(value)
        loo = []
        for year in years:
            part = failure[~failure["test_year"].eq(year)]
            value = _safe_spearman(part[feature], part["rmse_t2_minus_t1"])
            if np.isfinite(value):
                loo.append(value)
        rows.append(
            {
                "feature": feature,
                "n_environments": int(len(failure)),
                "pooled_spearman": pooled,
                "median_within_year_spearman": float(np.median(within)) if within else np.nan,
                "n_within_year_estimates": len(within),
                "same_sign_within_year_fraction": (
                    float(np.mean(np.sign(within) == np.sign(pooled))) if within and np.isfinite(pooled) and pooled != 0 else np.nan
                ),
                "leave_one_year_out_min_spearman": float(np.min(loo)) if loo else np.nan,
                "leave_one_year_out_max_spearman": float(np.max(loo)) if loo else np.nan,
                "leave_one_year_out_sign_stability": (
                    float(np.mean(np.sign(loo) == np.sign(pooled))) if loo and np.isfinite(pooled) and pooled != 0 else np.nan
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("pooled_spearman", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def yearly_summary(failure: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, part in failure.groupby("test_year"):
        rows.append(
            {
                "test_year": int(year),
                "train_year_max": int(part["train_year_max"].iloc[0]),
                "n_train_environments": int(part["n_train_environments"].iloc[0]),
                "n_test_environments": int(len(part)),
                "mean_rmse_t2_minus_t1_environment": float(part["rmse_t2_minus_t1"].mean()),
                "median_rmse_t2_minus_t1_environment": float(part["rmse_t2_minus_t1"].median()),
                "fraction_environments_t2_worse": float(part["t2_worse_than_t1"].mean()),
                "median_t1_full_nearest_z": float(part["t1_full_nearest_z"].median()),
                "median_t2_full_nearest_z": float(part["t2_full_nearest_z"].median()),
                "median_t2_full_nearest_percentile": float(part["t2_full_nearest_percentile"].median()),
                "fraction_t2_extreme_support_percentile": float(part["t2_extreme_support_percentile"].mean()),
                "median_t2_max_kernel_similarity": float(part["t2_full_max_training_kernel_similarity"].median()),
                "median_t2_local_kernel_density5": float(part["t2_full_local_kernel_density5"].median()),
                "median_t2_projection_residual": float(part["t2_full_kernel_projection_residual"].median()),
                "median_t2_weather_nearest_z": float(part["t2_weather_nearest_z"].median()),
                "median_t2_geographic_distance_km": float(part["t2_nearest_training_location_km"].median()),
                "fraction_city_seen_previously": float(part["t2_city_seen_previously"].astype(bool).mean()),
                "fraction_coordinate_seen_previously": float(part["t2_coordinate_seen_previously"].astype(bool).mean()),
                "fraction_soil_seen_previously": float(part["t2_soil_mukey_seen_previously"].astype(bool).mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("test_year").reset_index(drop=True)


def support_quartiles(failure: pd.DataFrame) -> pd.DataFrame:
    work = failure.copy()
    work["within_year_t2_novelty_quartile"] = (
        work.groupby("test_year")["t2_full_nearest_z"]
        .transform(lambda s: pd.qcut(s.rank(method="first"), q=4, labels=[1, 2, 3, 4]))
        .astype(int)
    )
    rows = []
    for quartile, part in work.groupby("within_year_t2_novelty_quartile"):
        rows.append(
            {
                "within_year_t2_novelty_quartile": int(quartile),
                "n_environments": int(len(part)),
                "mean_t2_nearest_z": float(part["t2_full_nearest_z"].mean()),
                "mean_rmse_t2_minus_t1": float(part["rmse_t2_minus_t1"].mean()),
                "median_rmse_t2_minus_t1": float(part["rmse_t2_minus_t1"].median()),
                "fraction_t2_worse": float(part["t2_worse_than_t1"].mean()),
            }
        )
    return pd.DataFrame(rows)


def _g_features(cells: pd.DataFrame, gmap) -> np.ndarray:
    lookup = gmap.lookup()
    return np.vstack([gmap.values[lookup[str(value)]] for value in cells["genotype"]]).astype(np.float32)


def geometry_sensitivity(
    root: Path,
    state_matrices: dict[str, pd.DataFrame],
    environment_manifest: pd.DataFrame,
    forward_manifest: pd.DataFrame,
    b10_forward_year_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run a diagnostic T2 geometry grid without selecting a new model."""

    pheno, geno, ecov = load_materialized(root)
    cells, geno, _, cols = prepare_cells(pheno, geno, ecov)
    env_info = environment_manifest[["environment", "year"]].copy()
    env_info["environment"] = env_info["environment"].astype(str)
    env_info["year"] = env_info["year"].astype(int)
    t2_matrix = state_matrices[STATE_BY_MODEL["G+E_T2"]]

    reference_year = (
        b10_forward_year_metrics[b10_forward_year_metrics["model"].eq("G+E_T1")]
        .set_index("test_year")["rmse"]
        .astype(float)
        .to_dict()
    )
    predictions: list[pd.DataFrame] = []
    yearly_rows: list[dict[str, object]] = []

    for test_year, train_year_max, train_envs, test_envs in _forward_partitions(environment_manifest, forward_manifest):
        train = cells[cells["environment"].astype(str).isin(train_envs)].copy()
        test = cells[cells["environment"].astype(str).isin(test_envs)].copy()
        gmap = genomic_map(geno, cols["geno_id"], set(train["genotype"].astype(str)), rank=FROZEN_CONFIG.g_rank)
        train_g = _g_features(train, gmap)
        test_g = _g_features(test, gmap)
        y_train = train["observed"].to_numpy(float)
        y_test = test["observed"].to_numpy(float)

        for cfg in DIAGNOSTIC_GRID:
            effective_rank = min(cfg.e_rank, max(1, len(train_envs) - 1))
            emap = environment_map(t2_matrix, train_envs, effective_rank, cfg.gamma_multiplier)
            ei = emap.lookup()
            train_e = np.vstack([emap.values[ei[str(v)]] for v in train["environment"]]).astype(np.float32)
            test_e = np.vstack([emap.values[ei[str(v)]] for v in test["environment"]]).astype(np.float32)
            pred = predict("G+E", train_g, train_e, y_train, test_g, test_e, cfg.alpha)
            row_metrics = metrics(y_test, pred)
            yearly_rows.append(
                {
                    "test_year": test_year,
                    "train_year_max": train_year_max,
                    "n_train_environments": len(train_envs),
                    "n_test_environments": len(test_envs),
                    "config": cfg.name,
                    "e_rank_requested": cfg.e_rank,
                    "e_rank_effective": int(emap.values.shape[1]),
                    "gamma_multiplier": cfg.gamma_multiplier,
                    "alpha": cfg.alpha,
                    "diagnostic_only_no_selection": True,
                    **row_metrics,
                    "frozen_t1_rmse": float(reference_year[test_year]),
                    "rmse_minus_frozen_t1": float(row_metrics["rmse"] - reference_year[test_year]),
                }
            )
            out = test[["genotype", "environment", "observed"]].copy()
            out["test_year"] = test_year
            out["config"] = cfg.name
            out["predicted"] = pred
            predictions.append(out)

    pred = pd.concat(predictions, ignore_index=True)
    pooled_rows = []
    frozen_t1_pooled = float(
        np.sqrt(
            np.average(
                np.square(
                    b10_forward_year_metrics.loc[
                        b10_forward_year_metrics["model"].eq("G+E_T1"), "rmse"
                    ].to_numpy(float)
                ),
                weights=b10_forward_year_metrics.loc[
                    b10_forward_year_metrics["model"].eq("G+E_T1"), "n"
                ].to_numpy(float),
            )
        )
    )
    for cfg, part in pred.groupby("config"):
        m = metrics(part["observed"], part["predicted"])
        cfg_obj = next(value for value in DIAGNOSTIC_GRID if value.name == cfg)
        pooled_rows.append(
            {
                "config": cfg,
                "e_rank_requested": cfg_obj.e_rank,
                "gamma_multiplier": cfg_obj.gamma_multiplier,
                "alpha": cfg_obj.alpha,
                "n": int(len(part)),
                "diagnostic_only_no_selection": True,
                **m,
                "frozen_t1_pooled_rmse": frozen_t1_pooled,
                "rmse_minus_frozen_t1": float(m["rmse"] - frozen_t1_pooled),
            }
        )
    return pd.DataFrame(yearly_rows), pd.DataFrame(pooled_rows).sort_values(["e_rank_requested", "gamma_multiplier"])


def diagnosis_summary(
    failure: pd.DataFrame,
    associations: pd.DataFrame,
    years: pd.DataFrame,
    geometry_year: pd.DataFrame,
    geometry_pooled: pd.DataFrame,
) -> pd.DataFrame:
    baseline = geometry_pooled[
        geometry_pooled["e_rank_requested"].eq(FROZEN_CONFIG.e_rank)
        & geometry_pooled["gamma_multiplier"].eq(FROZEN_CONFIG.gamma_multiplier)
    ].iloc[0]
    year2016 = geometry_year[geometry_year["test_year"].eq(2016)]
    baseline2016 = year2016[
        year2016["e_rank_requested"].eq(FROZEN_CONFIG.e_rank)
        & year2016["gamma_multiplier"].eq(FROZEN_CONFIG.gamma_multiplier)
    ].iloc[0]
    oracle2016 = year2016.sort_values("rmse").iloc[0]
    oracle_pooled = geometry_pooled.sort_values("rmse").iloc[0]

    top_positive = associations.dropna(subset=["pooled_spearman"]).sort_values("pooled_spearman", ascending=False).iloc[0]
    top_negative = associations.dropna(subset=["pooled_spearman"]).sort_values("pooled_spearman").iloc[0]
    y2016 = years[years["test_year"].eq(2016)].iloc[0]
    later = years[years["test_year"] > 2016]

    rows = [
        {
            "diagnostic": "primary_environment_count",
            "value": float(len(failure)),
            "interpretation": "forward-year held-out environments aligned to B10 T1/T2 errors",
        },
        {
            "diagnostic": "2016_training_environment_count",
            "value": float(y2016["n_train_environments"]),
            "interpretation": "smallest historical environmental support set",
        },
        {
            "diagnostic": "2016_fraction_t2_worse",
            "value": float(y2016["fraction_environments_t2_worse"]),
            "interpretation": "fraction of 2016 environments with higher T2 than T1 RMSE",
        },
        {
            "diagnostic": "2016_median_t2_nearest_percentile",
            "value": float(y2016["median_t2_full_nearest_percentile"]),
            "interpretation": "T2 nearest-distance percentile relative to training-environment spacing",
        },
        {
            "diagnostic": "later_year_median_t2_nearest_percentile",
            "value": float(later["median_t2_full_nearest_percentile"].median()),
            "interpretation": "median across 2017-2021 yearly medians",
        },
        {
            "diagnostic": "strongest_positive_support_error_association",
            "value": float(top_positive["pooled_spearman"]),
            "interpretation": str(top_positive["feature"]),
        },
        {
            "diagnostic": "strongest_negative_support_error_association",
            "value": float(top_negative["pooled_spearman"]),
            "interpretation": str(top_negative["feature"]),
        },
        {
            "diagnostic": "frozen_t2_pooled_rmse_reproduced",
            "value": float(baseline["rmse"]),
            "interpretation": "diagnostic grid cell matching frozen B10 rank/gamma",
        },
        {
            "diagnostic": "2016_frozen_t2_rmse_reproduced",
            "value": float(baseline2016["rmse"]),
            "interpretation": "diagnostic grid cell matching frozen B10 rank/gamma",
        },
        {
            "diagnostic": "2016_diagnostic_grid_min_rmse",
            "value": float(oracle2016["rmse"]),
            "interpretation": f"oracle diagnostic only: {oracle2016['config']}; not selected for deployment",
        },
        {
            "diagnostic": "pooled_diagnostic_grid_min_rmse",
            "value": float(oracle_pooled["rmse"]),
            "interpretation": f"oracle diagnostic only: {oracle_pooled['config']}; not selected for deployment",
        },
    ]
    return pd.DataFrame(rows)


def make_figure(years: pd.DataFrame, geometry_year: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.2))

    left = axes[0]
    left.scatter(years["n_train_environments"], years["mean_rmse_t2_minus_t1_environment"], s=70)
    for _, row in years.iterrows():
        left.annotate(
            str(int(row["test_year"])),
            (row["n_train_environments"], row["mean_rmse_t2_minus_t1_environment"]),
            xytext=(5, 5),
            textcoords="offset points",
        )
    left.axhline(0.0, linewidth=1.0)
    left.set_xlabel("Prior training environments")
    left.set_ylabel("Mean environment RMSE difference: T2 − T1")
    left.set_title("Forward support versus T2 deterioration")
    left.grid(alpha=0.25)

    right = axes[1]
    y2016 = geometry_year[geometry_year["test_year"].eq(2016)]
    for rank in DIAGNOSTIC_E_RANKS:
        part = y2016[y2016["e_rank_requested"].eq(rank)].sort_values("gamma_multiplier")
        right.plot(
            part["gamma_multiplier"],
            part["rmse"],
            marker="o",
            linewidth=2.0,
            label=f"environment rank {rank}",
        )
    frozen_t1 = float(y2016["frozen_t1_rmse"].iloc[0])
    right.axhline(frozen_t1, linestyle="--", linewidth=1.2, label="2016 frozen T1 RMSE")
    right.set_xscale("log", base=2)
    right.set_xticks(list(DIAGNOSTIC_GAMMA_MULTIPLIERS), [str(v) for v in DIAGNOSTIC_GAMMA_MULTIPLIERS])
    right.set_xlabel("T2 RBF gamma multiplier (diagnostic only)")
    right.set_ylabel("2016 forward-year RMSE")
    right.set_title("Does T2 collapse persist across kernel geometry?")
    right.grid(alpha=0.25)
    right.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False)

    fig.suptitle("Case Study B10-R — support-aware forward-time diagnostics", fontsize=15)
    fig.subplots_adjust(bottom=0.25, wspace=0.28)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(root: Path) -> dict[str, Path]:
    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    states = pd.read_csv(results / "case_study_b9_safe_environment_states.csv")
    environment_manifest = pd.read_csv(results / "case_study_b9_environment_manifest.csv")
    forward_manifest = pd.read_csv(results / "case_study_b9_forward_year_folds.csv")
    b10_env = pd.read_csv(results / "case_study_b10_environment_metrics.csv")
    b10_year = pd.read_csv(results / "case_study_b10_forward_year_metrics.csv")

    validate_b9_inputs(states, environment_manifest, forward_manifest)
    support, geometry = build_support_table(states, environment_manifest, forward_manifest)
    support_errors = merge_b10_errors(support, b10_env)
    failure = build_t2_failure_table(support_errors)
    associations = association_table(failure)
    years = yearly_summary(failure)
    quartiles = support_quartiles(failure)
    state_matrices, _ = build_environment_state_matrices(states, environment_manifest)
    geometry_year, geometry_pooled = geometry_sensitivity(
        root,
        state_matrices,
        environment_manifest,
        forward_manifest,
        b10_year,
    )
    diagnosis = diagnosis_summary(failure, associations, years, geometry_year, geometry_pooled)

    # Integrity: B10-R must reproduce the frozen T2 grid cell without selecting
    # a replacement. A small floating tolerance is allowed for CSV round trips.
    b10_t2 = float(
        np.sqrt(
            np.average(
                np.square(b10_year.loc[b10_year["model"].eq("G+E_T2"), "rmse"].to_numpy(float)),
                weights=b10_year.loc[b10_year["model"].eq("G+E_T2"), "n"].to_numpy(float),
            )
        )
    )
    reproduced = geometry_pooled[
        geometry_pooled["e_rank_requested"].eq(FROZEN_CONFIG.e_rank)
        & geometry_pooled["gamma_multiplier"].eq(FROZEN_CONFIG.gamma_multiplier)
    ]
    if len(reproduced) != 1 or not np.isclose(float(reproduced.iloc[0]["rmse"]), b10_t2, atol=1e-8):
        raise ValueError("B10-R failed to reproduce the frozen B10 T2 geometry cell.")
    if not geometry_pooled["diagnostic_only_no_selection"].astype(bool).all():
        raise ValueError("B10-R geometry grid must remain diagnostic-only.")
    if sorted(years["test_year"].astype(int)) != [2016, 2017, 2018, 2019, 2020, 2021]:
        raise ValueError("B10-R must preserve all six B9 forward test years.")

    paths = {
        "support": results / "case_study_b10r_environment_support.csv",
        "geometry": results / "case_study_b10r_kernel_geometry.csv",
        "failure": results / "case_study_b10r_t2_failure_diagnostic.csv",
        "associations": results / "case_study_b10r_support_error_associations.csv",
        "years": results / "case_study_b10r_year_summary.csv",
        "quartiles": results / "case_study_b10r_support_quartiles.csv",
        "geometry_year": results / "case_study_b10r_geometry_sensitivity_by_year.csv",
        "geometry_pooled": results / "case_study_b10r_geometry_sensitivity_pooled.csv",
        "diagnosis": results / "case_study_b10r_diagnosis_summary.csv",
        "figure": figures / "case_study_b10r_support_diagnostic.png",
    }
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    support_errors.to_csv(paths["support"], index=False)
    geometry.to_csv(paths["geometry"], index=False)
    failure.to_csv(paths["failure"], index=False)
    associations.to_csv(paths["associations"], index=False)
    years.to_csv(paths["years"], index=False)
    quartiles.to_csv(paths["quartiles"], index=False)
    geometry_year.to_csv(paths["geometry_year"], index=False)
    geometry_pooled.to_csv(paths["geometry_pooled"], index=False)
    diagnosis.to_csv(paths["diagnosis"], index=False)
    make_figure(years, geometry_year, paths["figure"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Case Study B10-R support-aware diagnostics.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B10-R support-aware diagnostics complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
