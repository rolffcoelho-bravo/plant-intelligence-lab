"""Authoritative execution wrapper for Case Study B8 decision horizons."""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from plant_intelligence.models import maize_environment_decision_horizons_core as core


STATES = {
    "Pre-season-G-only": "PRESEASON_GENOMICS_ONLY",
    "Pre-season-location-history": "PRESEASON_TRAINING_HISTORY",
    "Pre-flowering-observed": "RETROSPECTIVE_HORIZON_PROXY",
    "At-flowering-observed": "RETROSPECTIVE_HORIZON_PROXY",
    "Reproductive-stage-observed": "RETROSPECTIVE_HORIZON_PROXY",
    "Full-season-nonleaky": "RETROSPECTIVE_FULL_SEASON_REFERENCE",
}


def historical_location_proxy(ecov_nonleaky: pd.DataFrame, train_envs: set[str]):
    source = ecov_nonleaky.copy()
    source.index = source.index.astype(str)
    train = {str(v) for v in train_envs}
    if len(train) < 2:
        raise ValueError("At least two training environments are required.")
    missing = train.difference(source.index)
    if missing:
        raise ValueError("Training environment missing from ECOV.")

    global_mean = source.loc[sorted(train)].mean(axis=0)
    by_location = {}
    for env in sorted(train):
        by_location.setdefault(core.location_code(env), []).append(env)

    values, rows = [], []
    for env in source.index:
        loc = core.location_code(env)
        peers = list(by_location.get(loc, []))
        if env in train:
            peers = [v for v in peers if v != env]
        if peers:
            proxy = source.loc[peers].mean(axis=0)
            kind = "same_location_training_history"
        elif env in train:
            proxy = source.loc[sorted(train.difference({env}))].mean(axis=0)
            kind = "global_training_history_fallback_excluding_self"
        else:
            proxy = global_mean
            kind = "global_training_history_fallback"
        values.append(proxy.to_numpy(float))
        rows.append({
            "environment": env,
            "location": loc,
            "is_outer_training_environment": env in train,
            "history_source": kind,
            "n_same_location_history_environments": len(peers),
            "uses_own_current_year_ecov": False,
            "uses_outer_test_ecov": False,
        })
    return pd.DataFrame(values, index=source.index, columns=source.columns), pd.DataFrame(rows)


def availability_audit(ecov_audit: pd.DataFrame):
    rows = []
    for order, spec in enumerate(core.HORIZONS):
        cols = core.horizon_columns(ecov_audit, spec)
        rows.append({
            "horizon_order": order,
            "horizon": spec.name,
            "admitted_stages": "|".join(spec.stages),
            "n_current_year_ecov_columns": len(cols),
            "uses_current_year_ecov": spec.uses_current_year_ecov,
            "availability_state": STATES[spec.name],
            "strict_no_post_horizon_columns": True,
            "source_ecov_uses_observed_silking_calibration": spec.name != "Pre-season-G-only",
            "uses_heldout_current_year_ecov_or_silking": spec.uses_current_year_ecov,
            "forward_time_validation": False,
            "description": spec.description,
        })
    return pd.DataFrame(rows)


def install():
    core.historical_location_proxy = historical_location_proxy
    core.availability_audit = availability_audit


def run(root: Path):
    install()
    return core.run(root)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    print("Case Study B8 complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
