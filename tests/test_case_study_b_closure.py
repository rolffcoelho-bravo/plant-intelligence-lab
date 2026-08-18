import pandas as pd

from plant_intelligence.diagnostics.maize_case_study_b_closure import (
    CLOSURE_DECISION,
    PUBLICATION_FRAME,
    b18_gate,
    claim_ledger,
    literature_boundary,
)


def test_closure_decision_is_terminal_and_non_novelty_inflating():
    assert CLOSURE_DECISION == (
        "CASE_STUDY_B_CLOSED_EXTERNAL_VALIDATION_CONTRIBUTION_SUPPORTED_"
        "METHOD_NOVELTY_NOT_SUPPORTED_B18_SEPARATE_HYPOTHESIS_GATE_ONLY"
    )
    assert PUBLICATION_FRAME == (
        "SEAL_FIRST_BLINDED_EXTERNAL_VALIDATION_AND_FAILURE_ANALYSIS_"
        "NOT_NEW_PREDICTIVE_METHOD"
    )


def test_publication_claim_ledger_blocks_known_overclaims():
    claims = claim_ledger()
    assert len(claims) >= 10
    prohibited = claims[claims["claim_class"].str.startswith("PROHIBITED")]
    assert not prohibited["permitted"].any()
    calendar = claims[claims["claim"].str.contains("calendar-time prospective", regex=False)].iloc[0]
    assert calendar["permitted"] == False
    b12 = claims[claims["claim"].str.contains("2022 420-cell confirmatory", regex=False)].iloc[0]
    assert b12["permitted"] == False


def test_literature_boundary_blocks_obvious_b18_repackaging():
    lit = literature_boundary()
    required = {
        "10.1093/genetics/iyae171",
        "10.1093/genetics/iyae179",
        "10.1007/s00122-026-05280-z",
        "10.1371/journal.pcbi.1013729",
        "10.1093/plphys/kiag344",
    }
    assert required.issubset(set(lit["doi"]))
    gnn = lit[lit["doi"].eq("10.1371/journal.pcbi.1013729")].iloc[0]
    assert "adding nonlinear GxE" in gnn["closure_implication"]


def test_b18_can_only_open_as_separate_hypothesis_gate():
    gate = b18_gate().set_index("gate")
    assert gate.loc["B18_AUTOMATIC_MODEL_DEVELOPMENT", "permitted"] == False
    assert gate.loc["B18_SEPARATE_HYPOTHESIS_AND_NOVELTY_AUDIT", "permitted"] == True
    assert gate.loc["B18_FORBIDDEN_STARTING_QUESTION_ADD_GXE", "permitted"] == False
    assert gate.loc["B18_FORBIDDEN_STARTING_QUESTION_TUNE_2024_FAILURE", "permitted"] == False


def test_claim_ledger_is_dataframe_with_boolean_permission():
    claims = claim_ledger()
    assert isinstance(claims, pd.DataFrame)
    assert set(claims.columns) == {"claim", "permitted", "claim_class"}
    assert claims["permitted"].map(type).isin([bool]).all()
