"""Deterministic publication assets for Case Study B PUB-B2.

This module is publication-only. It reads already committed frozen artifacts and
formats them into manuscript tables and figures. It performs no model fitting,
no prediction generation, no outcome filtering, and no scientific retuning.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BUILDER_VERSION = "PUB-B2-v1"

INPUTS = {
    "pub_b1_evidence_hierarchy": "reports/results/case_study_b_pub_b1_evidence_hierarchy.csv",
    "b12_available_summary": "reports/results/case_study_b12_2022_available_case_summary.csv",
    "b12_available_coverage": "reports/results/case_study_b12_2022_available_case_coverage.csv",
    "b14c_primary_summary": "reports/results/case_study_b14c_2024_primary_summary.csv",
    "b14c_interval_summary": "reports/results/case_study_b14c_2024_interval_summary.csv",
    "b14c_primary_cohort": "reports/results/case_study_b14c_2024_primary_cohort.csv",
    "b16_error_structure": "reports/results/case_study_b16_2024_error_structure_summary.csv",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(repo_root: Path, key: str) -> pd.DataFrame:
    return pd.read_csv(repo_root / INPUTS[key])


def _save_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _table_01(repo_root: Path) -> pd.DataFrame:
    h = _read(repo_root, "pub_b1_evidence_hierarchy").copy()
    h = h[h["stage"].ne("PUB_B1")].copy()
    return h[["stage", "evidence_class", "terminal_status", "primary_or_secondary", "publication_role", "allowed_use"]]


def _table_02(repo_root: Path) -> pd.DataFrame:
    b12 = _read(repo_root, "b12_available_summary").iloc[0]
    b12cov = _read(repo_root, "b12_available_coverage")
    b12cov = b12cov.loc[b12cov["nominal"].eq(0.9)].iloc[0]
    b14 = _read(repo_root, "b14c_primary_summary").iloc[0]
    b14cov = _read(repo_root, "b14c_interval_summary")
    b14cov = b14cov.loc[b14cov["rule"].eq("FROZEN_B11_90")].iloc[0]

    rows = [
        {
            "stage": "B12_AVAILABLE_CASE",
            "target_year": 2022,
            "evidence_class": "DIAGNOSTIC_NON_CONFIRMATORY",
            "confirmatory": False,
            "n": int(b12["n_evaluated_available_cases"]),
            "n_environments": int(b12["n_environments"]),
            "n_genotypes": int(b12["n_genotypes"]),
            "rmse": float(b12["rmse"]),
            "mae": float(b12["mae"]),
            "r2": float(b12["r2"]),
            "correlation": float(b12["correlation"]),
            "coverage_90": float(b12cov["empirical_coverage"]),
            "environment_balanced_coverage_90": float(b12cov["environment_balanced_coverage"]),
            "cluster_ci95_low": float(b12cov["environment_cluster_ci95_low"]),
            "cluster_ci95_high": float(b12cov["environment_cluster_ci95_high"]),
        },
        {
            "stage": "B14C",
            "target_year": 2024,
            "evidence_class": "COMPLETED_CONFIRMATORY_EXTERNAL_EVALUATION",
            "confirmatory": True,
            "n": int(b14["n_officially_observable"]),
            "n_environments": int(b14["n_environments"]),
            "n_genotypes": int(b14["n_genotypes"]),
            "rmse": float(b14["rmse"]),
            "mae": float(b14["mae"]),
            "r2": float(b14["r2"]),
            "correlation": float(b14["correlation"]),
            "coverage_90": float(b14cov["empirical_coverage"]),
            "environment_balanced_coverage_90": float(b14cov["environment_balanced_coverage"]),
            "cluster_ci95_low": float(b14cov["cluster_ci_low"]),
            "cluster_ci95_high": float(b14cov["cluster_ci_high"]),
        },
    ]
    return pd.DataFrame(rows)


def _table_03(repo_root: Path) -> pd.DataFrame:
    d = _read(repo_root, "b14c_interval_summary").copy()
    d["publication_decision"] = d["rule"].map(
        {
            "FROZEN_B11_90": "RETAIN_FROZEN_CONTROL",
            "ONE_SIDED_CLUSTER_DRIFT_GUARD_90": "REJECT_PROMOTION",
        }
    )
    return d


def _table_04(repo_root: Path) -> pd.DataFrame:
    d = _read(repo_root, "b16_error_structure").iloc[0]
    return pd.DataFrame(
        [
            {
                "n_cells": int(d["n_cells"]),
                "n_environments": int(d["n_environments"]),
                "raw_rmse": float(d["raw_rmse"]),
                "environment_bias_sse_fraction": float(d["environment_bias_sse_fraction"]),
                "within_environment_sse_fraction": float(d["within_environment_sse_fraction"]),
                "oracle_environment_intercept_corrected_rmse_diagnostic_only": float(d["oracle_environment_intercept_corrected_rmse"]),
                "median_environment_pearson": float(d["median_environment_pearson"]),
                "median_environment_spearman": float(d["median_environment_spearman"]),
                "median_predicted_to_observed_sd_ratio": float(d["median_predicted_to_observed_sd_ratio"]),
                "publication_class": "POSTOUTCOME_DIAGNOSTIC_NO_MODEL_REPAIR",
            }
        ]
    )


def _figure_01(path: Path) -> None:
    stages = ["B12", "B13", "B13A/S", "B14A", "B14B", "B14C", "B16", "B17", "Closure", "B18", "PUB-B1", "PUB-B2"]
    fig, ax = plt.subplots(figsize=(12, 3.8))
    x = list(range(len(stages)))
    ax.plot(x, [0] * len(x), marker="o")
    for i, label in enumerate(stages):
        y = 0.18 if i % 2 == 0 else -0.18
        ax.text(i, y, label, ha="center", va="center", fontsize=9)
    ax.set_xlim(-0.5, len(stages) - 0.5)
    ax.set_ylim(-0.45, 0.45)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title("Case Study B: seal-first external-validation and publication chronology")
    for spine in ["left", "right", "top"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, format="svg")
    plt.close(fig)


def _figure_02(repo_root: Path, path: Path) -> None:
    d = _read(repo_root, "b14c_primary_cohort")
    summary = _read(repo_root, "b14c_primary_summary").iloc[0]
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.scatter(d["observed"], d["predicted"], s=12, alpha=0.45)
    lo = min(float(d["observed"].min()), float(d["predicted"].min()))
    hi = max(float(d["observed"].max()), float(d["predicted"].max()))
    ax.plot([lo, hi], [lo, hi], linestyle="--", linewidth=1)
    ax.set_xlabel("Observed yield")
    ax.set_ylabel("Sealed prediction")
    ax.set_title("2024 sealed external point prediction")
    ax.text(
        0.03,
        0.97,
        f"n={int(summary['n_officially_observable'])}\nRMSE={float(summary['rmse']):.3f}\nR²={float(summary['r2']):.3f}\nr={float(summary['correlation']):.3f}",
        transform=ax.transAxes,
        va="top",
    )
    fig.tight_layout()
    fig.savefig(path, format="svg")
    plt.close(fig)


def _figure_03(repo_root: Path, path: Path) -> None:
    d = _read(repo_root, "b14c_interval_summary").copy()
    x = list(range(len(d)))
    y = d["environment_balanced_coverage"].astype(float).to_numpy()
    low = d["cluster_ci_low"].astype(float).to_numpy()
    high = d["cluster_ci_high"].astype(float).to_numpy()
    yerr = [y - low, high - y]
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.errorbar(x, y, yerr=yerr, fmt="o", capsize=5)
    ax.axhline(0.90, linestyle="--", linewidth=1)
    ax.set_xticks(x, ["Frozen B11 90%", "One-sided drift guard"])
    ax.set_ylabel("Environment-balanced coverage")
    ax.set_ylim(0.84, 1.0)
    ax.set_title("2024 uncertainty-rule comparison")
    for i, row in d.reset_index(drop=True).iterrows():
        ax.text(i, float(row["cluster_ci_low"]) - 0.012, f"score={float(row['mean_interval_score']):.2f}\npass={bool(row['calibration_pass'])}", ha="center", va="top", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, format="svg")
    plt.close(fig)


def _figure_04(repo_root: Path, path: Path) -> None:
    d = _read(repo_root, "b16_error_structure").iloc[0]
    labels = ["Environment-offset\nSSE fraction", "Within-environment\nSSE fraction", "Predicted/observed\nSD ratio"]
    vals = [
        float(d["environment_bias_sse_fraction"]),
        float(d["within_environment_sse_fraction"]),
        float(d["median_predicted_to_observed_sd_ratio"]),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    bars = ax.bar(labels, vals)
    ax.set_ylim(0, 0.7)
    ax.set_ylabel("Ratio / fraction")
    ax.set_title("2024 postoutcome error-structure diagnostic")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.3f}", ha="center")
    fig.tight_layout()
    fig.savefig(path, format="svg")
    plt.close(fig)


def build_publication_assets(repo_root: str | Path = ".", output_dir: str | Path | None = None) -> dict[str, Path]:
    root = Path(repo_root).resolve()
    out = Path(output_dir).resolve() if output_dir is not None else root / "reports" / "publication" / "case_study_b"
    out.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    tables = {
        "table_01_evidence_hierarchy": _table_01(root),
        "table_02_external_validation_metrics": _table_02(root),
        "table_03_2024_uncertainty_comparison": _table_03(root),
        "table_04_2024_failure_structure": _table_04(root),
    }
    for name, df in tables.items():
        path = out / f"case_study_b_pub_b2_{name}.csv"
        _save_table(df, path)
        outputs[name] = path

    figures = {
        "figure_01_protocol_chronology": lambda p: _figure_01(p),
        "figure_02_2024_external_point_prediction": lambda p: _figure_02(root, p),
        "figure_03_2024_uncertainty_comparison": lambda p: _figure_03(root, p),
        "figure_04_2024_failure_structure": lambda p: _figure_04(root, p),
    }
    for name, fn in figures.items():
        path = out / f"case_study_b_pub_b2_{name}.svg"
        fn(path)
        outputs[name] = path

    figure_manifest = pd.DataFrame(
        [
            ["Figure 1", "case_study_b_pub_b2_figure_01_protocol_chronology.svg", "PUB-B1 evidence hierarchy + stage decisions", "Protocol chronology", "PRIMARY_PROVENANCE"],
            ["Figure 2", "case_study_b_pub_b2_figure_02_2024_external_point_prediction.svg", INPUTS["b14c_primary_cohort"], "Observed versus immutable sealed prediction on 779 officially observable keys", "CONFIRMATORY_EXTERNAL"],
            ["Figure 3", "case_study_b_pub_b2_figure_03_2024_uncertainty_comparison.svg", INPUTS["b14c_interval_summary"], "Frozen control versus predeclared one-sided drift guard", "CONFIRMATORY_EXTERNAL"],
            ["Figure 4", "case_study_b_pub_b2_figure_04_2024_failure_structure.svg", INPUTS["b16_error_structure"], "Postoutcome diagnostic decomposition and under-dispersion", "DIAGNOSTIC_ONLY"],
        ],
        columns=["figure", "file", "authoritative_source", "publication_role", "evidence_class"],
    )
    fm_path = out / "case_study_b_pub_b2_figure_manifest.csv"
    _save_table(figure_manifest, fm_path)
    outputs["figure_manifest"] = fm_path

    table_manifest = pd.DataFrame(
        [
            ["Table 1", "case_study_b_pub_b2_table_01_evidence_hierarchy.csv", INPUTS["pub_b1_evidence_hierarchy"], "Evidence hierarchy"],
            ["Table 2", "case_study_b_pub_b2_table_02_external_validation_metrics.csv", f"{INPUTS['b12_available_summary']}|{INPUTS['b12_available_coverage']}|{INPUTS['b14c_primary_summary']}|{INPUTS['b14c_interval_summary']}", "2022 diagnostic versus 2024 confirmatory external metrics"],
            ["Table 3", "case_study_b_pub_b2_table_03_2024_uncertainty_comparison.csv", INPUTS["b14c_interval_summary"], "2024 uncertainty-rule comparison"],
            ["Table 4", "case_study_b_pub_b2_table_04_2024_failure_structure.csv", INPUTS["b16_error_structure"], "Postoutcome failure structure"],
        ],
        columns=["table", "file", "authoritative_source", "publication_role"],
    )
    tm_path = out / "case_study_b_pub_b2_table_manifest.csv"
    _save_table(table_manifest, tm_path)
    outputs["table_manifest"] = tm_path

    manifest_rows = []
    for key, rel in INPUTS.items():
        p = root / rel
        manifest_rows.append({"kind": "INPUT", "name": key, "path": rel, "sha256": _sha256(p), "builder_version": BUILDER_VERSION})
    for key, p in sorted(outputs.items()):
        manifest_rows.append({"kind": "OUTPUT", "name": key, "path": str(p.relative_to(root)) if p.is_relative_to(root) else str(p), "sha256": _sha256(p), "builder_version": BUILDER_VERSION})
    manifest = pd.DataFrame(manifest_rows)
    manifest_path = out / "case_study_b_pub_b2_assets_manifest.csv"
    _save_table(manifest, manifest_path)
    outputs["assets_manifest"] = manifest_path
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    outputs = build_publication_assets(args.repo_root, args.output_dir)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
