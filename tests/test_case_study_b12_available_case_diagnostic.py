from pathlib import Path

import pandas as pd

from plant_intelligence.uncertainty.maize_b12_available_case_diagnostic import (
    DIAGNOSTIC_LABEL,
    PRIMARY_INCOMPLETE,
    SELECTION_RULE,
    evaluate_available_case_diagnostic,
)
from plant_intelligence.uncertainty.maize_external_temporal_validation import (
    FORBIDDEN_ANSWER_BASENAME,
    SUPPORTED_GENOTYPE,
    sha256_file,
    write_prediction_seal,
)
from plant_intelligence.uncertainty.maize_forward_uncertainty import RETAIN


def _sealed_predictions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "genotype": ["H1", "H2", "H3", "H4"],
            "environment": ["E1", "E1", "E2", "E2"],
            "predicted": [10.0, 11.0, 12.0, 13.0],
            "reliability_state": [RETAIN, RETAIN, RETAIN, RETAIN],
            "genotype_support_state": [SUPPORTED_GENOTYPE] * 4,
            "lower_80": [8.0, 9.0, 10.0, 11.0],
            "upper_80": [12.0, 13.0, 14.0, 15.0],
            "lower_90": [7.0, 8.0, 9.0, 10.0],
            "upper_90": [13.0, 14.0, 15.0, 16.0],
            "lower_95": [6.0, 7.0, 8.0, 9.0],
            "upper_95": [14.0, 15.0, 16.0, 17.0],
        }
    )


def _write_case(tmp_path: Path, yields: list[float]):
    prediction_path = tmp_path / "sealed.csv"
    seal_path = tmp_path / "seal.json"
    answer_path = tmp_path / FORBIDDEN_ANSWER_BASENAME
    write_prediction_seal(_sealed_predictions(), prediction_path, seal_path, {})
    pd.DataFrame(
        {
            "Hybrid": ["H1", "H2", "H3"],
            "Env": ["E1", "E1", "E2"],
            "Yield_Mg_ha": yields,
        }
    ).to_csv(answer_path, index=False)
    return prediction_path, seal_path, answer_path


def test_available_case_diagnostic_preserves_primary_incomplete_status(tmp_path: Path):
    prediction_path, seal_path, answer_path = _write_case(tmp_path, [10.2, 10.8, 12.4])
    digest_before = sha256_file(prediction_path)

    primary, summary, coverage, reliability, environment, cohort = (
        evaluate_available_case_diagnostic(prediction_path, seal_path, answer_path)
    )

    assert sha256_file(prediction_path) == digest_before
    assert primary.loc[0, "primary_status"] == PRIMARY_INCOMPLETE
    assert bool(primary.loc[0, "primary_confirmatory_evaluable"]) is False
    assert int(primary.loc[0, "n_sealed_predictions"]) == 4
    assert int(primary.loc[0, "n_officially_observable"]) == 3
    assert int(primary.loc[0, "n_missing_official_answer_keys"]) == 1
    assert bool(primary.loc[0, "sealed_artifact_replaced_or_resealed"]) is False
    assert bool(primary.loc[0, "post_reveal_protocol_amendment"]) is True
    assert bool(primary.loc[0, "available_case_diagnostic_confirmatory"]) is False
    assert primary.loc[0, "selection_rule"] == SELECTION_RULE
    assert bool(primary.loc[0, "selection_uses_outcome_value"]) is False
    assert bool(primary.loc[0, "t2_branch_reopened"]) is False
    assert bool(primary.loc[0, "post_result_tuning_permitted"]) is False

    assert summary.loc[0, "diagnostic"] == DIAGNOSTIC_LABEL
    assert bool(summary.loc[0, "confirmatory"]) is False
    assert int(summary.loc[0, "n_evaluated_available_cases"]) == 3
    assert int(summary.loc[0, "n_excluded_missing_official_keys"]) == 1
    assert set(round(v, 2) for v in coverage["nominal"]) == {0.80, 0.90, 0.95}
    assert reliability.loc[0, "state"] == "ALL_AVAILABLE_CASES"
    assert environment["n_sealed"].sum() == 4
    assert environment["n_officially_observable"].sum() == 3
    assert cohort["official_answer_key_present"].sum() == 3
    assert cohort["selection_uses_outcome_value"].eq(False).all()


def test_available_case_membership_is_invariant_to_numeric_yield_values(tmp_path: Path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    pa, sa, aa = _write_case(a, [10.0, 11.0, 12.0])
    pb, sb, ab = _write_case(b, [-1000.0, 0.0, 1000.0])

    result_a = evaluate_available_case_diagnostic(pa, sa, aa)
    result_b = evaluate_available_case_diagnostic(pb, sb, ab)
    cohort_a = result_a[-1]
    cohort_b = result_b[-1]

    keys_a = set(
        map(
            tuple,
            cohort_a.loc[
                cohort_a["official_answer_key_present"], ["genotype", "environment"]
            ].to_numpy(),
        )
    )
    keys_b = set(
        map(
            tuple,
            cohort_b.loc[
                cohort_b["official_answer_key_present"], ["genotype", "environment"]
            ].to_numpy(),
        )
    )
    assert keys_a == keys_b == {("H1", "E1"), ("H2", "E1"), ("H3", "E2")}
    assert result_a[0].loc[0, "selection_rule"] == SELECTION_RULE
    assert result_b[0].loc[0, "selection_rule"] == SELECTION_RULE
    assert bool(result_a[0].loc[0, "selection_uses_outcome_value"]) is False
    assert bool(result_b[0].loc[0, "selection_uses_outcome_value"]) is False
