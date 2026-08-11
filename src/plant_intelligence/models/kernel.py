from __future__ import annotations

from sklearn.kernel_ridge import KernelRidge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def make_kernel_ridge(*, alpha: float = 1.0, gamma: float | None = None, kernel: str = "rbf") -> Pipeline:
    """Create a standardized kernel-ridge model for nonlinear genomic signal."""
    return Pipeline(
        steps=[
            ("scale", StandardScaler()),
            ("model", KernelRidge(alpha=alpha, gamma=gamma, kernel=kernel)),
        ]
    )
