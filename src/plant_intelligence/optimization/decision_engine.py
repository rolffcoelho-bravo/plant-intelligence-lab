from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "reports" / "results"
FIGURES = ROOT / "reports" / "figures"
REPORTS = ROOT / "reports"
DEFAULT_BUDGET = 10


def _read_csv(name: str) -> pd.DataFrame:
    path = RESULTS / name
    if not path.exists():
        raise FileNotFoundError(f"Required result file not found: {path}")
    return pd.read_csv(path)


def _load_inputs() -> dict[str, pd.DataFrame]:
    return {
        "forecast": _read_csv("case_study_a_early_forecasting_summary.csv"),
        "uncertainty": _read_csv("case_study_a_uncertainty_predictions.csv"),
        "coverage": _read_csv("case_study_a_uncertainty_coverage.csv"),
        "abstention": _read_csv("case_study_a_uncertainty_abstention.csv"),
        "selection": _read_csv("case_study_a_active_selection_summary.csv"),
    }


def _decision_rankings(uncertainty: pd.DataFrame, budget: int = DEFAULT_BUDGET) -> pd.DataFrame:
    required = {
        "accession_id", "protocol", "x15", "y_pred", "lower_90", "upper_90",
        "half_width_90", "outside_calibration_range", "abstain",
    }
    missing = required.difference(uncertainty.columns)
    if missing:
        raise KeyError(f"Missing uncertainty columns for decision engine: {sorted(missing)}")

    frame = uncertainty.copy()
    frame["pred_rank"] = frame["y_pred"].rank(pct=True, method="average")
    frame["unc_rank"] = frame["half_width_90"].rank(pct=True, method="average")
    frame["balanced_score"] = 0.5 * frame["pred_rank"] + 0.5 * frame["unc_rank"]

    modes: list[pd.DataFrame] = []

    exploit = frame.loc[~frame["abstain"]].sort_values("y_pred", ascending=False).head(budget).copy()
    exploit["mode"] = "EXPLOIT"
    exploit["decision_score"] = exploit["y_pred"]
    exploit["rationale"] = "Highest expected Day-21 response among forecasts retained by the reliability filter."
    modes.append(exploit)

    explore = frame.sort_values(["half_width_90", "y_pred"], ascending=False).head(budget).copy()
    explore["mode"] = "EXPLORE"
    explore["decision_score"] = explore["half_width_90"]
    explore["rationale"] = "Highest calibrated predictive uncertainty; prioritizes information rather than immediate response."
    modes.append(explore)

    balanced = frame.loc[~frame["outside_calibration_range"]].sort_values(
        ["balanced_score", "y_pred"], ascending=False
    ).head(budget).copy()
    balanced["mode"] = "BALANCED"
    balanced["decision_score"] = balanced["balanced_score"]
    balanced["rationale"] = "Balances expected response and uncertainty while remaining inside calibration support."
    modes.append(balanced)

    rankings = pd.concat(modes, ignore_index=True)
    rankings["rank"] = rankings.groupby("mode").cumcount() + 1
    rankings["reliability_status"] = np.where(rankings["abstain"], "ABSTAIN", "FORECAST")

    cols = [
        "mode", "rank", "accession_id", "protocol", "x15", "y_pred", "lower_90", "upper_90",
        "half_width_90", "reliability_status", "decision_score", "rationale",
    ]
    return rankings[cols]


