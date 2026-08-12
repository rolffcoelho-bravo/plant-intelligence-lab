from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "reports" / "results"


@dataclass(frozen=True)
class EvidenceItem:
    topic: str
    statement: str
    values: dict[str, Any]
    source: str


@dataclass(frozen=True)
class GroundedAnswer:
    question: str
    answer: str
    evidence: tuple[EvidenceItem, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = [asdict(item) for item in self.evidence]
        return payload


class GroundedScientificInterface:
    """Evidence-first interface for scientific questions about Case Study A.

    The interface never asks a language model to discover facts from free text.
    It first loads committed, validated result tables and constructs an explicit
    evidence packet. A generative model can be connected as a rendering layer,
    but it must remain downstream of this evidence boundary.
    """

    def __init__(self, results_dir: Path | None = None) -> None:
        self.results_dir = Path(results_dir) if results_dir else RESULTS

    def _read(self, filename: str) -> pd.DataFrame:
        path = self.results_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Validated evidence file not found: {path}")
        frame = pd.read_csv(path)
        if frame.empty:
            raise ValueError(f"Validated evidence file is empty: {path}")
        return frame

    def evidence_catalog(self) -> tuple[EvidenceItem, ...]:
        forecast = self._read("case_study_a_early_forecasting_summary.csv")
        champion = forecast[
            (forecast["specification"] == "X15") & (forecast["scope"] == "pooled")
        ].iloc[0]

        coverage = self._read("case_study_a_uncertainty_coverage.csv")
        coverage90 = coverage[
            (coverage["scope"] == "pooled") & (coverage["nominal_coverage"] == 0.9)
        ].iloc[0]

        abstention = self._read("case_study_a_uncertainty_abstention.csv").iloc[0]

        selection = self._read("case_study_a_active_selection_summary.csv")
        guided10 = selection[
            (selection["strategy"] == "predicted_response") & (selection["budget"] == 10)
        ].iloc[0]
        random10 = selection[
            (selection["strategy"] == "random") & (selection["budget"] == 10)
        ].iloc[0]

        protocol = self._read("case_study_a_protocol_response_summary.csv")
        day15 = protocol[protocol["day"] == 15].iloc[0]
        day21 = protocol[protocol["day"] == 21].iloc[0]

        gblup = self._read("case_study_a_gblup_summary.csv")
        mean_r2 = float(gblup["r2"].mean())
        boundary_folds = int(gblup["boundary_folds"].sum())

        return (
            EvidenceItem(
                topic="forecast",
                statement=(
                    "Day-15 phenotype alone is the champion Day-21 forecast in the "
                    "information-ablation study."
                ),
                values={
                    "r2": float(champion["r2"]),
                    "rmse": float(champion["rmse"]),
                    "mae": float(champion["mae"]),
                    "predictive_correlation": float(champion["predictive_correlation"]),
                    "n": int(champion["n"]),
                },
                source="reports/results/case_study_a_early_forecasting_summary.csv",
            ),
            EvidenceItem(
                topic="uncertainty",
                statement=(
                    "The 90% conformal interval is close to nominal coverage on pooled "
                    "out-of-fold predictions."
                ),
                values={
                    "nominal_coverage": float(coverage90["nominal_coverage"]),
                    "empirical_coverage": float(coverage90["empirical_coverage"]),
                    "mean_interval_width": float(coverage90["mean_interval_width"]),
                    "n": int(coverage90["n"]),
                },
                source="reports/results/case_study_a_uncertainty_coverage.csv",
            ),
            EvidenceItem(
                topic="abstention",
                statement=(
                    "The reliability filter abstains on a small subset with much larger "
                    "retrospective error."
                ),
                values={
                    "n_total": int(abstention["n_total"]),
                    "n_retained": int(abstention["n_retained"]),
                    "n_abstained": int(abstention["n_abstained"]),
                    "retained_fraction": float(abstention["retained_fraction"]),
                    "rmse_retained": float(abstention["rmse_retained"]),
                    "rmse_abstained": float(abstention["rmse_abstained"]),
                },
                source="reports/results/case_study_a_uncertainty_abstention.csv",
            ),
            EvidenceItem(
                topic="experiment_selection",
                statement=(
                    "Predicted-response ranking strongly enriched high-value outcomes at "
                    "budget 10 in the retrospective benchmark."
                ),
                values={
                    "budget": 10,
                    "guided_hit_rate": float(guided10["high_value_hit_rate"]),
                    "guided_mean_response": float(guided10["mean_observed_response"]),
                    "random_hit_rate": float(random10["high_value_hit_rate"]),
                    "random_mean_response": float(random10["mean_observed_response"]),
                },
                source="reports/results/case_study_a_active_selection_summary.csv",
            ),
            EvidenceItem(
                topic="protocol",
                statement=(
                    "Protocol response is heterogeneous across accessions, with stronger "
                    "evidence for a positive mean shift at Day 15 than Day 21."
                ),
                values={
                    "day15_mean_delta_b_minus_a": float(day15["mean_delta_b_minus_a"]),
                    "day15_ci95_low": float(day15["mean_delta_ci95_low"]),
                    "day15_ci95_high": float(day15["mean_delta_ci95_high"]),
                    "day21_mean_delta_b_minus_a": float(day21["mean_delta_b_minus_a"]),
                    "day21_ci95_low": float(day21["mean_delta_ci95_low"]),
                    "day21_ci95_high": float(day21["mean_delta_ci95_high"]),
                },
                source="reports/results/case_study_a_protocol_response_summary.csv",
            ),
            EvidenceItem(
                topic="genomics",
                statement=(
                    "Genomic-only GBLUP prediction is weak under genotype-aware validation "
                    "and variance estimation is frequently boundary-limited."
                ),
                values={
                    "mean_target_r2": mean_r2,
                    "boundary_folds_total": boundary_folds,
                    "total_variance_folds": int(5 * len(gblup)),
                },
                source="reports/results/case_study_a_gblup_summary.csv",
            ),
        )

    @staticmethod
    def _select_topics(question: str) -> set[str]:
        text = question.lower()
        topics: set[str] = set()
        mapping = {
            "forecast": (
                "forecast",
                "predict",
                "accuracy",
                "r2",
                "rmse",
                "day 21",
                "day-21",
            ),
            "uncertainty": (
                "uncertainty",
                "interval",
                "coverage",
                "conformal",
                "calibration",
            ),
            "abstention": ("abstain", "reliability", "confidence", "difficult"),
            "experiment_selection": (
                "experiment",
                "selection",
                "active learning",
                "priorit",
                "exploit",
                "explore",
                "budget",
            ),
            "protocol": ("protocol", "treatment", "response heterogeneity", "delta"),
            "genomics": (
                "genomic",
                "genome",
                "gene",
                "snp",
                "gblup",
                "heritability",
                "genetics",
            ),
        }
        for topic, keywords in mapping.items():
            if any(keyword in text for keyword in keywords):
                topics.add(topic)
        return topics or {"forecast", "uncertainty", "abstention", "experiment_selection"}

    @staticmethod
    def _unsupported_reason(question: str) -> str | None:
        text = question.lower()
        causal_phrases = (
            "which gene causes",
            "what gene causes",
            "causal gene",
            "causal mechanism",
            "molecular mechanism",
            "prove causality",
            "proves genomics is useless",
            "prove genomics is useless",
        )
        if any(phrase in text for phrase in causal_phrases):
            return (
                "Case Study A contains predictive and comparative evidence, not validated "
                "causal-gene or molecular-mechanism evidence."
            )

        prospective_phrases = (
            "will this reduce",
            "will it reduce",
            "real laboratory",
            "real lab",
            "prospectively validated",
            "prospective validation",
            "commercially validated",
            "production ready",
            "production-ready",
            "another laboratory",
            "another lab",
        )
        if any(phrase in text for phrase in prospective_phrases):
            return (
                "The repository contains retrospective public-data validation, not prospective "
                "performance evidence for another laboratory or commercial process."
            )
        return None

    def build_grounding_packet(self, question: str) -> dict[str, Any]:
        selected = self._select_topics(question)
        evidence = [item for item in self.evidence_catalog() if item.topic in selected]
        unsupported_reason = self._unsupported_reason(question)
        return {
            "question": question,
            "answerability": "unsupported" if unsupported_reason else "supported",
            "unsupported_reason": unsupported_reason,
            "evidence": [asdict(item) for item in evidence],
            "instructions": [
                "Answer only from the supplied evidence.",
                "Distinguish retrospective evidence from prospective validation.",
                "Do not infer biological causality from predictive performance.",
                "Preserve uncertainty and abstention information when relevant.",
                "Name the source file for each material quantitative claim.",
                "If answerability is unsupported, do not answer the unsupported scientific claim.",
                "If the evidence does not answer the question, say that the repository does not yet contain validated evidence for it.",
            ],
        }

    def answer(self, question: str) -> GroundedAnswer:
        packet = self.build_grounding_packet(question)
        evidence = tuple(EvidenceItem(**item) for item in packet["evidence"])

        limitations = (
            "Case Study A uses public Arabidopsis regeneration data; results are not validated for proprietary or other biological systems.",
            "The experiment-selection result is retrospective, not a prospective laboratory trial.",
            "Predictive associations and rankings do not establish biological causality.",
        )

        if packet["answerability"] == "unsupported":
            answer = (
                "The repository does not contain validated evidence sufficient to support that "
                f"claim. {packet['unsupported_reason']}"
            )
            return GroundedAnswer(
                question=question,
                answer=answer,
                evidence=evidence,
                limitations=limitations,
            )

        fragments: list[str] = []
        for item in evidence:
            v = item.values
            if item.topic == "forecast":
                fragments.append(
                    f"The validated champion is X15 -> Day 21 with out-of-fold R2={v['r2']:.3f}, "
                    f"RMSE={v['rmse']:.3f}, and predictive correlation={v['predictive_correlation']:.3f}."
                )
            elif item.topic == "uncertainty":
                fragments.append(
                    f"At nominal 90% coverage, empirical coverage is {100*v['empirical_coverage']:.2f}% "
                    f"with mean interval width {v['mean_interval_width']:.3f}."
                )
            elif item.topic == "abstention":
                fragments.append(
                    f"The reliability filter retained {100*v['retained_fraction']:.2f}% of predictions; "
                    f"retained RMSE was {v['rmse_retained']:.3f} versus {v['rmse_abstained']:.3f} "
                    f"for {v['n_abstained']} abstained cases."
                )
            elif item.topic == "experiment_selection":
                fragments.append(
                    f"At retrospective budget 10, predicted-response ranking had a {100*v['guided_hit_rate']:.1f}% "
                    f"high-value hit rate versus {100*v['random_hit_rate']:.2f}% on average under random selection."
                )
            elif item.topic == "protocol":
                fragments.append(
                    f"The mean Protocol B-A shift was {v['day15_mean_delta_b_minus_a']:.3f} at Day 15 "
                    f"(95% bootstrap CI {v['day15_ci95_low']:.3f} to {v['day15_ci95_high']:.3f}) and "
                    f"{v['day21_mean_delta_b_minus_a']:.3f} at Day 21 "
                    f"(CI {v['day21_ci95_low']:.3f} to {v['day21_ci95_high']:.3f})."
                )
            elif item.topic == "genomics":
                fragments.append(
                    f"Genomic-only GBLUP remained weak across targets (mean target R2={v['mean_target_r2']:.3f}); "
                    f"{v['boundary_folds_total']}/{v['total_variance_folds']} variance-estimation folds were boundary-limited."
                )

        answer = " ".join(fragments)
        if not answer:
            answer = "The repository does not yet contain validated evidence sufficient to answer this question."

        return GroundedAnswer(
            question=question,
            answer=answer,
            evidence=evidence,
            limitations=limitations,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Query validated Plant Intelligence Lab evidence.")
    parser.add_argument(
        "question",
        help="Scientific question about the validated Case Study A results.",
    )
    parser.add_argument(
        "--packet",
        action="store_true",
        help="Emit the structured grounding packet intended for a downstream generative model.",
    )
    args = parser.parse_args()

    interface = GroundedScientificInterface()
    payload = (
        interface.build_grounding_packet(args.question)
        if args.packet
        else interface.answer(args.question).to_dict()
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
