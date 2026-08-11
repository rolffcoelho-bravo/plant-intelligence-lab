from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


@dataclass(frozen=True)
class RegressionMetrics:
    rmse: float
    mae: float
    r2: float
    predictive_correlation: float
    n: int


def evaluate_regression(y_true, y_pred) -> RegressionMetrics:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if y_true.size == 0:
        raise ValueError("No finite observations available for evaluation.")

    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred)) if y_true.size > 1 else float("nan")

    if y_true.size > 1 and np.std(y_true) > 0 and np.std(y_pred) > 0:
        rho = float(np.corrcoef(y_true, y_pred)[0, 1])
    else:
        rho = float("nan")

    return RegressionMetrics(rmse=rmse, mae=mae, r2=r2, predictive_correlation=rho, n=int(y_true.size))


def evaluate_predictions(predictions: pd.DataFrame, *, truth_col: str = "y_true", pred_col: str = "y_pred", fold_col: str = "fold") -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {truth_col, pred_col, fold_col}
    missing = required.difference(predictions.columns)
    if missing:
        raise KeyError(f"Missing evaluation columns: {sorted(missing)}")

    fold_rows = []
    for fold, frame in predictions.groupby(fold_col, sort=True):
        metrics = asdict(evaluate_regression(frame[truth_col], frame[pred_col]))
        metrics[fold_col] = fold
        fold_rows.append(metrics)

    fold_metrics = pd.DataFrame(fold_rows)
    overall = pd.DataFrame([asdict(evaluate_regression(predictions[truth_col], predictions[pred_col]))])
    return fold_metrics, overall
