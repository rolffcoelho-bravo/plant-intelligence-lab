"""Case Study B10-T: temporal stability of environmental spectral geometry.

B10-T does not fit a new predictor. It audits the already-published B10-R
12-geometry diagnostic grid across the six forward test years (2016-2021) and
asks whether geometry rankings persist enough to justify any adaptive T2
controller.

The primary quantities are:

* adjacent-year Spearman rank correlation;
* Top-k overlap;
* lagged-winner regret: performance in year t+1 of the geometry that won year t;
* per-configuration rank dispersion;
* descriptive alignment between rank inversion and outcome-free support/kernel
  shifts already measured in B10-R.

The final shift analysis is intentionally descriptive. There are only five
adjacent-year transitions, so B10-T does not use these associations to define a
new deployment rule or significance claim.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

GRID_FILE = "case_study_b10r_geometry_sensitivity_by_year.csv"
YEAR_FILE = "case_study_b10r_year_summary.csv"
KERNEL_FILE = "case_study_b10r_kernel_geometry.csv"
T2_HORIZON = "T2_60DAP_reproductive_window_proxy"
EXPECTED_YEARS = (2016, 2017, 2018, 2019, 2020, 2021)
TOP_K = (1, 3, 5)


def validate_inputs(grid: pd.DataFrame, years: pd.DataFrame, kernel: pd.DataFrame) -> None:
    required_grid = {
        "test_year",
        "config",
        "e_rank_requested",
        "gamma_multiplier",
        "diagnostic_only_no_selection",
        "rmse",
        "frozen_t1_rmse",
    }
    missing = required_grid.difference(grid.columns)
    if missing:
        raise ValueError(f"B10-T grid is missing required columns: {sorted(missing)}")

    observed_years = tuple(sorted(grid["test_year"].astype(int).unique()))
    if observed_years != EXPECTED_YEARS:
        raise ValueError(f"B10-T requires years {EXPECTED_YEARS}; found {observed_years}")
    counts = grid.groupby("test_year")["config"].nunique()
    if not (counts == 12).all():
        raise ValueError(f"B10-T requires 12 geometries per year; found {counts.to_dict()}")
    config_sets = [set(part["config"].astype(str)) for _, part in grid.groupby("test_year")]
    if any(s != config_sets[0] for s in config_sets[1:]):
        raise ValueError("B10-T requires the identical geometry family in every year.")

    diagnostic = grid["diagnostic_only_no_selection"]
    if not diagnostic.astype(str).str.lower().eq("true").all():
        raise ValueError("B10-T only accepts the B10-R diagnostic-only geometry grid.")
    if grid["rmse"].isna().any() or (~np.isfinite(grid["rmse"].astype(float))).any():
        raise ValueError("B10-T requires finite RMSE for every year/configuration.")

    required_year = {
        "test_year",
        "n_train_environments",
        "median_t2_full_nearest_z",
        "median_t2_max_kernel_similarity",
        "median_t2_local_kernel_density5",
        "median_t2_projection_residual",
        "median_t2_weather_nearest_z",
    }
    if not required_year.issubset(years.columns):
        raise ValueError("B10-T year support summary is missing required outcome-free fields.")
    if tuple(sorted(years["test_year"].astype(int).unique())) != EXPECTED_YEARS:
        raise ValueError("B10-T year support summary does not cover the locked six years.")

    required_kernel = {
        "test_year",
        "horizon",
        "full_training_kernel_effective_rank",
        "weather_training_kernel_effective_rank",
        "full_rbf_gamma",
        "weather_rbf_gamma",
    }
    if not required_kernel.issubset(kernel.columns):
        raise ValueError("B10-T kernel audit is missing required geometry fields.")
    t2 = kernel.loc[kernel["horizon"].astype(str).eq(T2_HORIZON)]
    if tuple(sorted(t2["test_year"].astype(int).unique())) != EXPECTED_YEARS:
        raise ValueError("B10-T requires one T2 kernel-geometry row per locked year.")


def rank_table(grid: pd.DataFrame) -> pd.DataFrame:
    out = grid.copy()
    out["test_year"] = out["test_year"].astype(int)
    out["rmse"] = out["rmse"].astype(float)
    out["rmse_rank"] = out.groupby("test_year")["rmse"].rank(method="average", ascending=True)
    out["is_year_winner"] = out["rmse_rank"].eq(1.0)
    for k in TOP_K:
        out[f"is_top{k}"] = out["rmse_rank"].le(float(k))
    return out.sort_values(["test_year", "rmse_rank", "config"]).reset_index(drop=True)


def adjacent_rank_stability(ranked: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    years = sorted(ranked["test_year"].astype(int).unique())
    n_cfg = ranked["config"].nunique()
    for year_a, year_b in zip(years[:-1], years[1:]):
        a = ranked.loc[ranked["test_year"].eq(year_a)].set_index("config").sort_index()
        b = ranked.loc[ranked["test_year"].eq(year_b)].set_index("config").sort_index()
        if not a.index.equals(b.index):
            raise ValueError("Adjacent B10-T years do not contain identical configurations.")
        rho = float(spearmanr(a["rmse_rank"], b["rmse_rank"]).statistic)
        mean_abs = float(np.mean(np.abs(a["rmse_rank"].to_numpy() - b["rmse_rank"].to_numpy())))
        winner = str(a["rmse"].idxmin())
        winner_next_rmse = float(b.loc[winner, "rmse"])
        oracle_next = str(b["rmse"].idxmin())
        oracle_next_rmse = float(b.loc[oracle_next, "rmse"])
        frozen_t1 = float(b["frozen_t1_rmse"].iloc[0])
        row: dict[str, object] = {
            "from_year": int(year_a),
            "to_year": int(year_b),
            "spearman_rank_rho": rho,
            "rank_inversion_score": float((1.0 - rho) / 2.0),
            "mean_absolute_rank_change": mean_abs,
            "normalized_mean_absolute_rank_change": float(mean_abs / (n_cfg - 1)),
            "from_year_winner": winner,
            "to_year_oracle_winner": oracle_next,
            "winner_persisted": bool(winner == oracle_next),
            "lagged_winner_next_year_rank": float(b.loc[winner, "rmse_rank"]),
            "lagged_winner_next_year_rmse": winner_next_rmse,
            "to_year_oracle_rmse": oracle_next_rmse,
            "lagged_winner_regret": float(winner_next_rmse - oracle_next_rmse),
            "lagged_winner_relative_regret_pct": float(
                100.0 * (winner_next_rmse - oracle_next_rmse) / oracle_next_rmse
            ),
            "to_year_frozen_t1_rmse": frozen_t1,
            "lagged_winner_beats_frozen_t1": bool(winner_next_rmse < frozen_t1),
        }
        for k in TOP_K:
            top_a = set(a.index[a["rmse_rank"].le(float(k))])
            top_b = set(b.index[b["rmse_rank"].le(float(k))])
            overlap = len(top_a.intersection(top_b))
            row[f"top{k}_overlap_count"] = int(overlap)
            row[f"top{k}_overlap_fraction"] = float(overlap / k)
        rows.append(row)
    return pd.DataFrame(rows)


def configuration_stability(ranked: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for config, part in ranked.groupby("config", sort=True):
        p = part.sort_values("test_year")
        ranks = p["rmse_rank"].to_numpy(dtype=float)
        rows.append(
            {
                "config": str(config),
                "e_rank_requested": int(p["e_rank_requested"].iloc[0]),
                "gamma_multiplier": float(p["gamma_multiplier"].iloc[0]),
                "mean_rank": float(np.mean(ranks)),
                "median_rank": float(np.median(ranks)),
                "rank_sd": float(np.std(ranks, ddof=1)),
                "best_count": int(np.sum(ranks == 1.0)),
                "top3_count": int(np.sum(ranks <= 3.0)),
                "worst_rank": float(np.max(ranks)),
                "best_rank": float(np.min(ranks)),
                "mean_adjacent_abs_rank_change": float(np.mean(np.abs(np.diff(ranks)))),
            }
        )
    return pd.DataFrame(rows).sort_values(["mean_rank", "rank_sd", "config"]).reset_index(drop=True)


def outcome_free_shift_table(
    stability: pd.DataFrame,
    years: pd.DataFrame,
    kernel: pd.DataFrame,
) -> pd.DataFrame:
    year = years.copy()
    year["test_year"] = year["test_year"].astype(int)
    year = year.set_index("test_year").sort_index()
    t2 = kernel.loc[kernel["horizon"].astype(str).eq(T2_HORIZON)].copy()
    t2["test_year"] = t2["test_year"].astype(int)
    t2 = t2.set_index("test_year").sort_index()

    fields = {
        "n_train_environments": year["n_train_environments"].astype(float),
        "median_t2_full_nearest_z": year["median_t2_full_nearest_z"].astype(float),
        "median_t2_max_kernel_similarity": year["median_t2_max_kernel_similarity"].astype(float),
        "median_t2_local_kernel_density5": year["median_t2_local_kernel_density5"].astype(float),
        "median_t2_projection_residual": year["median_t2_projection_residual"].astype(float),
        "median_t2_weather_nearest_z": year["median_t2_weather_nearest_z"].astype(float),
        "t2_full_kernel_effective_rank": t2["full_training_kernel_effective_rank"].astype(float),
        "t2_weather_kernel_effective_rank": t2["weather_training_kernel_effective_rank"].astype(float),
        "t2_full_rbf_gamma": t2["full_rbf_gamma"].astype(float),
        "t2_weather_rbf_gamma": t2["weather_rbf_gamma"].astype(float),
    }

    # Z-score each six-year outcome-free state series only to create a compact
    # descriptive transition-distance index. This index is never used for model
    # selection in B10-T.
    zfields: dict[str, pd.Series] = {}
    for name, series in fields.items():
        sd = float(series.std(ddof=1))
        zfields[name] = (series - float(series.mean())) / sd if sd > 0 else series * 0.0

    rows: list[dict[str, object]] = []
    for _, transition in stability.iterrows():
        a = int(transition["from_year"])
        b = int(transition["to_year"])
        row = transition.to_dict()
        z_diffs = []
        for name, series in fields.items():
            delta = float(series.loc[b] - series.loc[a])
            row[f"delta_{name}"] = delta
            row[f"abs_delta_{name}"] = abs(delta)
            z_diffs.append(float(zfields[name].loc[b] - zfields[name].loc[a]))
        row["outcome_free_shift_index"] = float(np.sqrt(np.mean(np.square(z_diffs))))
        rows.append(row)
    return pd.DataFrame(rows)


def shift_associations(shift: pd.DataFrame) -> pd.DataFrame:
    # With five transitions, these correlations are descriptive diagnostics only.
    candidate_fields = [
        "outcome_free_shift_index",
        "abs_delta_n_train_environments",
        "abs_delta_median_t2_full_nearest_z",
        "abs_delta_median_t2_max_kernel_similarity",
        "abs_delta_median_t2_local_kernel_density5",
        "abs_delta_median_t2_projection_residual",
        "abs_delta_median_t2_weather_nearest_z",
        "abs_delta_t2_full_kernel_effective_rank",
        "abs_delta_t2_weather_kernel_effective_rank",
        "abs_delta_t2_full_rbf_gamma",
        "abs_delta_t2_weather_rbf_gamma",
    ]
    rows = []
    for field in candidate_fields:
        rho_inv = float(spearmanr(shift[field], shift["rank_inversion_score"]).statistic)
        rho_regret = float(spearmanr(shift[field], shift["lagged_winner_regret"]).statistic)
        rows.append(
            {
                "outcome_free_shift_metric": field,
                "n_transitions": int(len(shift)),
                "spearman_vs_rank_inversion": rho_inv,
                "spearman_vs_lagged_winner_regret": rho_regret,
                "descriptive_only_small_n": True,
            }
        )
    return pd.DataFrame(rows).sort_values(
        "spearman_vs_rank_inversion", key=lambda s: s.abs(), ascending=False
    ).reset_index(drop=True)


def summary_table(stability: pd.DataFrame, config: pd.DataFrame) -> pd.DataFrame:
    best_stable = config.iloc[0]
    return pd.DataFrame(
        [
            {
                "n_years": 6,
                "n_adjacent_transitions": int(len(stability)),
                "n_geometries": 12,
                "mean_adjacent_spearman_rho": float(stability["spearman_rank_rho"].mean()),
                "median_adjacent_spearman_rho": float(stability["spearman_rank_rho"].median()),
                "min_adjacent_spearman_rho": float(stability["spearman_rank_rho"].min()),
                "max_adjacent_spearman_rho": float(stability["spearman_rank_rho"].max()),
                "mean_top3_overlap_fraction": float(stability["top3_overlap_fraction"].mean()),
                "winner_persistence_fraction": float(stability["winner_persisted"].mean()),
                "mean_lagged_winner_regret": float(stability["lagged_winner_regret"].mean()),
                "median_lagged_winner_regret": float(stability["lagged_winner_regret"].median()),
                "lagged_winner_beats_frozen_t1_fraction": float(
                    stability["lagged_winner_beats_frozen_t1"].mean()
                ),
                "most_stable_average_rank_config": str(best_stable["config"]),
                "most_stable_average_rank": float(best_stable["mean_rank"]),
                "most_stable_average_rank_sd": float(best_stable["rank_sd"]),
                "controller_admission": "NOT_JUSTIFIED_BY_RANK_PERSISTENCE_AUDIT",
            }
        ]
    )


def plot_stability(ranked: pd.DataFrame, stability: pd.DataFrame, output: Path) -> None:
    pivot = ranked.pivot(index="config", columns="test_year", values="rmse_rank")
    ordered = pivot.mean(axis=1).sort_values().index
    pivot = pivot.loc[ordered]

    # Give the legend/x-label block its own vertical breathing room so the
    # lower-panel title never collides with the upper-panel annotations.
    fig = plt.figure(figsize=(12.5, 9.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[2.1, 1.0], hspace=1.05)
    ax1 = fig.add_subplot(gs[0, 0])
    for config, row in pivot.iterrows():
        ax1.plot(pivot.columns, row.values, marker="o", linewidth=1.2, alpha=0.8, label=config)
    ax1.invert_yaxis()
    ax1.set_title("Case Study B10-T — environmental geometry rank trajectories")
    ax1.set_ylabel("RMSE rank (1 = best)")
    ax1.set_xlabel("Forward test year", labelpad=8)
    ax1.set_xticks(list(EXPECTED_YEARS))
    ax1.grid(alpha=0.2)
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=4, frameon=False, fontsize=8)

    ax2 = fig.add_subplot(gs[1, 0])
    labels = [f"{int(a)}→{int(b)}" for a, b in zip(stability["from_year"], stability["to_year"])]
    x = np.arange(len(labels))
    ax2.bar(x, stability["spearman_rank_rho"].to_numpy(dtype=float), width=0.58)
    ax2.axhline(0.0, linewidth=0.8)
    ax2.set_ylim(-1.0, 1.0)
    ax2.set_ylabel("Adjacent-year Spearman ρ")
    ax2.set_xticks(x, labels)
    ax2.set_title("Year-to-year rank persistence", pad=12)
    ax2.grid(axis="y", alpha=0.2)

    fig.subplots_adjust(top=0.95, bottom=0.08, left=0.09, right=0.98)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run(output_root: Path) -> dict[str, Path]:
    results = output_root / "reports" / "results"
    figures = output_root / "reports" / "figures"
    grid = pd.read_csv(results / GRID_FILE)
    years = pd.read_csv(results / YEAR_FILE)
    kernel = pd.read_csv(results / KERNEL_FILE)
    validate_inputs(grid, years, kernel)

    ranked = rank_table(grid)
    stability = adjacent_rank_stability(ranked)
    configs = configuration_stability(ranked)
    shift = outcome_free_shift_table(stability, years, kernel)
    assoc = shift_associations(shift)
    summary = summary_table(stability, configs)

    outputs = {
        "rank_table": results / "case_study_b10t_geometry_rank_table.csv",
        "rank_stability": results / "case_study_b10t_rank_stability.csv",
        "config_stability": results / "case_study_b10t_config_stability.csv",
        "shift_alignment": results / "case_study_b10t_shift_alignment.csv",
        "shift_associations": results / "case_study_b10t_shift_associations.csv",
        "summary": results / "case_study_b10t_summary.csv",
        "figure": figures / "case_study_b10t_temporal_stability.png",
    }
    ranked.to_csv(outputs["rank_table"], index=False)
    stability.to_csv(outputs["rank_stability"], index=False)
    configs.to_csv(outputs["config_stability"], index=False)
    shift.to_csv(outputs["shift_alignment"], index=False)
    assoc.to_csv(outputs["shift_associations"], index=False)
    summary.to_csv(outputs["summary"], index=False)
    plot_stability(ranked, stability, outputs["figure"])
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Case Study B10-T temporal geometry stability audit")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    outputs = run(args.output_root.resolve())
    print("Case Study B10-T temporal geometry stability audit complete")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()