def _headline_summary(inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    forecast = inputs["forecast"]
    coverage = inputs["coverage"]
    abstention = inputs["abstention"].iloc[0]
    selection = inputs["selection"]

    x15 = forecast[(forecast["scope"] == "pooled") & (forecast["specification"] == "X15")].iloc[0]
    cov90 = coverage[(coverage["scope"] == "pooled") & (coverage["nominal_coverage"] == 0.90)].iloc[0]
    sel10 = selection[(selection["strategy"] == "predicted_response") & (selection["budget"] == 10)].iloc[0]
    rnd10 = selection[(selection["strategy"] == "random") & (selection["budget"] == 10)].iloc[0]

    rows = [
        ("Champion forecast", "X15 -> Day 21", "Parsimonious early-phenotype model"),
        ("Out-of-fold R2", float(x15["r2"]), "Forecast skill"),
        ("Out-of-fold RMSE", float(x15["rmse"]), "Forecast error"),
        ("90% empirical coverage", float(cov90["empirical_coverage"]), "Calibrated uncertainty"),
        ("Retained fraction", float(abstention["retained_fraction"]), "Selective prediction"),
        ("Retained RMSE", float(abstention["rmse_retained"]), "Reliability-filtered error"),
        ("Abstained RMSE", float(abstention["rmse_abstained"]), "Difficult-case error"),
        ("Budget-10 guided hit rate", float(sel10["high_value_hit_rate"]), "Retrospective experiment selection"),
        ("Budget-10 random hit rate", float(rnd10["high_value_hit_rate"]), "Random benchmark"),
    ]
    return pd.DataFrame(rows, columns=["metric", "value", "role"])


def _plot_dashboard(inputs: dict[str, pd.DataFrame], summary: pd.DataFrame, path: Path) -> None:
    forecast = inputs["forecast"]
    coverage = inputs["coverage"]
    abstention = inputs["abstention"].iloc[0]
    selection = inputs["selection"]

    fig = plt.figure(figsize=(15, 10), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)

    ax1 = fig.add_subplot(gs[0, 0])
    info = forecast[forecast["scope"] == "pooled"].copy()
    order = ["Mean", "G", "G+P", "X15", "P+X15", "G+X15", "G+P+X15"]
    info["specification"] = pd.Categorical(info["specification"], categories=order, ordered=True)
    info = info.sort_values("specification")
    ax1.bar(info["specification"].astype(str), info["rmse"])
    ax1.set_title("Information value: Day-21 forecast error")
    ax1.set_ylabel("Out-of-fold RMSE")
    ax1.tick_params(axis="x", rotation=28)

    ax2 = fig.add_subplot(gs[0, 1])
    pooled = coverage[coverage["scope"] == "pooled"]
    ax2.plot(pooled["nominal_coverage"], pooled["empirical_coverage"], marker="o", linewidth=2)
    ax2.plot([0.78, 0.97], [0.78, 0.97], linestyle="--", linewidth=1)
    ax2.set_xlim(0.78, 0.97)
    ax2.set_ylim(0.78, 0.97)
    ax2.set_title("Conformal calibration")
    ax2.set_xlabel("Nominal coverage")
    ax2.set_ylabel("Empirical coverage")

    ax3 = fig.add_subplot(gs[1, 0])
    labels = ["All", "Retained", "Abstained"]
    values = [abstention["rmse_all"], abstention["rmse_retained"], abstention["rmse_abstained"]]
    ax3.bar(labels, values)
    ax3.set_title("Selective prediction separates difficult cases")
    ax3.set_ylabel("RMSE")
    for i, value in enumerate(values):
        ax3.text(i, value, f"{value:.2f}", ha="center", va="bottom")

    ax4 = fig.add_subplot(gs[1, 1])
    for strategy, group in selection.groupby("strategy", sort=False):
        group = group.sort_values("budget")
        ax4.plot(group["budget"], group["high_value_hit_rate"], marker="o", label=strategy.replace("_", " ").title())
    ax4.set_title("Experiment-selection efficiency")
    ax4.set_xlabel("Experimental budget")
    ax4.set_ylabel("High-value discovery rate")
    ax4.legend(frameon=False, fontsize=8)

    fig.suptitle("Plant Intelligence Lab - Case Study A Decision Intelligence", fontsize=19, fontweight="bold")
    fig.savefig(path, dpi=260, bbox_inches="tight")
    plt.close(fig)


def _report_page_title(title: str, subtitle: str | None = None):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.07, 0.88, title, fontsize=24, fontweight="bold")
    if subtitle:
        fig.text(0.07, 0.82, subtitle, fontsize=12)
    return fig


