"""Case Study B10: forecast-time-safe prediction and Value of Waiting.

B10 consumes the B9 issuance-safe environmental states without redefining their
horizons. The primary deployment benchmark is the forward-year manifest frozen
in B9. B5 CV-E and CV-GE remain secondary continuity checks.

The model family is intentionally fixed and small:

    G -> G + E_T0 -> G + E_T1 -> G + E_T2

No B10 hyperparameter search is performed. The genomic/environmental
representation is frozen before seeing B10 performance at the modal B6-R
configuration selected in 3/5 outer folds: genomic rank 20, environmental rank
16, environmental gamma multiplier 2, ridge alpha 10.

T0 uses prior-year climatology plus static/known-at-issuance context; T1 uses
weather observed through 30 DAP; T2 uses weather observed through 60 DAP. B10
never admits future realized weather, observed future phenology, or outcome
fields into an earlier forecast state.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plant_intelligence.models.maize_environment_transfer import (
    BOOTSTRAP_REPS,
    _attach_folds,
    _load_manifests,
    prepare_cells,
)
from plant_intelligence.models.maize_environment_transfer_robustness import (
    TransferConfig,
    cell_features,
    environment_map,
    genomic_map,
    load_materialized,
    metrics,
    predict,
)

SEED = 20260813

# Frozen before B10 performance is observed. This is the modal B6-R selected
# configuration (3/5 outer folds); all B6-R selections also used g_rank=20 and
# alpha=10. B10 does not tune these values.
FROZEN_CONFIG = TransferConfig(
    "b6r_modal_environment_narrower",
    g_rank=20,
    e_rank=16,
    gamma_multiplier=2.0,
    alpha=10.0,
)

MODEL_ORDER = ("G", "G+E_T0", "G+E_T1", "G+E_T2")
STATE_BY_MODEL = {
    "G+E_T0": "T0_preseason",
    "G+E_T1": "T1_30DAP",
    "G+E_T2": "T2_60DAP_reproductive_window_proxy",
}
WEATHER_COLUMNS = (
    "wx_t2m",
    "wx_t2m_min",
    "wx_t2m_max",
    "wx_prectotcorr",
    "wx_allsky_sfc_sw_dwn",
    "wx_rh2m",
    "wx_ws2m",
)
PAIR_SPECS = (
    ("G+E_T0", "G", "preseason_environment_value"),
    ("G+E_T1", "G+E_T0", "wait_T0_to_T1"),
    ("G+E_T2", "G+E_T1", "wait_T1_to_T2"),
    ("G+E_T2", "G+E_T0", "wait_T0_to_T2"),
    ("G+E_T2", "G", "total_environment_value_T2"),
)


def _as_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().eq("true")


def _year_from_environment(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values.astype(str).str.slice(0, 4), errors="raise").astype(int)


def validate_b9_inputs(
    states: pd.DataFrame,
    environment_manifest: pd.DataFrame,
    forward_manifest: pd.DataFrame,
) -> None:
    required_states = {
        "environment",
        "horizon",
        "planting_date",
        "uses_future_weather",
        "uses_observed_phenology",
        "ssurgo_mukey",
        *WEATHER_COLUMNS,
    }
    if not required_states.issubset(states.columns):
        missing = sorted(required_states.difference(states.columns))
        raise ValueError(f"B9 safe-state table is missing required columns: {missing}")
    if _as_bool(states["uses_future_weather"]).any():
        raise ValueError("B10 refuses B9 states containing future realized weather.")
    if _as_bool(states["uses_observed_phenology"]).any():
        raise ValueError("B10 refuses B9 states containing observed future phenology.")

    expected_horizons = set(STATE_BY_MODEL.values())
    observed_horizons = set(states["horizon"].astype(str))
    if observed_horizons != expected_horizons:
        raise ValueError(
            f"B10 requires exactly the three frozen B9 horizons; found {sorted(observed_horizons)}"
        )
    counts = states.groupby(["environment", "horizon"]).size()
    if not (counts == 1).all():
        raise ValueError("B9 safe states must contain exactly one row per environment/horizon.")

    required_env = {"environment", "year", "planting_date", "latitude", "longitude"}
    if not required_env.issubset(environment_manifest.columns):
        raise ValueError("B9 environment manifest is missing date/coordinate fields required by B10.")
    if environment_manifest["environment"].astype(str).duplicated().any():
        raise ValueError("B9 environment manifest must contain one row per environment.")

    required_forward = {"scenario", "test_year", "environment", "train_year_max", "admission"}
    if not required_forward.issubset(forward_manifest.columns):
        raise ValueError("B9 forward-year manifest is missing required lock fields.")
    if not (forward_manifest["train_year_max"].astype(int) < forward_manifest["test_year"].astype(int)).all():
        raise ValueError("B10 refuses a forward-year manifest that violates temporal order.")
    if not forward_manifest["admission"].astype(str).eq("FORWARD_YEAR_LOCKED").all():
        raise ValueError("B10 requires the pre-registered B9 FORWARD_YEAR_LOCKED manifest.")


def build_environment_state_matrices(
    states: pd.DataFrame,
    environment_manifest: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Create fixed numeric environment representations for the three B9 states.

    All source variables are known at the corresponding issuance date. Static
    SSURGO map-unit identity is one-hot encoded. Planting day-of-year and
    coordinates are known context. Missing plant-population metadata uses a
    deterministic zero + missing-indicator encoding; no test-set statistic is
    used for imputation.
    """

    validate_cols = ["environment", "horizon", "ssurgo_mukey", *WEATHER_COLUMNS]
    if states[validate_cols].isna().any().any():
        # ssurgo_mukey and weather are expected complete from the B9 lock.
        bad = states[validate_cols].columns[states[validate_cols].isna().any()].tolist()
        raise ValueError(f"B10 requires complete locked weather/soil identity fields; missing in {bad}")

    env = environment_manifest.copy()
    env["environment"] = env["environment"].astype(str)
    env = env.set_index("environment").sort_index()
    planting = pd.to_datetime(env["planting_date"], errors="raise")
    doy = planting.dt.dayofyear.astype(float)

    static = states.sort_values(["environment", "horizon"]).drop_duplicates("environment").copy()
    static["environment"] = static["environment"].astype(str)
    static = static.set_index("environment").reindex(env.index)
    if static["ssurgo_mukey"].isna().any():
        raise ValueError("Every B10 environment must retain a B9 SSURGO map-unit identity.")
    soil = pd.get_dummies(
        static["ssurgo_mukey"].astype(str),
        prefix="soil_mukey",
        dtype=float,
    )

    population = pd.to_numeric(env.get("plant_population_proxy", pd.Series(index=env.index, dtype=float)), errors="coerce")
    common = pd.DataFrame(index=env.index)
    common["latitude"] = pd.to_numeric(env["latitude"], errors="raise")
    common["longitude"] = pd.to_numeric(env["longitude"], errors="raise")
    common["planting_doy_sin"] = np.sin(2.0 * np.pi * doy / 365.25)
    common["planting_doy_cos"] = np.cos(2.0 * np.pi * doy / 365.25)
    common["plant_population_proxy"] = population.fillna(0.0)
    common["plant_population_missing"] = population.isna().astype(float)
    common = pd.concat([common, soil], axis=1)

    matrices: dict[str, pd.DataFrame] = {}
    audit_rows: list[dict[str, object]] = []
    for model, horizon in STATE_BY_MODEL.items():
        part = states.loc[states["horizon"].astype(str).eq(horizon)].copy()
        part["environment"] = part["environment"].astype(str)
        part = part.set_index("environment").reindex(env.index)
        weather = part[list(WEATHER_COLUMNS)].apply(pd.to_numeric, errors="raise")
        matrix = pd.concat([weather, common], axis=1).astype(float)
        if matrix.isna().any().any():
            raise ValueError(f"B10 environment matrix {horizon} contains missing values.")
        matrices[horizon] = matrix
        audit_rows.append(
            {
                "model": model,
                "horizon": horizon,
                "n_environments": int(len(matrix)),
                "n_features": int(matrix.shape[1]),
                "n_weather_features": int(len(WEATHER_COLUMNS)),
                "n_static_soil_features": int(soil.shape[1]),
                "includes_coordinates": True,
                "includes_planting_day": True,
                "includes_plant_population_proxy": True,
                "uses_future_weather": False,
                "uses_observed_phenology": False,
            }
        )
    return matrices, pd.DataFrame(audit_rows)


