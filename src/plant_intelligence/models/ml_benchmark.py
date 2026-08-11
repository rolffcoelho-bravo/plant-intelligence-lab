from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.dummy import DummyRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .boosting import make_lightgbm, make_xgboost
from .evaluation import evaluate_predictions
from .kernel import make_kernel_ridge
from .linear import make_elastic_net
from .tree import make_random_forest

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
RESULTS = ROOT / "reports" / "results"


def _load_inputs():
    X = np.load(DATA / "processed" / "case_study_a" / "genotype_matrix_qc.npy", mmap_mode="r")
    accessions = pd.read_csv(DATA / "processed" / "case_study_a" / "model_accessions.csv")
    folds = pd.read_csv(DATA / "processed" / "case_study_a" / "genotype_aware_folds.csv")
    phen = pd.read_csv(DATA / "interim" / "case_study_a" / "shoot_regeneration_accession_summary.csv")

    if X.shape[0] != len(accessions):
        raise ValueError(f"Genotype rows ({X.shape[0]}) do not match model accessions ({len(accessions)}).")

    index = accessions.reset_index().rename(columns={"index": "row_index"})
    folds = index.merge(folds, on="accession_id", how="inner", validate="one_to_one")
    if len(folds) != len(accessions):
        raise ValueError("Every model accession must have exactly one genotype-aware fold.")
    return X, folds, phen


def _models():
    # Fixed, conservative specifications keep the outer genotype-aware folds untouched.
    # PCA is fitted inside each training fold by the sklearn pipeline, preventing leakage.
    return {
        "Mean baseline": DummyRegressor(strategy="mean"),
        "Elastic Net": make_elastic_net(alpha=0.1, l1_ratio=0.5),
        "Kernel Ridge": make_kernel_ridge(alpha=1.0, gamma=1e-4, kernel="rbf"),
        "Random Forest": make_random_forest(n_estimators=500, min_samples_leaf=3, max_features="sqrt"),
        "XGBoost": make_xgboost(
            n_estimators=500,
            learning_rate=0.03,
            max_depth=3,
            subsample=0.8,
            colsample_bytree=0.35,
            reg_alpha=0.1,
            reg_lambda=5.0,
        ),
        "LightGBM": make_lightgbm(
            n_estimators=500,
            learning_rate=0.03,
            num_leaves=7,
            min_child_samples=12,
            subsample=0.8,
            colsample_bytree=0.35,
            reg_alpha=0.1,
            reg_lambda=5.0,
        ),
        "PCA + Elastic Net": make_pipeline(
            StandardScaler(),
            PCA(n_components=0.90, svd_solver="full"),
            make_elastic_net(alpha=0.1, l1_ratio=0.5),
        ),
        "PCA + Kernel Ridge": make_pipeline(
            StandardScaler(),
            PCA(n_components=0.90, svd_solver="full"),
            make_kernel_ridge(alpha=1.0, gamma=1e-3, kernel="rbf"),
        ),
    }


def run_benchmark() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    X, fold_map, phen = _load_inputs()
    predictions = []
    fold_metrics = []
    summaries = []

    for phenotype_name in sorted(phen["phenotype_name"].unique()):
        target = phen.loc[phen["phenotype_name"] == phenotype_name, ["accession_id", "phenotype_mean"]]
        frame = fold_map.merge(target, on="accession_id", how="inner", validate="one_to_one")
        if len(frame) < 20:
            continue

        for model_name, prototype in _models().items():
            model_predictions = []
            for fold in sorted(frame["fold"].unique()):
                test = frame["fold"] == fold
                train = ~test
                train_rows = frame.loc[train, "row_index"].to_numpy(dtype=int)
                test_rows = frame.loc[test, "row_index"].to_numpy(dtype=int)
                y_train = frame.loc[train, "phenotype_mean"].to_numpy(dtype=float)
                y_test = frame.loc[test, "phenotype_mean"].to_numpy(dtype=float)

                model = clone(prototype)
                model.fit(np.asarray(X[train_rows]), y_train)
                y_pred = np.asarray(model.predict(np.asarray(X[test_rows])), dtype=float)

                part = pd.DataFrame({
                    "accession_id": frame.loc[test, "accession_id"].to_numpy(),
                    "phenotype_name": phenotype_name,
                    "model": model_name,
                    "fold": int(fold),
                    "y_true": y_test,
                    "y_pred": y_pred,
                })
                model_predictions.append(part)
                predictions.append(part)

            model_predictions = pd.concat(model_predictions, ignore_index=True)
            fm, overall = evaluate_predictions(model_predictions)
            fm.insert(0, "phenotype_name", phenotype_name)
            fm.insert(1, "model", model_name)
            fold_metrics.append(fm)

            row = overall.iloc[0].to_dict()
            row.update({"phenotype_name": phenotype_name, "model": model_name})
            summaries.append(row)

    predictions_df = pd.concat(predictions, ignore_index=True)
    fold_metrics_df = pd.concat(fold_metrics, ignore_index=True)
    summary_df = pd.DataFrame(summaries)

    RESULTS.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(RESULTS / "case_study_a_ml_predictions.csv", index=False)
    fold_metrics_df.to_csv(RESULTS / "case_study_a_ml_fold_metrics.csv", index=False)
    summary_df.to_csv(RESULTS / "case_study_a_ml_summary.csv", index=False)
    return predictions_df, fold_metrics_df, summary_df


def main():
    _, _, summary = run_benchmark()
    print(summary.sort_values(["phenotype_name", "rmse"]).to_string(index=False))


if __name__ == "__main__":
    main()
