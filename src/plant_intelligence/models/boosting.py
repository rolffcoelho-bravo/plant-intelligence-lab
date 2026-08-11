from __future__ import annotations

from lightgbm import LGBMRegressor
from xgboost import XGBRegressor


def make_xgboost(*, n_estimators: int = 500, learning_rate: float = 0.03, max_depth: int = 4, subsample: float = 0.8, colsample_bytree: float = 0.8, reg_alpha: float = 0.0, reg_lambda: float = 1.0, random_state: int = 42, n_jobs: int = -1) -> XGBRegressor:
    """Create a regularized XGBoost regressor for high-dimensional genomic prediction."""
    return XGBRegressor(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        reg_alpha=reg_alpha,
        reg_lambda=reg_lambda,
        objective="reg:squarederror",
        random_state=random_state,
        n_jobs=n_jobs,
    )


def make_lightgbm(*, n_estimators: int = 500, learning_rate: float = 0.03, num_leaves: int = 15, min_child_samples: int = 10, subsample: float = 0.8, colsample_bytree: float = 0.8, reg_alpha: float = 0.0, reg_lambda: float = 1.0, random_state: int = 42, n_jobs: int = -1) -> LGBMRegressor:
    """Create a conservative LightGBM regressor for high-dimensional genomic prediction."""
    return LGBMRegressor(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        num_leaves=num_leaves,
        min_child_samples=min_child_samples,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        reg_alpha=reg_alpha,
        reg_lambda=reg_lambda,
        random_state=random_state,
        n_jobs=n_jobs,
        verbosity=-1,
    )
