from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from plant_intelligence.models.evaluation import evaluate_predictions

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
RESULTS = ROOT / "reports" / "results"
FIGURES = ROOT / "reports" / "figures"


def _load_inputs() -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame]:
    X = np.load(DATA / "processed" / "case_study_a" / "genotype_matrix_qc.npy", mmap_mode="r")
    accessions = pd.read_csv(DATA / "processed" / "case_study_a" / "model_accessions.csv")
    folds = pd.read_csv(DATA / "processed" / "case_study_a" / "genotype_aware_folds.csv")
    phen = pd.read_csv(DATA / "interim" / "case_study_a" / "shoot_regeneration_accession_summary.csv")

    if X.shape[0] != len(accessions):
        raise ValueError("Genotype matrix and accession index are misaligned.")

    index = accessions.reset_index().rename(columns={"index": "row_index"})
    fold_map = index.merge(folds, on="accession_id", how="inner", validate="one_to_one")
    if len(fold_map) != len(accessions):
        raise ValueError("Every modelling accession must have exactly one genotype-aware fold.")

    return X, fold_map, phen


def _build_longitudinal_frame(fold_map: pd.DataFrame, phen: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for protocol in ("a", "b"):
        d15 = phen.loc[
            phen["phenotype_name"] == f"shoots 15d protocol {protocol}",
            ["accession_id", "phenotype_mean"],
        ].rename(columns={"phenotype_mean": "x15"})
        d21 = phen.loc[
            phen["phenotype_name"] == f"shoots 21d protocol {protocol}",
            ["accession_id", "phenotype_mean"],
        ].rename(columns={"phenotype_mean": "y21"})

        paired = d15.merge(d21, on="accession_id", how="inner", validate="one_to_one")
        paired["protocol"] = protocol.upper()
        paired["protocol_b"] = 1.0 if protocol == "b" else 0.0
        rows.append(paired)

    frame = pd.concat(rows, ignore_index=True)
    frame = frame.merge(fold_map, on="accession_id", how="inner", validate="many_to_one")
    if frame.empty:
        raise ValueError("No longitudinal observations overlap the genomic modelling population.")
    return frame


def _fit_genomic_projection(X_train: np.ndarray, X_test: np.ndarray):
    marker_scaler = StandardScaler()
    X_train_scaled = marker_scaler.fit_transform(X_train)
    X_test_scaled = marker_scaler.transform(X_test)

    pca = PCA(n_components=0.90, svd_solver="full")
    Z_train = pca.fit_transform(X_train_scaled)
    Z_test = pca.transform(X_test_scaled)
    return Z_train, Z_test, int(pca.n_components_)


def _design(Z: np.ndarray, protocol_b: np.ndarray, x15: np.ndarray, specification: str) -> np.ndarray:
    if specification == "G":
        return Z
    if specification == "G+P":
        return np.column_stack([Z, protocol_b])
    if specification == "G+P+X15":
        return np.column_stack([Z, protocol_b, x15])
    raise ValueError(f"Unknown forecasting specification: {specification}")


def run_early_forecasting() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    X, fold_map, phen = _load_inputs()
    frame = _build_longitudinal_frame(fold_map, phen)

    specifications = ("G", "G+P", "G+P+X15")
    predictions = []
    fold_metrics = []
    pca_rows = []

    for fold in sorted(frame["fold"].unique()):
        test = frame["fold"] == fold
        train = ~test

        train_accession_rows = frame.loc[train, ["accession_id", "row_index"]].drop_duplicates()
        test_accession_rows = frame.loc[test, ["accession_id", "row_index"]].drop_duplicates()

        Z_train_unique, Z_test_unique, n_components = _fit_genomic_projection(
            np.asarray(X[train_accession_rows["row_index"].to_numpy(dtype=int)]),
            np.asarray(X[test_accession_rows["row_index"].to_numpy(dtype=int)]),
        )

        train_lookup = {
            accession: Z_train_unique[i]
            for i, accession in enumerate(train_accession_rows["accession_id"].astype(str))
        }
        test_lookup = {
            accession: Z_test_unique[i]
            for i, accession in enumerate(test_accession_rows["accession_id"].astype(str))
        }

        Z_train = np.vstack([train_lookup[str(a)] for a in frame.loc[train, "accession_id"]])
        Z_test = np.vstack([test_lookup[str(a)] for a in frame.loc[test, "accession_id"]])

        y_train = frame.loc[train, "y21"].to_numpy(dtype=float)
        y_test = frame.loc[test, "y21"].to_numpy(dtype=float)
        p_train = frame.loc[train, "protocol_b"].to_numpy(dtype=float)
        p_test = frame.loc[test, "protocol_b"].to_numpy(dtype=float)
        x15_train = frame.loc[train, "x15"].to_numpy(dtype=float)
        x15_test = frame.loc[test, "x15"].to_numpy(dtype=float)

        pca_rows.append({"fold": int(fold), "n_pca_components": n_components})

        for specification in specifications:
            D_train = _design(Z_train, p_train, x15_train, specification)
            D_test = _design(Z_test, p_test, x15_test, specification)

            scaler = StandardScaler()
            D_train = scaler.fit_transform(D_train)
            D_test = scaler.transform(D_test)

            model = Ridge(alpha=10.0)
            model.fit(D_train, y_train)
            y_pred = model.predict(D_test)

            part = pd.DataFrame(
                {
                    "accession_id": frame.loc[test, "accession_id"].to_numpy(),
                    "protocol": frame.loc[test, "protocol"].to_numpy(),
                    "fold": int(fold),
                    "specification": specification,
                    "x15": x15_test,
                    "y_true": y_test,
                    "y_pred": y_pred,
                }
            )
            predictions.append(part)

    predictions_df = pd.concat(predictions, ignore_index=True)
    summary_rows = []

    for specification, group in predictions_df.groupby("specification", sort=False):
        fm, overall = evaluate_predictions(group, fold_col="fold")
        fm.insert(0, "specification", specification)
        fold_metrics.append(fm)

        pooled = overall.iloc[0].to_dict()
        pooled.update({"specification": specification, "scope": "pooled"})
        summary_rows.append(pooled)

        for protocol, pg in group.groupby("protocol"):
            _, protocol_overall = evaluate_predictions(pg, fold_col="fold")
            row = protocol_overall.iloc[0].to_dict()
            row.update({"specification": specification, "scope": f"protocol_{protocol}"})
            summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    fold_metrics_df = pd.concat(fold_metrics, ignore_index=True)
    pca_df = pd.DataFrame(pca_rows)

    pooled = summary_df.loc[summary_df["scope"] == "pooled"].set_index("specification")
    baseline_rmse = float(pooled.loc["G", "rmse"])
    baseline_mae = float(pooled.loc["G", "mae"])
    summary_df["rmse_improvement_vs_G"] = np.nan
    summary_df["mae_improvement_vs_G"] = np.nan
    pooled_mask = summary_df["scope"] == "pooled"
    summary_df.loc[pooled_mask, "rmse_improvement_vs_G"] = baseline_rmse - summary_df.loc[pooled_mask, "rmse"]
    summary_df.loc[pooled_mask, "mae_improvement_vs_G"] = baseline_mae - summary_df.loc[pooled_mask, "mae"]

    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(RESULTS / "case_study_a_early_forecasting_predictions.csv", index=False)
    fold_metrics_df.to_csv(RESULTS / "case_study_a_early_forecasting_fold_metrics.csv", index=False)
    summary_df.to_csv(RESULTS / "case_study_a_early_forecasting_summary.csv", index=False)
    pca_df.to_csv(RESULTS / "case_study_a_early_forecasting_pca.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    plot_df = summary_df.loc[summary_df["scope"] == "pooled"].copy()
    ax.bar(plot_df["specification"], plot_df["rmse"])
    ax.set_ylabel("Out-of-fold RMSE")
    ax.set_xlabel("Information available at prediction time")
    ax.set_title("Case Study A — Does early biological information improve Day-21 forecasting?")
    for i, value in enumerate(plot_df["rmse"]):
        ax.text(i, value, f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES / "case_study_a_early_forecasting.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    return predictions_df, fold_metrics_df, summary_df


def main():
    _, _, summary = run_early_forecasting()
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
