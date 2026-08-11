from __future__ import annotations

from sklearn.ensemble import RandomForestRegressor


def make_random_forest(*, n_estimators: int = 500, max_depth: int | None = None, min_samples_leaf: int = 2, max_features: str | float | int = "sqrt", random_state: int = 42, n_jobs: int = -1) -> RandomForestRegressor:
    """Create a conservative Random Forest baseline for nonlinear genomic effects."""
    return RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        random_state=random_state,
        n_jobs=n_jobs,
    )
