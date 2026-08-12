from plant_intelligence.ai.evaluation import run_benchmark
from plant_intelligence.ai.grounded_interface import GroundedScientificInterface
from plant_intelligence.ai.providers import CallableLLMAdapter, GroundedTemplateAdapter
from plant_intelligence.ai.runtime import VerifiedScientificGenerator


def test_reference_adapter_passes_claim_verification():
    generator = VerifiedScientificGenerator(adapter=GroundedTemplateAdapter())
    result = generator.generate("How accurate is the Day-21 forecast?")
    assert result.verification.passed
    assert "source:" in result.answer


def test_hallucinated_numeric_claim_is_withheld():
    bad = CallableLLMAdapter(
        name="bad-numeric",
        generator=lambda packet: (
            "The Day-21 model has R2=0.999. "
            "[source: reports/results/case_study_a_early_forecasting_summary.csv]"
        ),
    )
    result = VerifiedScientificGenerator(adapter=bad).generate(
        "How accurate is the Day-21 forecast?"
    )
    assert not result.verification.passed
    assert "unsupported_numeric_claim" in {issue.code for issue in result.verification.issues}
    assert result.answer.startswith("Generated answer withheld")


def test_prospective_inflation_is_withheld():
    bad = CallableLLMAdapter(
        name="bad-prospective",
        generator=lambda packet: "This will reduce experiments by 90% in a real laboratory.",
    )
    result = VerifiedScientificGenerator(adapter=bad).generate(
        "Does experiment prioritization beat random selection at budget 10?"
    )
    codes = {issue.code for issue in result.verification.issues}
    assert not result.verification.passed
    assert "prospective_inflation" in codes or "source_traceability_missing" in codes


def test_unsupported_causal_question_refuses_claim():
    interface = GroundedScientificInterface()
    packet = interface.build_grounding_packet("Which gene causes the regeneration response?")
    assert packet["answerability"] == "unsupported"
    result = VerifiedScientificGenerator().generate(
        "Which gene causes the regeneration response?"
    )
    assert result.verification.passed
    assert "does not contain validated evidence" in result.answer.lower()


def test_reference_grounding_benchmark_passes_all_cases():
    cases, summary = run_benchmark()
    assert cases["case_passed"].all()
    row = summary.iloc[0]
    assert row["grounded_scientific_answer_rate"] == 1.0
    assert row["unsupported_safe_response_rate"] == 1.0
