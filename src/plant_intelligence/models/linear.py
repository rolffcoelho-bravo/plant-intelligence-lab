from __future__ import annotations

from sklearn.linear_model import ElasticNet
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def make_elastic_net(*, alpha: float = 0.1, l1_ratio: float = 0.5, max_iter: int = 10000, random_state: int = 42) -> Pipeline:
    """Create a leakage-safe Elastic Net pipeline for high-dimensional genomic features."""
    return Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "model",
                ElasticNet(
                    alpha=alpha,
                    l1_ratio=l1_ratio,
                    max_iter=max_iter,
                    random_state=random_state,
                ),
            ),
        ]
    )
