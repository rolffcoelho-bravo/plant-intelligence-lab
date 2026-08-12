from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .grounded_interface import GroundedScientificInterface
from .providers import GroundedTemplateAdapter, LLMAdapter
from .verification import ScientificClaimVerifier, VerificationResult


@dataclass(frozen=True)
class VerifiedGeneration:
    question: str
    provider: str
    draft: str
    answer: str
    verification: VerificationResult
    grounding_packet: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["verification"] = asdict(self.verification)
        return payload


class VerifiedScientificGenerator:
    """Generate scientific prose only after retrieval and claim verification."""

    def __init__(
        self,
        adapter: LLMAdapter | None = None,
        interface: GroundedScientificInterface | None = None,
        verifier: ScientificClaimVerifier | None = None,
    ) -> None:
        self.adapter = adapter or GroundedTemplateAdapter()
        self.interface = interface or GroundedScientificInterface()
        self.verifier = verifier or ScientificClaimVerifier()

    def generate(self, question: str) -> VerifiedGeneration:
        packet = self.interface.build_grounding_packet(question)
        draft = self.adapter.generate(packet)
        verification = self.verifier.verify(draft, packet)
        if verification.passed:
            answer = draft
        else:
            codes = ", ".join(issue.code for issue in verification.issues)
            answer = (
                "Generated answer withheld because it failed the scientific grounding check "
                f"({codes})."
            )
        return VerifiedGeneration(
            question=question,
            provider=self.adapter.name,
            draft=draft,
            answer=answer,
            verification=verification,
            grounding_packet=packet,
        )
