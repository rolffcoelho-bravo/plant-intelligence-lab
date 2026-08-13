"""Decision-time availability safety layer for Case Study B8.

This module is the executable B8 entry point. It enforces two boundaries before
calling the frozen decision-horizon engine:

1. A pre-season location-history proxy never uses the held-out current-year
   ECOV row and never uses a training environment's own ECOV row in its proxy.
2. Source provenance distinguishes historical ECOV construction from use of
   held-out current-year ECOV information.

The underlying G2F ECOV matrix remains a retrospective research resource; this
layer prevents the repository from relabeling current-year horizon results as
prospective deployment evidence.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from plant_intelligence.models import maize_environment_decision_horizons as engine


def historical_location_proxy(
    ecov_nonleaky: pd.DataFrame,
    train_envs: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_envs = [str(v) for v in ecov_nonleaky.index]
    train = {str(v) for v in train_envs}
    if len(train) < 2:
        raise ValueError("At least two training environments are required for B8 history proxies.")

    source = ecov_nonleaky.copy()
    source.index = source.index.astype(str)
    missing = train.difference(source.index)
    if missing:
        raise ValueError(f"Training environments absent from ECOV: {sorted(missing)[:3]}")

    global_train = source.loc[sorted(train)].mean(axis=0)
    train_by_location: dict[str, list[str]] = {}
    for env in sorted(train):
        train_by_location.setdefault(engine.location_code(env), []).append(env)

    values = []
    audit_rows = []
    for env in all_envs:
        loc = engine.location_code(env)
        same_location = list(train_by_location.get(loc, []))
        if env in train:
            same_location = [candidate for candidate in same_location if candidate != env]

        if same_location:
            proxy = source.loc[same_location].mean(axis=0)
            source_type = "same_location_training_history"
        elif env in train:
            fallback = sorted(train.difference({env}))
            proxy = source.loc[fallback].mean(axis=0)
            source_type = "global_training_history_fallback_excluding_self"
        else:
            proxy = global_train
            source_type = "global_training_history_fallback"

        values.append(proxy.to_numpy(float))
        audit_rows.append(
            {
                "environment": env,
                "location": loc,
                "is_outer_training_environment": env in train,
                "history_source": source_type,
                "n_same_location_history_environments": int(len(same_location)),
                "uses_own_current_year_ecov": False,
                "uses_outer_test_ecov": False,
            }
        )

    proxy_frame = pd.DataFrame(values, index=all_envs, columns=source.columns, dtype=float)
    return proxy_frame, pd.DataFrame(audit_rows)


def availability_audit(ecov_audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for order, spec in enumerate(engine.HORIZONS):
        columns = engine.horizon_columns(ecov_audit, spec)
        uses_any_ecov = spec.name != "Pre-season-G-only"
        rows.append(
            {
                "horizon_order": order,
                "horizon": spec.name,
                "admitted_stages": "|".join(spec.stages),
                "n_current_year_ecov_columns": len(columns),
                "uses_current_year_ecov": spec.uses_current_year_ecov,
                "availability_state": spec.availability_state,
                "strict_no_post_horizon_columns": True,
                "source_ecov_uses_observed_silking_calibration": uses_any_ecov,
                "uses_heldout_current_year_ecov_or_silking": spec.uses_current_year_ecov,
                "description": spec.description,
            }
        )
    return pd.DataFrame(rows)


def run(root: Path) -> dict[str, Path]:
    # The engine resolves these names at call time. Assigning the safety-layer
    # implementations makes this module the authoritative B8 execution path.
    engine.historical_location_proxy = historical_location_proxy
    engine.availability_audit = availability_audit
    return engine.run(root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run leakage-safe Case Study B8 decision horizons.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B8 safety-audited execution complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
