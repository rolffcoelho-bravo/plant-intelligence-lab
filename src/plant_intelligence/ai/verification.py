from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any


_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])-?\d+(?:\.\d+)?%?")
_SOURCE_RE = re.compile(r"\[source:\s*([^\]]+)\]")


@dataclass(frozen=True)
class VerificationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    issues: tuple[VerificationIssue, ...]
    checked_numeric_claims: int
    traceable_sources: int
    expected_sources: int


class ScientificClaimVerifier:
    """Verify that a generated answer stays inside the supplied evidence boundary."""

    def __init__(self, numeric_relative_tolerance: float = 0.02) -> None:
        self.numeric_relative_tolerance = numeric_relative_tolerance

    @staticmethod
    def _numeric_tokens(text: str) -> list[float]:
        values: list[float] = []
        for token in _NUMBER_RE.findall(text):
            is_percent = token.endswith("%")
            value = float(token.rstrip("%"))
            values.append(value if not is_percent else value)
        return values

    @staticmethod
    def _evidence_numeric_values(packet: dict[str, Any]) -> list[float]:
        allowed: list[float] = []
        for item in packet.get("evidence", []):
            for value in item.get("values", {}).values():
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)) and math.isfinite(float(value)):
                    numeric = float(value)
                    allowed.append(numeric)
                    if 0.0 <= numeric <= 1.0:
                        allowed.append(100.0 * numeric)
            allowed.extend(ScientificClaimVerifier._numeric_tokens(item.get("statement", "")))
        allowed.extend(ScientificClaimVerifier._numeric_tokens(packet.get("question", "")))
        return allowed

    def _matches_allowed(self, claim: float, allowed: list[float]) -> bool:
        for expected in allowed:
            tolerance = max(0.01, self.numeric_relative_tolerance * max(1.0, abs(expected)))
            if abs(claim - expected) <= tolerance:
                return True
        return False

    @staticmethod
    def _has_positive_inflation(answer: str) -> list[VerificationIssue]:
        text = answer.lower()
        patterns = {
            "causality_inflation": (
                " proves causality",
                " proves that",
                " causes regeneration",
                " causal gene is",
                " causal mechanism is",
            ),
            "prospective_inflation": (
                "will reduce laboratory",
                "will reduce experiments",
                "guarantees laboratory",
                "prospectively validated",
                "commercially validated",
                "production-ready",
                "production ready",
            ),
        }
        issues: list[VerificationIssue] = []
        for code, phrases in patterns.items():
            if any(phrase in text for phrase in phrases):
                issues.append(
                    VerificationIssue(
                        code=code,
                        message=f"Generated answer contains unsupported {code.replace('_', ' ')}.",
                    )
                )
        return issues

    def verify(self, answer: str, packet: dict[str, Any]) -> VerificationResult:
        issues: list[VerificationIssue] = []

        if packet.get("answerability") == "unsupported":
            safe_language = (
                "does not contain validated evidence" in answer.lower()
                or "does not yet contain validated evidence" in answer.lower()
                or "insufficient" in answer.lower()
            )
            if not safe_language:
                issues.append(
                    VerificationIssue(
                        code="unsupported_question_answered",
                        message=(
                            "The evidence packet marks the question unsupported, but the answer "
                            "does not clearly refuse the unsupported claim."
                        ),
                    )
                )

        answer_without_sources = _SOURCE_RE.sub("", answer)
        numeric_claims = self._numeric_tokens(answer_without_sources)
        allowed = self._evidence_numeric_values(packet)
        for claim in numeric_claims:
            if not self._matches_allowed(claim, allowed):
                issues.append(
                    VerificationIssue(
                        code="unsupported_numeric_claim",
                        message=f"Numeric claim {claim:g} is not traceable to supplied evidence.",
                    )
                )

        issues.extend(self._has_positive_inflation(answer))

        topics = {item.get("topic") for item in packet.get("evidence", [])}
        lower = answer.lower()
        if "uncertainty" in topics and not ("coverage" in lower or "interval" in lower):
            issues.append(
                VerificationIssue(
                    code="uncertainty_omitted",
                    message="Uncertainty evidence was supplied but omitted from the answer.",
                )
            )
        if "experiment_selection" in topics and packet.get("answerability") == "supported":
            if "retrospective" not in lower:
                issues.append(
                    VerificationIssue(
                        code="retrospective_boundary_omitted",
                        message=(
                            "Experiment-selection evidence must be identified as retrospective."
                        ),
                    )
                )
        if "abstention" in topics and packet.get("answerability") == "supported":
            if not ("abstain" in lower or "retained" in lower):
                issues.append(
                    VerificationIssue(
                        code="abstention_omitted",
                        message="Reliability evidence was supplied but abstention was omitted.",
                    )
                )

        expected_sources = {
            item.get("source", "") for item in packet.get("evidence", []) if item.get("source")
        }
        cited_sources = set(_SOURCE_RE.findall(answer))
        traceable = len(expected_sources.intersection(cited_sources))
        if packet.get("answerability") == "supported" and expected_sources and traceable == 0:
            issues.append(
                VerificationIssue(
                    code="source_traceability_missing",
                    message="No material claim is linked to a supplied repository source.",
                )
            )

        return VerificationResult(
            passed=not issues,
            issues=tuple(issues),
            checked_numeric_claims=len(numeric_claims),
            traceable_sources=traceable,
            expected_sources=len(expected_sources),
        )