def _g_features(cells: pd.DataFrame, gmap) -> np.ndarray:
    lookup = gmap.lookup()
    return np.vstack([gmap.values[lookup[str(v)]] for v in cells["genotype"]]).astype(np.float32)


def _predict_g(train: pd.DataFrame, test: pd.DataFrame, gmap) -> np.ndarray:
    tg = _g_features(train, gmap)
    vg = _g_features(test, gmap)
    zeros_t = np.zeros((len(train), 1), dtype=np.float32)
    zeros_v = np.zeros((len(test), 1), dtype=np.float32)
    return predict(
        "G",
        tg,
        zeros_t,
        train["observed"].to_numpy(float),
        vg,
        zeros_v,
        FROZEN_CONFIG.alpha,
    )


def _predict_ge(train: pd.DataFrame, test: pd.DataFrame, gmap, emap) -> np.ndarray:
    tg, te = cell_features(train, gmap, emap)
    vg, ve = cell_features(test, gmap, emap)
    return predict(
        "G+E",
        tg,
        te,
        train["observed"].to_numpy(float),
        vg,
        ve,
        FROZEN_CONFIG.alpha,
    )


def _append_prediction(
    store: list[pd.DataFrame],
    test: pd.DataFrame,
    regime: str,
    scenario: str,
    model: str,
    pred: np.ndarray,
    test_year: int | None = None,
) -> None:
    keep = ["genotype", "environment", "observed"]
    for optional in ("environment_fold", "genotype_fold"):
        if optional in test.columns:
            keep.append(optional)
    out = test[keep].copy()
    if "environment_fold" not in out:
        out["environment_fold"] = np.nan
    if "genotype_fold" not in out:
        out["genotype_fold"] = np.nan
    out["regime"] = regime
    out["scenario"] = scenario
    out["model"] = model
    out["predicted"] = np.asarray(pred, float)
    out["test_year"] = int(test_year) if test_year is not None else _year_from_environment(out["environment"])
    out["frozen_config"] = FROZEN_CONFIG.name
    store.append(out)


