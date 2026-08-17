"""B12B seal-first reveal runner for the official 2022 observed outcomes.

This module is intentionally separate from every Stage-A runner. It verifies the
committed prediction SHA-256 before resolving or downloading the answer file.
No model, interval, support parameter, or admission criterion is modified after
reveal. The answer-key audit records only identifier overlap and missingness,
never observed yield values.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests

from plant_intelligence.uncertainty import maize_b12_cyverse_source as source
from plant_intelligence.uncertainty import maize_external_temporal_validation as b12

ANSWER_BASENAME = b12.FORBIDDEN_ANSWER_BASENAME
USER_AGENT = "plant-intelligence-lab/0.1 B12B seal-first-reveal"


def _norm(value: object) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def _authenticated_url(url: str) -> str:
    parts = urlsplit(str(url))
    path = parts.path.replace("/dav-anon/", "/dav/", 1)
    return urlunsplit(("https", parts.netloc, path, parts.query, ""))


def _answer_schema_ok(body: bytes) -> bool:
    try:
        frame = pd.read_csv(io.BytesIO(body), nrows=8)
    except Exception:
        return False
    columns = {_norm(column) for column in frame.columns}
    genotype_ok = bool(columns.intersection({_norm("Hybrid"), _norm("Genotype")}))
    env_ok = bool(columns.intersection({_norm("Env"), _norm("Environment")}))
    yield_ok = bool(
        columns.intersection(
            {
                _norm("Yield_Mg_ha"),
                _norm("Yield"),
                _norm("grain_yield"),
                _norm("Observed"),
            }
        )
    )
    return genotype_ok and env_ok and yield_ok


def _registry_roots(payload: dict[str, object]) -> list[str]:
    roots: list[str] = []

    def add(value: str) -> None:
        if value and value not in roots:
            roots.append(value.rstrip("/"))

    for value in source._all_strings(payload.get("result", {})):
        irods = source._irods_path_from_string(value)
        if irods:
            lower = irods.lower()
            if "/testing_data" in lower:
                index = lower.find("/testing_data")
                add(irods[:index])
            add(irods)
        clean = source._clean_http_url(value)
        if clean:
            parts = urlsplit(clean)
            path = parts.path.rstrip("/")
            lower = path.lower()
            if "/testing_data" in lower:
                index = lower.find("/testing_data")
                add(urlunsplit(("https", parts.netloc, path[:index], "", "")))
            add(clean)

    historical_paths = (
        "/iplant/home/shared/commons_repo/curated/"
        "GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2023",
        "/iplant/commons/cyverse_curated/"
        "GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2023",
    )
    for path in historical_paths:
        add(f"https://data.cyverse.org/dav-anon{path}")
    return roots


def answer_candidates(payload: dict[str, object]) -> list[str]:
    candidates: list[str] = []

    def add(value: str) -> None:
        value = _authenticated_url(value)
        if value not in candidates:
            candidates.append(value)

    for root in _registry_roots(payload):
        if str(root).startswith("/"):
            root = f"https://data.cyverse.org/dav-anon{root}"
        add(f"{str(root).rstrip('/')}/{ANSWER_BASENAME}")
        add(f"{str(root).rstrip('/')}/Testing_data/{ANSWER_BASENAME}")
        add(f"{str(root).rstrip('/')}/Testing_Data/{ANSWER_BASENAME}")
    return candidates


def acquire_answer_after_seal(
    prediction_path: Path,
    seal_path: Path,
    destination: Path,
    timeout: int = 180,
) -> tuple[Path, dict[str, object]]:
    seal = b12.verify_prediction_seal(prediction_path, seal_path)
    if int(seal.get("target_year", -1)) != b12.TARGET_YEAR:
        raise b12.SealViolation("B12B seal target year mismatch.")

    payload = source.registry_payload()
    attempts: list[dict[str, object]] = []
    for url in answer_candidates(payload):
        try:
            response = requests.get(
                url,
                auth=("anonymous", ""),
                headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*;q=0.5"},
                timeout=(30, timeout),
                allow_redirects=False,
            )
            attempts.append(
                {
                    "url": url,
                    "status": response.status_code,
                    "location": response.headers.get("location", ""),
                    "content_type": response.headers.get("content-type", ""),
                    "size": len(response.content),
                    "html_like": source._is_html_response(response),
                }
            )
            response.raise_for_status()
            if response.is_redirect or not response.content:
                continue
            if source._is_html_response(response) or not _answer_schema_ok(response.content):
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.content)
            return destination, {
                "prediction_sha256_verified_before_answer_access": seal["prediction_sha256"],
                "answer_url": url,
                "answer_sha256": b12._sha256_bytes(response.content),
                "answer_size_bytes": len(response.content),
                "official_source_doi": b12.SOURCE_DOI,
            }
        except Exception as exc:
            attempts.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    raise RuntimeError(
        "B12B could not resolve the official observed-answer CSV after seal verification. "
        + json.dumps(attempts[-30:], indent=2)
    )


def _canonical_key(genotype: object, environment: object) -> str:
    return f"{str(genotype).strip()}\x1f{str(environment).strip()}"


def write_answer_key_audit(
    prediction_path: Path,
    answer_path: Path,
    audit_path: Path,
    missing_path: Path,
) -> pd.DataFrame:
    """Audit identifier overlap without writing any observed yield value."""
    predictions = pd.read_csv(prediction_path, low_memory=False)
    answer = pd.read_csv(answer_path, low_memory=False)
    g_col, e_col, y_col = b12._answer_columns(answer)

    pred = predictions[["genotype", "environment"]].copy()
    pred["genotype"] = pred["genotype"].astype(str).str.strip()
    pred["environment"] = pred["environment"].astype(str).str.strip()
    pred["key"] = [
        _canonical_key(g, e)
        for g, e in zip(pred["genotype"], pred["environment"])
    ]

    ans = answer[[g_col, e_col, y_col]].copy()
    ans.columns = ["genotype", "environment", "observed"]
    ans = ans.dropna(subset=["genotype", "environment"])
    ans["genotype"] = ans["genotype"].astype(str).str.strip()
    ans["environment"] = ans["environment"].astype(str).str.strip()
    ans["key"] = [
        _canonical_key(g, e)
        for g, e in zip(ans["genotype"], ans["environment"])
    ]
    ans["has_observed_value"] = pd.to_numeric(ans["observed"], errors="coerce").notna()

    answer_keys = set(ans["key"])
    observed_keys = set(ans.loc[ans["has_observed_value"], "key"])
    pred_keys = set(pred["key"])

    key_present = pred["key"].isin(answer_keys)
    observed_present = pred["key"].isin(observed_keys)
    missing = pred.loc[~observed_present, ["genotype", "environment", "key"]].copy()
    missing["answer_key_present"] = missing["key"].isin(answer_keys)
    missing["missing_reason"] = missing["answer_key_present"].map(
        {True: "OFFICIAL_KEY_PRESENT_BUT_YIELD_MISSING", False: "OFFICIAL_ANSWER_KEY_ABSENT"}
    )
    missing = missing.drop(columns=["key"])
    missing.to_csv(missing_path, index=False)

    audit = pd.DataFrame(
        [
            {
                "n_sealed_predictions": int(len(pred)),
                "n_sealed_unique_keys": int(len(pred_keys)),
                "n_answer_rows": int(len(ans)),
                "n_answer_unique_keys": int(ans["key"].nunique()),
                "n_answer_unique_keys_with_observed_yield": int(len(observed_keys)),
                "n_sealed_keys_present_in_answer": int(key_present.sum()),
                "n_sealed_keys_with_observed_yield": int(observed_present.sum()),
                "n_sealed_keys_missing_observed_yield": int((~observed_present).sum()),
                "n_missing_because_answer_key_absent": int((~key_present).sum()),
                "n_missing_because_yield_is_na": int((key_present & ~observed_present).sum()),
                "sealed_observed_key_fraction": float(observed_present.mean()),
                "selection_rule_if_evaluated": "SEALED_KEY_AND_OFFICIAL_NONMISSING_OUTCOME_ONLY",
                "selection_uses_outcome_value": False,
            }
        ]
    )
    audit.to_csv(audit_path, index=False)
    return audit


def run(root: Path) -> dict[str, Path]:
    results = root / "reports" / "results"
    prediction_path = results / "case_study_b12_2022_sealed_predictions.csv"
    seal_path = results / "case_study_b12_2022_prediction_seal.json"

    # First operation with any reveal capability: verify committed Stage-A seal.
    seal = b12.verify_prediction_seal(prediction_path, seal_path)

    answer_path, provenance = acquire_answer_after_seal(
        prediction_path,
        seal_path,
        root / "data" / "raw" / "case_study_b12_2022_reveal" / ANSWER_BASENAME,
    )
    if provenance["prediction_sha256_verified_before_answer_access"] != seal["prediction_sha256"]:
        raise b12.SealViolation("B12B reveal provenance does not match prediction seal.")

    key_audit_path = results / "case_study_b12_2022_answer_key_audit.csv"
    missing_keys_path = results / "case_study_b12_2022_missing_answer_keys.csv"
    write_answer_key_audit(
        prediction_path,
        answer_path,
        key_audit_path,
        missing_keys_path,
    )

    summary, coverage, reliability = b12.evaluate_reveal(
        prediction_path,
        seal_path,
        answer_path,
    )
    summary_path = results / "case_study_b12_2022_external_validation_summary.csv"
    coverage_path = results / "case_study_b12_2022_external_coverage.csv"
    reliability_path = results / "case_study_b12_2022_external_reliability.csv"
    provenance_path = results / "case_study_b12_2022_reveal_provenance.json"

    summary.to_csv(summary_path, index=False)
    coverage.to_csv(coverage_path, index=False)
    reliability.to_csv(reliability_path, index=False)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "summary": summary_path,
        "coverage": coverage_path,
        "reliability": reliability_path,
        "provenance": provenance_path,
        "key_audit": key_audit_path,
        "missing_keys": missing_keys_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reveal and evaluate sealed B12 2022 predictions.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root.resolve())
    summary = pd.read_csv(paths["summary"])
    coverage = pd.read_csv(paths["coverage"])
    print("B12B external validation")
    print(summary.to_string(index=False))
    print("\nB12B external coverage")
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()
