import numpy as np
import pandas as pd
import pytest

from plant_intelligence.uncertainty import maize_b14c_2024_sealed_reveal as b14c


def sealed_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "genotype": ["G1", "G2", "G3"],
            "environment": ["E1", "E1", "E2"],
            "predicted": [1.0, 2.0, 3.0],
            "control_lower_90": [0.0, 1.0, 2.0],
            "control_upper_90": [2.0, 3.0, 4.0],
            "adaptive_lower_90": [-0.5, 0.5, 1.5],
            "adaptive_upper_90": [2.5, 3.5, 4.5],
            "support_group": ["WITHIN", "WITHIN", "EDGE"],
            "reliability_state": ["RETAIN_SUPPORTED", "RETAIN_SUPPORTED", "ABSTAIN_LOW_ENVIRONMENT_SUPPORT"],
        }
    )


def test_official_normalization_uses_locked_exact_schema():
    raw = pd.DataFrame(
        {
            "Env": ["E1", "E2"],
            "Hybrid": ["G1", "G2"],
            "Yield_Mg_ha": [1.2, 2.3],
            "ignored": [7, 8],
        }
    )
    out = b14c.normalize_official_outcomes(raw)
    assert list(out.columns) == ["genotype", "environment", "observed"]
    assert out.to_dict("records") == [
        {"genotype": "G1", "environment": "E1", "observed": 1.2},
        {"genotype": "G2", "environment": "E2", "observed": 2.3},
    ]


def test_official_duplicate_keys_abort():
    raw = pd.DataFrame(
        {
            "Env": ["E1", "E1"],
            "Hybrid": ["G1", "G1"],
            "Yield_Mg_ha": [1.0, 1.1],
        }
    )
    with pytest.raises(b14c.B14CIntegrityError, match="duplicate"):
        b14c.normalize_official_outcomes(raw)


def test_primary_cohort_membership_depends_on_key_presence_not_outcome_value():
    sealed = sealed_fixture()
    official_a = pd.DataFrame(
        {
            "genotype": ["G1", "G3"],
            "environment": ["E1", "E2"],
            "observed": [1.1, 3.2],
        }
    )
    official_b = official_a.copy()
    official_b["observed"] = [999.0, -999.0]

    cohort_a, audit_a = b14c.build_primary_cohort(sealed, official_a)
    cohort_b, audit_b = b14c.build_primary_cohort(sealed, official_b)

    keys_a = set(map(tuple, cohort_a[["genotype", "environment"]].to_numpy()))
    keys_b = set(map(tuple, cohort_b[["genotype", "environment"]].to_numpy()))
    assert keys_a == keys_b == {("G1", "E1"), ("G3", "E2")}
    pd.testing.assert_series_equal(
        audit_a["official_answer_key_present"],
        audit_b["official_answer_key_present"],
        check_names=False,
    )
    assert not audit_a["selection_uses_outcome_value"].any()
    assert not audit_a["post_reveal_protocol_amendment"].any()


def test_present_key_with_missing_or_nonnumeric_outcome_aborts():
    sealed = sealed_fixture()
    official = pd.DataFrame(
        {
            "genotype": ["G1", "G3"],
            "environment": ["E1", "E2"],
            "observed": [1.1, np.nan],
        }
    )
    with pytest.raises(b14c.B14CIntegrityError, match="missing/non-numeric"):
        b14c.build_primary_cohort(sealed, official)


def test_point_metrics_are_standard_external_metrics():
    frame = pd.DataFrame({"observed": [1.0, 2.0, 3.0], "predicted": [1.0, 2.0, 2.0]})
    out = b14c.point_metrics(frame)
    assert np.isclose(out["rmse"], np.sqrt(1.0 / 3.0))
    assert np.isclose(out["mae"], 1.0 / 3.0)
    assert np.isfinite(out["r2"])
    assert np.isfinite(out["correlation"])


def interval_summary(control_pass, adaptive_pass, control_score, adaptive_score):
    return pd.DataFrame(
        [
            {
                "rule": b14c.CONTROL,
                "calibration_pass": control_pass,
                "mean_interval_score": control_score,
            },
            {
                "rule": b14c.ADAPTIVE,
                "calibration_pass": adaptive_pass,
                "mean_interval_score": adaptive_score,
            },
        ]
    )


def test_adaptive_promoted_only_when_calibrated_and_strictly_more_efficient():
    assert (
        b14c.branch_decision(interval_summary(True, True, 10.0, 9.0))
        == b14c.DECISION_ADAPTIVE_PROMOTED
    )
    assert (
        b14c.branch_decision(interval_summary(False, True, 10.0, 10.0))
        == b14c.DECISION_ADAPTIVE_INEFFICIENT
    )
    assert (
        b14c.branch_decision(interval_summary(True, True, 10.0, 10.0))
        == b14c.DECISION_KEEP_CONTROL
    )
    assert (
        b14c.branch_decision(interval_summary(False, False, 10.0, 9.0))
        == b14c.DECISION_BOTH_FAIL
    )


def test_interval_evaluation_uses_locked_bounds_without_recalibration():
    frame = sealed_fixture().copy()
    frame["observed"] = [1.0, 3.2, 4.2]
    summary, detail = b14c.interval_evaluation(frame)
    assert set(summary["rule"]) == {b14c.CONTROL, b14c.ADAPTIVE}
    assert "control_covered_90" in detail
    assert "adaptive_covered_90" in detail
    assert "control_interval_score_90" in detail
    assert "adaptive_interval_score_90" in detail
    assert (summary["mean_half_width"] > 0).all()


def test_sealed_csv_adaptive_level_accepts_only_frozen_serialization_precision():
    assert b14c.sealed_csv_adaptive_level_matches([0.951281331718, 0.951281331718])
    assert not b14c.sealed_csv_adaptive_level_matches([0.9512813318])
    assert not b14c.sealed_csv_adaptive_level_matches([0.952])


def test_frozen_constants_match_b14b_seal_contract():
    assert b14c.EXPECTED_PREDICTION_SHA256 == "91c765ea994f557db1911865309bca94ebc2110b87a5fea483a03c879d1fb19d"
    assert b14c.EXPECTED_CANDIDATE_SHA256 == "32e4f308522ee849e498d2bf0614f3ec349574a27bb327fefeb80e0f4e05bf7f"
    assert b14c.EXPECTED_N_PREDICTIONS == 798
    assert b14c.EXPECTED_N_GENOTYPES == 92
    assert b14c.EXPECTED_N_ENVIRONMENTS == 19
    assert np.isclose(b14c.EXPECTED_ADAPTIVE_LEVEL, 0.9512813317177465, rtol=0, atol=1e-15)
    assert b14c.SEALED_CSV_ADAPTIVE_LEVEL_ATOL == 5e-13
    assert b14c.PRIMARY_ESTIMAND == "OFFICIALLY_OBSERVABLE_SEALED_KEYS"