def _genomic_map_cached(
    cache: dict[tuple[str, ...], object],
    geno: pd.DataFrame,
    geno_id_col: str,
    train_ids: set[str],
):
    key = tuple(sorted(str(v) for v in train_ids))
    if key not in cache:
        cache[key] = genomic_map(geno, geno_id_col, set(key), rank=FROZEN_CONFIG.g_rank)
    return cache[key]


def _append_design(
    store: list[dict[str, object]],
    regime: str,
    scenario: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    test_year: int | None,
    train_year_max: int | None,
) -> None:
    store.append(
        {
            "regime": regime,
            "scenario": scenario,
            "test_year": test_year,
            "train_year_max": train_year_max,
            "n_train_cells": int(len(train)),
            "n_test_cells": int(len(test)),
            "n_train_environments": int(train["environment"].nunique()),
            "n_test_environments": int(test["environment"].nunique()),
            "n_train_genotypes": int(train["genotype"].nunique()),
            "n_test_genotypes": int(test["genotype"].nunique()),
            "g_rank": FROZEN_CONFIG.g_rank,
            "e_rank": FROZEN_CONFIG.e_rank,
            "gamma_multiplier": FROZEN_CONFIG.gamma_multiplier,
            "alpha": FROZEN_CONFIG.alpha,
            "hyperparameter_search_in_b10": False,
            "chronological_lock": bool(test_year is not None and train_year_max is not None),
            "train_year_precedes_test_year": (
                bool(int(train_year_max) < int(test_year))
                if test_year is not None and train_year_max is not None
                else np.nan
            ),
        }
    )


