from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
RESULTS = ROOT / "reports" / "results"
FIGURES = ROOT / "reports" / "figures"


def _load_accession_summary() -> pd.DataFrame:
    path = DATA / "interim" / "case_study_a" / "shoot_regeneration_accession_summary.csv"
    frame = pd.read_csv(path)
    required = {"accession_id", "phenotype_name", "phenotype_mean"}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing required phenotype columns: {sorted(missing)}")
    return frame


def _paired_protocol_frame(frame: pd.DataFrame, day: int) -> pd.DataFrame:
    a_name = f"shoots {day}d protocol a"
    b_name = f"shoots {day}d protocol b"

    a = frame.loc[frame["phenotype_name"] == a_name, ["accession_id", "phenotype_mean"]].rename(
        columns={"phenotype_mean": "protocol_a"}
    )
    b = frame.loc[frame["phenotype_name"] == b_name, ["accession_id", "phenotype_mean"]].rename(
        columns={"phenotype_mean": "protocol_b"}
    )

    paired = a.merge(b, on="accession_id", how="inner", validate="one_to_one")
    paired["day"] = day
    paired["delta_b_minus_a"] = paired["protocol_b"] - paired["protocol_a"]
    paired["absolute_delta"] = paired["delta_b_minus_a"].abs()
    return paired


def _bootstrap_mean_ci(values: np.ndarray, *, n_boot: int = 5000, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    values = np.asarray(values, dtype=float)
    draws = rng.choice(values, size=(n_boot, values.size), replace=True).mean(axis=1)
    low, high = np.quantile(draws, [0.025, 0.975])
    return float(low), float(high)


def analyze_protocol_response() -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = _load_accession_summary()
    paired_frames = []
    rows = []

    for day in (15, 21):
        paired = _paired_protocol_frame(frame, day)
        if len(paired) < 20:
            raise ValueError(f"Insufficient paired protocol observations at day {day}: {len(paired)}")

        delta = paired["delta_b_minus_a"].to_numpy(dtype=float)
        pearson = pearsonr(paired["protocol_a"], paired["protocol_b"])
        spearman = spearmanr(paired["protocol_a"], paired["protocol_b"])
        ci_low, ci_high = _bootstrap_mean_ci(delta)

        rows.append(
            {
                "day": day,
                "n_paired": int(len(paired)),
                "mean_protocol_a": float(paired["protocol_a"].mean()),
                "mean_protocol_b": float(paired["protocol_b"].mean()),
                "mean_delta_b_minus_a": float(delta.mean()),
                "median_delta_b_minus_a": float(np.median(delta)),
                "sd_delta_b_minus_a": float(delta.std(ddof=1)),
                "mean_delta_ci95_low": ci_low,
                "mean_delta_ci95_high": ci_high,
                "fraction_b_greater_a": float(np.mean(delta > 0)),
                "fraction_equal": float(np.mean(delta == 0)),
                "fraction_b_less_a": float(np.mean(delta < 0)),
                "pearson_a_vs_b": float(pearson.statistic),
                "pearson_pvalue": float(pearson.pvalue),
                "spearman_a_vs_b": float(spearman.statistic),
                "spearman_pvalue": float(spearman.pvalue),
            }
        )
        paired_frames.append(paired)

    paired_all = pd.concat(paired_frames, ignore_index=True)
    summary = pd.DataFrame(rows)

    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    paired_all.to_csv(RESULTS / "case_study_a_protocol_response_pairs.csv", index=False)
    summary.to_csv(RESULTS / "case_study_a_protocol_response_summary.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, day in zip(axes, (15, 21)):
        d = paired_all.loc[paired_all["day"] == day]
        ax.scatter(d["protocol_a"], d["protocol_b"], alpha=0.7, s=28)
        max_value = float(max(d["protocol_a"].max(), d["protocol_b"].max()))
        ax.plot([0, max_value], [0, max_value], linewidth=1.0, linestyle="--")
        ax.set_xlabel("Protocol A — accession mean shoots")
        ax.set_ylabel("Protocol B — accession mean shoots")
        ax.set_title(f"Day {day}: within-accession protocol response")
    fig.suptitle("Case Study A — Genotype-specific response across regeneration protocols")
    fig.tight_layout()
    fig.savefig(FIGURES / "case_study_a_protocol_response.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    return paired_all, summary


def main():
    _, summary = analyze_protocol_response()
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
