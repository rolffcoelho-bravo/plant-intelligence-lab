from __future__ import annotations

import numpy as np
import pandas as pd

from plant_intelligence.uncertainty.wheat_gxe_uncertainty import (
    calibrate_intervals,
    deployment_boundary,
    finite_sample_quantile,
    selective_risk,
    support_diagnostics,
)


def _synthetic_predictions() -> pd.DataFrame:
    rows = []
    for regime in ("CV-G", "CV2"):
        for fold in range(5):
            for env in ("ME1", "ME2"):
                for i in range(12):
                    observed = float(i) / 10.0 + (0.1 if env == "ME2" else 0.0)
                    predicted = observed + 0.05 * ((i % 3) - 1)
                    rows.append(
                        {
                            "regime": regime,
                            "scenario": f"gfold_{fold}" if regime == "CV-G" else "sparse_cell",
                            "model": "test",
                            "genotype_id": f"{regime}_{fold}_{env}_{i}",
                            "environment": env,
                            "observed": observed,
                            "predicted": predicted,
                            "calibration_fold": f"fold_{fold}",
                            "abs_error": abs(observed - predicted),
                            "genomic_support_distance": float(i + fold) if regime == "CV-G" else 0.0,
                        }
                    )
    return pd.DataFrame(rows)


def test_finite_sample_quantile_uses_finite_sample_rank() -> None:
    residuals = np.arange(1, 11, dtype=float)
    assert finite_sample_quantile(residuals, 0.80) == 9.0
    assert finite_sample_quantile(residuals, 0.90) == 10.0


def test_crossfit_calibration_excludes_own_fold() -> None:
    frame = _synthetic_predictions()
    calibrated = calibrate_intervals(frame)
    assert len(calibrated) == len(frame)
    assert (calibrated["calibration_n"] >= 30).all()
    assert {"covered_80", "covered_90", "covered_95", "width_90"}.issubset(calibrated.columns)
    assert (calibrated["width_90"] >= 0).all()


def test_support_diagnostics_are_regime_specific() -> None:
    frame = calibrate_intervals(_synthetic_predictions())
    diagnostics = support_diagnostics(frame)
    cvg_signals = set(diagnostics.loc[diagnostics["regime"] == "CV-G", "signal"])
    cv2_signals = set(diagnostics.loc[diagnostics["regime"] == "CV2", "signal"])
    assert cvg_signals == {"width_90", "genomic_support_distance"}
    assert cv2_signals == {"width_90"}


def test_selective_risk_reports_retention_curve_without_fixed_abstention() -> None:
    frame = calibrate_intervals(_synthetic_predictions())
    risk = selective_risk(frame)
    assert set(risk["removed_fraction_target"]) == {0.0, 0.05, 0.10, 0.20}
    assert (risk["retained_fraction"] > 0).all()
    assert (risk["retained_fraction"] <= 1).all()


def test_deployment_boundary_marks_unseen_environments_unsupported() -> None:
    boundary = deployment_boundary().set_index("regime")
    assert boundary.loc["CV-G", "deployment_state"] == "FORECAST_SUPPORTED"
    assert boundary.loc["CV2", "deployment_state"] == "FORECAST_SUPPORTED"
    assert boundary.loc["CV-E", "deployment_state"] == "UNSUPPORTED_ENVIRONMENT"
    assert boundary.loc["CV-GE", "deployment_state"] == "UNSUPPORTED_ENVIRONMENT"
