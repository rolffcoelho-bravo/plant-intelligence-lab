from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "reports" / "results"
FIGURES = ROOT / "reports" / "figures"

LEVELS = (0.80, 0.90, 0.95)


def _finite_sample_quantile(values: np.ndarray, coverage: float) -> float:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        raise ValueError("Calibration residual set is empty.")
    rank = int(np.ceil((values.size + 1) * coverage))
    rank = min(max(rank, 1), values.size)
    return float(np.sort(values)[rank - 1])


def _load_x15_predictions() -> pd.DataFrame:
    path = RESULTS / "case_study_a_early_forecasting_predictions.csv"
    frame = pd.read_csv(path)
    required = {"accession_id", "protocol", "fold", "specification", "x15", "y_true", "y_pred"}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required forecasting columns: {sorted(missing)}")
    frame = frame.loc[frame["specification"] == "X15"].copy()
    if frame.empty:
        raise ValueError("No X15 out-of-fold predictions were found.")
    frame["abs_error"] = (frame["y_true"] - frame["y_pred"]).abs()
    return frame


def run_conformal_uncertainty() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame = _load_x15_predictions()
    interval_rows: list[pd.DataFrame] = []

    # Leave-one-fold-out calibration: each held-out fold is calibrated only from
    # out-of-fold residuals belonging to the other genotype-aware folds.
    for fold in sorted(frame["fold"].unique()):
        test = frame.loc[frame["fold"] == fold].copy()
        calibration = frame.loc[frame["fold"] != fold].copy()

        for protocol in sorted(test["protocol"].unique()):
            test_p = test.loc[test["protocol"] == protocol].copy()
            cal_p = calibration.loc[calibration["protocol"] == protocol].copy()
            if len(cal_p) < 30:
                cal_p = calibration.copy()

            x_low = float(cal_p["x15"].quantile(0.01))
            x_high = float(cal_p["x15"].quantile(0.99))
            test_p["outside_calibration_range"] = (test_p["x15"] < x_low) | (test_p["x15"] > x_high)

            for coverage in LEVELS:
                q = _finite_sample_quantile(cal_p["abs_error"].to_numpy(), coverage)
                label = int(round(coverage * 100))
                test_p[f"lower_{label}"] = test_p["y_pred"] - q
                test_p[f"upper_{label}"] = test_p["y_pred"] + q
                test_p[f"half_width_{label}"] = q
                test_p[f"covered_{label}"] = (
                    (test_p["y_true"] >= test_p[f"lower_{label}"])
                    & (test_p["y_true"] <= test_p[f"upper_{label}"])
                )

            interval_rows.append(test_p)

    intervals = pd.concat(interval_rows, ignore_index=True)

    # Abstention is based on the 90% interval and calibration support. The width
    # threshold is empirical and declared explicitly rather than hidden in a score.
    width_threshold = float(intervals["half_width_90"].quantile(0.75))
    intervals["abstain"] = intervals["outside_calibration_range"] | (
        intervals["half_width_90"] > width_threshold
    )

    coverage_rows = []
    for scope, group in [("pooled", intervals)] + [
        (f"protocol_{p}", g) for p, g in intervals.groupby("protocol")
    ]:
        for coverage in LEVELS:
            label = int(round(coverage * 100))
            coverage_rows.append(
                {
                    "scope": scope,
                    "nominal_coverage": coverage,
                    "empirical_coverage": float(group[f"covered_{label}"].mean()),
                    "mean_interval_width": float((2 * group[f"half_width_{label}"]).mean()),
                    "median_interval_width": float((2 * group[f"half_width_{label}"]).median()),
                    "n": int(len(group)),
                }
            )
    coverage_summary = pd.DataFrame(coverage_rows)

    retained = intervals.loc[~intervals["abstain"]]
    abstained = intervals.loc[intervals["abstain"]]
    abstention_summary = pd.DataFrame(
        [
            {
                "n_total": int(len(intervals)),
                "n_retained": int(len(retained)),
                "n_abstained": int(len(abstained)),
                "retained_fraction": float(len(retained) / len(intervals)),
                "abstained_fraction": float(len(abstained) / len(intervals)),
                "rmse_all": float(np.sqrt(np.mean((intervals["y_true"] - intervals["y_pred"]) ** 2))),
                "rmse_retained": float(np.sqrt(np.mean((retained["y_true"] - retained["y_pred"]) ** 2))) if len(retained) else np.nan,
                "rmse_abstained": float(np.sqrt(np.mean((abstained["y_true"] - abstained["y_pred"]) ** 2))) if len(abstained) else np.nan,
                "mae_all": float(intervals["abs_error"].mean()),
                "mae_retained": float(retained["abs_error"].mean()) if len(retained) else np.nan,
                "mae_abstained": float(abstained["abs_error"].mean()) if len(abstained) else np.nan,
                "width_threshold_90": width_threshold,
            }
        ]
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    intervals.to_csv(RESULTS / "case_study_a_uncertainty_predictions.csv", index=False)
    coverage_summary.to_csv(RESULTS / "case_study_a_uncertainty_coverage.csv", index=False)
    abstention_summary.to_csv(RESULTS / "case_study_a_uncertainty_abstention.csv", index=False)

    order = intervals.sort_values("y_pred").reset_index(drop=True)
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.fill_between(x, order["lower_90"], order["upper_90"], alpha=0.25, label="90% calibrated interval")
    ax.plot(x, order["y_pred"], linewidth=1.5, label="Day-21 forecast")
    ax.scatter(x, order["y_true"], s=13, alpha=0.65, label="Observed Day-21 outcome")
    ax.set_xlabel("Held-out observations ordered by forecast")
    ax.set_ylabel("Regenerated shoots")
    ax.set_title("Case Study A — Uncertainty-aware early biological forecasting")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "case_study_a_uncertainty_intervals.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    return intervals, coverage_summary, abstention_summary


def main():
    _, coverage, abstention = run_conformal_uncertainty()
    print("Coverage summary")
    print(coverage.to_string(index=False))
    print("\nAbstention summary")
    print(abstention.to_string(index=False))


if __name__ == "__main__":
    main()
