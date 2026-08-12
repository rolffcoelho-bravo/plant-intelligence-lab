from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "reports" / "results"
FIGURES = ROOT / "reports" / "figures"
SEED = 20260812
BUDGETS = (5, 10, 20, 30, 50)
RANDOM_REPEATS = 5000


def _load_candidates() -> pd.DataFrame:
    path = RESULTS / "case_study_a_uncertainty_predictions.csv"
    frame = pd.read_csv(path)
    required = {
        "accession_id", "protocol", "fold", "x15", "y_true", "y_pred",
        "half_width_90", "outside_calibration_range", "abstain",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required Step-07 columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("The Step-07 candidate table is empty.")
    return frame.copy()


def _rank(frame: pd.DataFrame, strategy: str) -> pd.DataFrame:
    ranked = frame.copy()
    if strategy == "predicted_response":
        ranked["acquisition_score"] = ranked["y_pred"]
    elif strategy == "uncertainty":
        ranked["acquisition_score"] = ranked["half_width_90"]
    elif strategy == "balanced":
        pred_rank = ranked["y_pred"].rank(pct=True, method="average")
        unc_rank = ranked["half_width_90"].rank(pct=True, method="average")
        ranked["acquisition_score"] = 0.5 * pred_rank + 0.5 * unc_rank
    else:
        raise ValueError(f"Unknown acquisition strategy: {strategy}")
    return ranked.sort_values(["acquisition_score", "y_pred"], ascending=False).reset_index(drop=True)


def _metrics(selected: pd.DataFrame, high_value_threshold: float) -> dict[str, float]:
    return {
        "mean_observed_response": float(selected["y_true"].mean()),
        "max_observed_response": float(selected["y_true"].max()),
        "high_value_hits": int((selected["y_true"] >= high_value_threshold).sum()),
        "high_value_hit_rate": float((selected["y_true"] >= high_value_threshold).mean()),
        "mean_uncertainty_half_width_90": float(selected["half_width_90"].mean()),
        "protocol_diversity": int(selected["protocol"].nunique()),
    }


def run_active_selection() -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = _load_candidates()
    rng = np.random.default_rng(SEED)
    high_value_threshold = float(frame["y_true"].quantile(0.90))
    strategies = ("predicted_response", "uncertainty", "balanced")
    summary_rows: list[dict] = []
    selection_rows: list[pd.DataFrame] = []

    for budget in BUDGETS:
        if budget > len(frame):
            continue

        random_stats = []
        for _ in range(RANDOM_REPEATS):
            idx = rng.choice(len(frame), size=budget, replace=False)
            random_stats.append(_metrics(frame.iloc[idx], high_value_threshold))
        random_df = pd.DataFrame(random_stats)
        random_row = {
            "strategy": "random",
            "budget": budget,
            "high_value_threshold": high_value_threshold,
        }
        for col in random_df.columns:
            random_row[col] = float(random_df[col].mean())
            random_row[f"{col}_q05"] = float(random_df[col].quantile(0.05))
            random_row[f"{col}_q95"] = float(random_df[col].quantile(0.95))
        summary_rows.append(random_row)

        for strategy in strategies:
            ranked = _rank(frame, strategy)
            selected = ranked.head(budget).copy()
            selected["strategy"] = strategy
            selected["budget"] = budget
            selection_rows.append(selected)
            row = {
                "strategy": strategy,
                "budget": budget,
                "high_value_threshold": high_value_threshold,
                **_metrics(selected, high_value_threshold),
            }
            row["mean_response_lift_vs_random"] = row["mean_observed_response"] - random_row["mean_observed_response"]
            row["hit_rate_lift_vs_random"] = row["high_value_hit_rate"] - random_row["high_value_hit_rate"]
            summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    selections = pd.concat(selection_rows, ignore_index=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    summary.to_csv(RESULTS / "case_study_a_active_selection_summary.csv", index=False)
    selections.to_csv(RESULTS / "case_study_a_active_selection_candidates.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5.8))
    for strategy, group in summary.groupby("strategy", sort=False):
        group = group.sort_values("budget")
        ax.plot(group["budget"], group["high_value_hit_rate"], marker="o", label=strategy.replace("_", " ").title())
    ax.set_xlabel("Experimental budget")
    ax.set_ylabel("High-value outcome discovery rate")
    ax.set_title("Case Study A — Active experiment selection vs random allocation")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "case_study_a_active_selection.png", dpi=240, bbox_inches="tight")
    plt.close(fig)
    return selections, summary


def main():
    _, summary = run_active_selection()
    cols = [
        "strategy", "budget", "mean_observed_response", "high_value_hit_rate",
        "mean_response_lift_vs_random", "hit_rate_lift_vs_random",
    ]
    print(summary[[c for c in cols if c in summary.columns]].to_string(index=False))


if __name__ == "__main__":
    main()
