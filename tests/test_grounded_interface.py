from plant_intelligence.ai.grounded_interface import GroundedScientificInterface


def test_forecast_question_is_grounded_in_forecast_evidence():
    interface = GroundedScientificInterface()
    answer = interface.answer("How accurate is the Day-21 forecast?")
    topics = {item.topic for item in answer.evidence}
    assert "forecast" in topics
    assert "X15 -> Day 21" in answer.answer
    assert "R2=" in answer.answer


def test_uncertainty_question_preserves_coverage_evidence():
    interface = GroundedScientificInterface()
    packet = interface.build_grounding_packet("How well calibrated is the 90% prediction interval?")
    topics = {item["topic"] for item in packet["evidence"]}
    assert "uncertainty" in topics
    assert any("Answer only from the supplied evidence" in instruction for instruction in packet["instructions"])


def test_active_learning_question_is_marked_retrospective():
    interface = GroundedScientificInterface()
    answer = interface.answer("Does experiment prioritization beat random selection at budget 10?")
    topics = {item.topic for item in answer.evidence}
    assert "experiment_selection" in topics
    assert any("retrospective" in limitation.lower() for limitation in answer.limitations)


def test_unknown_question_returns_default_validated_topics_without_external_facts():
    interface = GroundedScientificInterface()
    packet = interface.build_grounding_packet("What should I know about this case study?")
    topics = {item["topic"] for item in packet["evidence"]}
    assert topics == {"forecast", "uncertainty", "abstention", "experiment_selection"}