def run_predictions(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pheno, geno, ecov = load_materialized(root)
    cells, geno, _, cols = prepare_cells(pheno, geno, ecov)
    results = root / "reports" / "results"

    states = pd.read_csv(results / "case_study_b9_safe_environment_states.csv")
    env_manifest = pd.read_csv(results / "case_study_b9_environment_manifest.csv")
    forward = pd.read_csv(results / "case_study_b9_forward_year_folds.csv")
    validate_b9_inputs(states, env_manifest, forward)
    state_matrices, feature_audit = build_environment_state_matrices(states, env_manifest)

    # B5 manifests are preserved unchanged as secondary continuity regimes.
    envm, genom = _load_manifests(results)
    cells = _attach_folds(cells, envm, genom)

    predictions: list[pd.DataFrame] = []
    design_rows: list[dict[str, object]] = []
    gcache: dict[tuple[str, ...], object] = {}

    # ------------------------------------------------------------------
    # Primary: forward-year deployment backtest registered in B9.
    # ------------------------------------------------------------------
    env_info = env_manifest[["environment", "year"]].copy()
    env_info["environment"] = env_info["environment"].astype(str)
    env_info["year"] = env_info["year"].astype(int)
    for test_year in sorted(forward["test_year"].astype(int).unique()):
        part = forward.loc[forward["test_year"].astype(int).eq(test_year)]
        train_year_values = part["train_year_max"].astype(int).unique()
        if len(train_year_values) != 1:
            raise ValueError(f"Forward-year {test_year} has an inconsistent train-year lock.")
        train_year_max = int(train_year_values[0])
        if train_year_max >= test_year:
            raise ValueError("Forward-year execution violated the frozen chronology.")
        test_envs = set(part["environment"].astype(str))
        train_envs = set(env_info.loc[env_info["year"] <= train_year_max, "environment"].astype(str))
        train = cells[cells["environment"].astype(str).isin(train_envs)].copy()
        test = cells[cells["environment"].astype(str).isin(test_envs)].copy()
        if train.empty or test.empty:
            raise ValueError(f"Forward-year {test_year} produced an empty train/test partition.")
        if int(_year_from_environment(train["environment"]).max()) >= test_year:
            raise ValueError("Forward-year training cells include the test year or later.")
        if not set(test["environment"].astype(str)).issubset(test_envs):
            raise ValueError("Forward-year test cells are inconsistent with the locked manifest.")

        gmap = _genomic_map_cached(gcache, geno, cols["geno_id"], set(train["genotype"].astype(str)))
        scenario = f"forward_year_{test_year}"
        _append_prediction(
            predictions,
            test,
            "FORWARD-YEAR-B10",
            scenario,
            "G",
            _predict_g(train, test, gmap),
            test_year,
        )
        train_env_ids = set(train["environment"].astype(str))
        erank = min(FROZEN_CONFIG.e_rank, max(1, len(train_env_ids) - 1))
        for model in MODEL_ORDER[1:]:
            horizon = STATE_BY_MODEL[model]
            emap = environment_map(
                state_matrices[horizon],
                train_env_ids,
                erank,
                FROZEN_CONFIG.gamma_multiplier,
            )
            _append_prediction(
                predictions,
                test,
                "FORWARD-YEAR-B10",
                scenario,
                model,
                _predict_ge(train, test, gmap, emap),
                test_year,
            )
        _append_design(
            design_rows,
            "FORWARD-YEAR-B10",
            scenario,
            train,
            test,
            test_year,
            train_year_max,
        )

    # ------------------------------------------------------------------
    # Secondary continuity: original B5 CV-E frozen environment folds.
    # ------------------------------------------------------------------
    for outer in sorted(envm["environment_fold"].unique()):
        outer = int(outer)
        train = cells[cells["environment_fold"] != outer].copy()
        test = cells[cells["environment_fold"] == outer].copy()
        gmap = _genomic_map_cached(gcache, geno, cols["geno_id"], set(train["genotype"].astype(str)))
        scenario = f"efold_{outer}"
        _append_prediction(predictions, test, "CV-E-B10", scenario, "G", _predict_g(train, test, gmap))
        train_env_ids = set(train["environment"].astype(str))
        erank = min(FROZEN_CONFIG.e_rank, max(1, len(train_env_ids) - 1))
        for model in MODEL_ORDER[1:]:
            emap = environment_map(
                state_matrices[STATE_BY_MODEL[model]],
                train_env_ids,
                erank,
                FROZEN_CONFIG.gamma_multiplier,
            )
            _append_prediction(
                predictions,
                test,
                "CV-E-B10",
                scenario,
                model,
                _predict_ge(train, test, gmap, emap),
            )
        _append_design(design_rows, "CV-E-B10", scenario, train, test, None, None)

    # ------------------------------------------------------------------
    # Secondary continuity: B5 double cold start (unseen G + unseen E).
    # ------------------------------------------------------------------
    strict_gmaps: dict[int, object] = {}
    for gf in sorted(genom["genotype_fold"].unique()):
        gf = int(gf)
        train_ids = set(genom.loc[genom["genotype_fold"] != gf, "genotype"].astype(str))
        strict_gmaps[gf] = _genomic_map_cached(gcache, geno, cols["geno_id"], train_ids)

    for outer in sorted(envm["environment_fold"].unique()):
        outer = int(outer)
        train_env_ids = set(envm.loc[envm["environment_fold"] != outer, "environment"].astype(str))
        erank = min(FROZEN_CONFIG.e_rank, max(1, len(train_env_ids) - 1))
        emaps = {
            model: environment_map(
                state_matrices[STATE_BY_MODEL[model]],
                train_env_ids,
                erank,
                FROZEN_CONFIG.gamma_multiplier,
            )
            for model in MODEL_ORDER[1:]
        }
        for gf, gmap in strict_gmaps.items():
            train = cells[(cells["environment_fold"] != outer) & (cells["genotype_fold"] != gf)].copy()
            test = cells[(cells["environment_fold"] == outer) & (cells["genotype_fold"] == gf)].copy()
            if test.empty:
                continue
            scenario = f"efold_{outer}__gfold_{gf}"
            _append_prediction(predictions, test, "CV-GE-B10", scenario, "G", _predict_g(train, test, gmap))
            for model in MODEL_ORDER[1:]:
                _append_prediction(
                    predictions,
                    test,
                    "CV-GE-B10",
                    scenario,
                    model,
                    _predict_ge(train, test, gmap, emaps[model]),
                )
            _append_design(design_rows, "CV-GE-B10", scenario, train, test, None, None)

    out = pd.concat(predictions, ignore_index=True)
    if set(out["model"].unique()) != set(MODEL_ORDER):
        raise ValueError("B10 prediction output does not contain the four frozen model states.")
    return out, pd.DataFrame(design_rows), feature_audit


def summarize(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    order = {name: i for i, name in enumerate(MODEL_ORDER)}
    pooled_rows = []
    year_rows = []
    env_rows = []
    for (regime, model), part in predictions.groupby(["regime", "model"]):
        pooled_rows.append(
            {
                "regime": regime,
                "model": model,
                "n": int(len(part)),
                "n_environments": int(part["environment"].nunique()),
                "n_test_years": int(part["test_year"].nunique()),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    primary = predictions[predictions["regime"].eq("FORWARD-YEAR-B10")]
    for (test_year, model), part in primary.groupby(["test_year", "model"]):
        year_rows.append(
            {
                "test_year": int(test_year),
                "model": model,
                "n": int(len(part)),
                "n_environments": int(part["environment"].nunique()),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    for (regime, environment, model), part in predictions.groupby(["regime", "environment", "model"]):
        env_rows.append(
            {
                "regime": regime,
                "environment": environment,
                "test_year": int(part["test_year"].iloc[0]),
                "model": model,
                "n": int(len(part)),
                **metrics(part["observed"], part["predicted"]),
            }
        )
    pooled = pd.DataFrame(pooled_rows)
    pooled["model_order"] = pooled["model"].map(order)
    pooled = pooled.sort_values(["regime", "model_order"]).reset_index(drop=True)
    years = pd.DataFrame(year_rows)
    if not years.empty:
        years["model_order"] = years["model"].map(order)
        years = years.sort_values(["test_year", "model_order"]).reset_index(drop=True)
    return pooled, years, pd.DataFrame(env_rows)


def _paired_frame(part: pd.DataFrame) -> pd.DataFrame:
    pivot = part.pivot_table(
        index=["genotype", "environment", "observed", "test_year"],
        columns="model",
        values="predicted",
        aggfunc="first",
    ).reset_index()
    missing = [m for m in MODEL_ORDER if m not in pivot.columns]
    if missing:
        raise ValueError(f"B10 paired comparison is missing models: {missing}")
    return pivot


def value_of_waiting(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for regime, part in predictions.groupby("regime"):
        pivot = _paired_frame(part)
        y = pivot["observed"].to_numpy(float)
        for challenger, reference, comparison in PAIR_SPECS:
            rmse_ch = float(np.sqrt(np.mean((y - pivot[challenger].to_numpy(float)) ** 2)))
            rmse_ref = float(np.sqrt(np.mean((y - pivot[reference].to_numpy(float)) ** 2)))
            delta = rmse_ch - rmse_ref
            rows.append(
                {
                    "regime": regime,
                    "comparison": comparison,
                    "challenger": challenger,
                    "reference": reference,
                    "reference_rmse": rmse_ref,
                    "challenger_rmse": rmse_ch,
                    "delta_challenger_minus_reference": delta,
                    "value_of_waiting_rmse": -delta,
                    "pct_rmse_improvement": 100.0 * (-delta) / rmse_ref,
                }
            )
    return pd.DataFrame(rows)


def paired_cluster_bootstrap(
    predictions: pd.DataFrame,
    reps: int = BOOTSTRAP_REPS,
) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for regime, part in predictions.groupby("regime"):
        pivot = _paired_frame(part)
        for challenger, reference, comparison in PAIR_SPECS:
            ae = (pivot["observed"].to_numpy(float) - pivot[challenger].to_numpy(float)) ** 2
            be = (pivot["observed"].to_numpy(float) - pivot[reference].to_numpy(float)) ** 2
            for cluster in ("environment", "test_year"):
                cluster_values = pivot[cluster].astype(str)
                stats = (
                    pd.DataFrame({"cluster": cluster_values, "a": ae, "b": be})
                    .groupby("cluster")
                    .agg(sa=("a", "sum"), sb=("b", "sum"), n=("a", "size"))
                )
                labels = np.asarray(stats.index.astype(str))
                if len(labels) < 2:
                    continue
                delta = float(np.sqrt(np.mean(ae)) - np.sqrt(np.mean(be)))
                boots = np.empty(reps, dtype=float)
                for i in range(reps):
                    sample = rng.choice(labels, size=len(labels), replace=True)
                    chosen = stats.loc[sample]
                    n = float(chosen["n"].sum())
                    boots[i] = np.sqrt(float(chosen["sa"].sum()) / n) - np.sqrt(float(chosen["sb"].sum()) / n)
                vow = -boots
                rows.append(
                    {
                        "regime": regime,
                        "comparison": comparison,
                        "challenger": challenger,
                        "reference": reference,
                        "bootstrap_cluster": cluster,
                        "n_clusters": int(len(labels)),
                        "bootstrap_reps": int(reps),
                        "delta_challenger_minus_reference": delta,
                        "ci95_low": float(np.quantile(boots, 0.025)),
                        "ci95_high": float(np.quantile(boots, 0.975)),
                        "improvement_frequency": float(np.mean(boots < 0.0)),
                        "value_of_waiting_rmse": -delta,
                        "value_of_waiting_ci95_low": float(np.quantile(vow, 0.025)),
                        "value_of_waiting_ci95_high": float(np.quantile(vow, 0.975)),
                    }
                )
    return pd.DataFrame(rows)


def make_figure(summary: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.8, 7.4))
    x = np.arange(len(MODEL_ORDER))
    labels = ["G only", "T0\npre-season", "T1\n30 DAP", "T2\n60 DAP"]
    regime_labels = {
        "FORWARD-YEAR-B10": "Forward year (primary)",
        "CV-E-B10": "B5 CV-E continuity",
        "CV-GE-B10": "B5 CV-GE continuity",
    }
    for regime in ("FORWARD-YEAR-B10", "CV-E-B10", "CV-GE-B10"):
        part = summary[summary["regime"].eq(regime)].set_index("model").loc[list(MODEL_ORDER)]
        ax.plot(x, part["rmse"].to_numpy(float), marker="o", linewidth=2.2, label=regime_labels[regime])
    ax.set_xticks(x, labels)
    ax.set_ylabel("Out-of-sample RMSE")
    ax.set_title("Case Study B10 — forecast-time-safe prediction and Value of Waiting")
    ax.grid(axis="y", alpha=0.25)
    # Keep the legend completely outside the plotting area and horizontal.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
    fig.subplots_adjust(bottom=0.27)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(root: Path) -> dict[str, Path]:
    predictions, design, feature_audit = run_predictions(root)
    summary, year_metrics, environment_metrics = summarize(predictions)
    vow = value_of_waiting(predictions)
    bootstrap = paired_cluster_bootstrap(predictions)

    # Hard post-fit integrity checks: performance is evaluated only after the
    # frozen information states and chronology have already been established.
    primary_design = design[design["regime"].eq("FORWARD-YEAR-B10")]
    if not primary_design["train_year_precedes_test_year"].astype(bool).all():
        raise ValueError("B10 forward-year design failed the chronology integrity check.")
    if sorted(primary_design["test_year"].astype(int).tolist()) != [2016, 2017, 2018, 2019, 2020, 2021]:
        raise ValueError("B10 primary benchmark must retain the six locked B9 test years.")

    results = root / "reports" / "results"
    figures = root / "reports" / "figures"
    results.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary": results / "case_study_b10_forecast_time_summary.csv",
        "forward_year_metrics": results / "case_study_b10_forward_year_metrics.csv",
        "environment_metrics": results / "case_study_b10_environment_metrics.csv",
        "value_of_waiting": results / "case_study_b10_value_of_waiting.csv",
        "bootstrap": results / "case_study_b10_value_of_waiting_bootstrap.csv",
        "design": results / "case_study_b10_design_audit.csv",
        "feature_audit": results / "case_study_b10_feature_audit.csv",
        "figure": figures / "case_study_b10_value_of_waiting.png",
    }
    summary.to_csv(paths["summary"], index=False)
    year_metrics.to_csv(paths["forward_year_metrics"], index=False)
    environment_metrics.to_csv(paths["environment_metrics"], index=False)
    vow.to_csv(paths["value_of_waiting"], index=False)
    bootstrap.to_csv(paths["bootstrap"], index=False)
    design.to_csv(paths["design"], index=False)
    feature_audit.to_csv(paths["feature_audit"], index=False)
    make_figure(summary, paths["figure"])
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Case Study B10 forecast-time-safe prediction.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B10 forecast-time-safe prediction complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