def _write_pdf(inputs: dict[str, pd.DataFrame], rankings: pd.DataFrame, summary: pd.DataFrame, path: Path) -> None:
    forecast = inputs["forecast"]
    coverage = inputs["coverage"]
    abstention = inputs["abstention"].iloc[0]
    selection = inputs["selection"]

    with PdfPages(path) as pdf:
        fig = _report_page_title(
            "Plant Intelligence Lab - Case Study A",
            "Integrated Biological Decision Engine | Real-data retrospective validation",
        )
        fig.text(0.07, 0.70, "Forecast -> Uncertainty -> Reliability -> Decision Objective -> Experiment Recommendation", fontsize=14)
        lines = [
            "Champion forecast: X15 -> Day-21 regeneration",
            f"Out-of-fold R2: {float(summary.loc[summary.metric == 'Out-of-fold R2', 'value'].iloc[0]):.3f}",
            f"90% empirical coverage: {float(summary.loc[summary.metric == '90% empirical coverage', 'value'].iloc[0]):.3f}",
            f"Retained RMSE: {float(summary.loc[summary.metric == 'Retained RMSE', 'value'].iloc[0]):.3f}",
            "Decision modes: EXPLOIT | EXPLORE | BALANCED",
        ]
        for i, line in enumerate(lines):
            fig.text(0.09, 0.60 - i * 0.075, line, fontsize=13)
        fig.text(0.07, 0.13, "Interpretation: complexity is retained only when it adds measurable decision value.", fontsize=11)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        info = forecast[forecast["scope"] == "pooled"].copy()
        order = ["Mean", "G", "G+P", "X15", "P+X15", "G+X15", "G+P+X15"]
        info["specification"] = pd.Categorical(info["specification"], categories=order, ordered=True)
        info = info.sort_values("specification")
        ax.bar(info["specification"].astype(str), info["rmse"])
        ax.set_title("Information ablation: what data are worth collecting?", fontsize=18, fontweight="bold")
        ax.set_ylabel("Out-of-fold RMSE")
        ax.tick_params(axis="x", rotation=28)
        for i, v in enumerate(info["rmse"]):
            ax.text(i, v, f"{v:.2f}", ha="center", va="bottom")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        for scope, group in coverage.groupby("scope", sort=False):
            ax.plot(group["nominal_coverage"], group["empirical_coverage"], marker="o", linewidth=2, label=scope.replace("_", " ").title())
        ax.plot([0.78, 0.97], [0.78, 0.97], linestyle="--", linewidth=1)
        ax.set_title("Uncertainty calibration across protocols", fontsize=18, fontweight="bold")
        ax.set_xlabel("Nominal coverage")
        ax.set_ylabel("Empirical coverage")
        ax.legend(frameon=False)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        labels = ["All", "Retained", "Abstained"]
        values = [abstention["rmse_all"], abstention["rmse_retained"], abstention["rmse_abstained"]]
        ax.bar(labels, values)
        ax.set_title("Reliability filter: difficult cases are separated", fontsize=18, fontweight="bold")
        ax.set_ylabel("RMSE")
        for i, v in enumerate(values):
            ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=12)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        for strategy, group in selection.groupby("strategy", sort=False):
            group = group.sort_values("budget")
            ax.plot(group["budget"], group["high_value_hit_rate"], marker="o", linewidth=2, label=strategy.replace("_", " ").title())
        ax.set_title("Retrospective experiment-selection efficiency", fontsize=18, fontweight="bold")
        ax.set_xlabel("Experimental budget")
        ax.set_ylabel("High-value outcome discovery rate")
        ax.legend(frameon=False)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        for mode in ("EXPLOIT", "EXPLORE", "BALANCED"):
            top = rankings[rankings["mode"] == mode].head(5)
            fig = _report_page_title(f"Decision mode: {mode}", top["rationale"].iloc[0] if not top.empty else None)
            y = 0.70
            for _, row in top.iterrows():
                text = (
                    f"#{int(row['rank'])} accession {row['accession_id']} | protocol {row['protocol']} | "
                    f"forecast {row['y_pred']:.2f} | 90% PI [{row['lower_90']:.2f}, {row['upper_90']:.2f}] | "
                    f"status {row['reliability_status']}"
                )
                fig.text(0.08, y, text, fontsize=11)
                y -= 0.105
            fig.text(0.07, 0.12, "Retrospective recommendation only; prospective laboratory validation is required before operational claims.", fontsize=10)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)


def run_decision_engine(budget: int = DEFAULT_BUDGET) -> tuple[pd.DataFrame, pd.DataFrame]:
    inputs = _load_inputs()
    rankings = _decision_rankings(inputs["uncertainty"], budget=budget)
    summary = _headline_summary(inputs)

    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    rankings.to_csv(RESULTS / "case_study_a_decision_recommendations.csv", index=False)
    summary.to_csv(RESULTS / "case_study_a_decision_engine_summary.csv", index=False)

    dashboard_path = FIGURES / "case_study_a_decision_engine.png"
    report_path = REPORTS / "Plant_Intelligence_Lab_Case_Study_A_Decision_Report.pdf"
    _plot_dashboard(inputs, summary, dashboard_path)
    _write_pdf(inputs, rankings, summary, report_path)
    return rankings, summary


def main():
    rankings, summary = run_decision_engine()
    print("Decision engine summary")
    print(summary.to_string(index=False))
    print("\nTop recommendations")
    print(rankings.groupby("mode", sort=False).head(3).to_string(index=False))


if __name__ == "__main__":
    main()
