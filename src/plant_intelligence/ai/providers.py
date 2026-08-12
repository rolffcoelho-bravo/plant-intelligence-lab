from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class LLMAdapter(Protocol):
    """Provider-independent contract for a grounded generative model."""

    name: str

    def generate(self, grounding_packet: dict[str, Any]) -> str:
        """Render an answer from an already-grounded evidence packet."""


@dataclass
class CallableLLMAdapter:
    """Wrap any provider SDK or local model behind the common adapter contract.

    The callable receives only the structured grounding packet. This keeps provider
    code outside the scientific evidence layer and avoids binding the project to a
    specific API or model family.
    """

    name: str
    generator: Callable[[dict[str, Any]], str]

    def generate(self, grounding_packet: dict[str, Any]) -> str:
        return str(self.generator(grounding_packet))


@dataclass
class GroundedTemplateAdapter:
    """Deterministic reference adapter used for CI and grounding evaluation.

    This is not presented as a language model. It provides a reproducible reference
    implementation of the same contract that an external LLM adapter must satisfy.
    """

    name: str = "grounded-template-reference"

    def generate(self, grounding_packet: dict[str, Any]) -> str:
        if grounding_packet.get("answerability") == "unsupported":
            reason = grounding_packet.get("unsupported_reason") or (
                "The supplied evidence does not support the requested claim."
            )
            return (
                "The repository does not contain validated evidence sufficient to support "
                f"that claim. {reason}"
            )

        fragments: list[str] = []
        for item in grounding_packet.get("evidence", []):
            topic = item["topic"]
            values = item["values"]
            source = item["source"]

            if topic == "forecast":
                text = (
                    "The validated champion is X15 -> Day 21 with out-of-fold "
                    f"R2={values['r2']:.3f}, RMSE={values['rmse']:.3f}, and predictive "
                    f"correlation={values['predictive_correlation']:.3f}."
                )
            elif topic == "uncertainty":
                text = (
                    "At nominal 90% interval coverage, empirical coverage is "
                    f"{100 * values['empirical_coverage']:.2f}% with mean interval width "
                    f"{values['mean_interval_width']:.3f}."
                )
            elif topic == "abstention":
                text = (
                    "The reliability filter retained "
                    f"{100 * values['retained_fraction']:.2f}% of predictions; retained RMSE "
                    f"was {values['rmse_retained']:.3f} versus {values['rmse_abstained']:.3f} "
                    f"for {values['n_abstained']} abstained cases."
                )
            elif topic == "experiment_selection":
                text = (
                    "In the retrospective budget-10 benchmark, predicted-response ranking "
                    f"had a {100 * values['guided_hit_rate']:.1f}% high-value hit rate versus "
                    f"{100 * values['random_hit_rate']:.2f}% on average under random selection."
                )
            elif topic == "protocol":
                text = (
                    "The mean Protocol B-A shift was "
                    f"{values['day15_mean_delta_b_minus_a']:.3f} at Day 15 "
                    f"(95% bootstrap CI {values['day15_ci95_low']:.3f} to "
                    f"{values['day15_ci95_high']:.3f}) and "
                    f"{values['day21_mean_delta_b_minus_a']:.3f} at Day 21 "
                    f"(95% bootstrap CI {values['day21_ci95_low']:.3f} to "
                    f"{values['day21_ci95_high']:.3f})."
                )
            elif topic == "genomics":
                text = (
                    "Genomic-only GBLUP remained weak across targets with mean target "
                    f"R2={values['mean_target_r2']:.3f}; "
                    f"{values['boundary_folds_total']}/{values['total_variance_folds']} "
                    "variance-estimation folds were boundary-limited."
                )
            else:
                text = item["statement"]

            fragments.append(f"{text} [source: {source}]")

        if not fragments:
            return (
                "The repository does not yet contain validated evidence sufficient to answer "
                "this question."
            )
        return " ".join(fragments)
