"""Case Study B13-S: blind 2023 planting-date provenance recovery.

This audit is intentionally narrow. It may inspect one authoritative, outcome-free
metadata object from the official G2F 2024 competition release and map explicit
2023 planting dates back to the already-frozen B13A environment universe. It does
not open trait/phenotype outcomes, change the T1 clock, tune the predictor, or
reopen T2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

TARGET_YEAR = 2023
SOURCE_DOI = "10.25739/78mn-4394"
SOURCE_DATASET = "GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2025"
SOURCE_RELATIVE_PATH = "Training_data/2_Training_Meta_Data_2014_2023.csv"
SOURCE_IRODS_ROOT = f"/iplant/home/shared/commons_repo/curated/{SOURCE_DATASET}"
SOURCE_IRODS_PATH = f"{SOURCE_IRODS_ROOT}/{SOURCE_RELATIVE_PATH}"

B13A_ENVIRONMENT_AUDIT = Path(
    "reports/results/case_study_b13a_2023_environment_audit.csv"
)

FORBIDDEN_TOKENS = (
    "trait",
    "phenotyp",
    "observed",
    "answer",
    "1_training_trait_data_2014_2023.csv",
    "7_testing_observed_values.csv",
    "g2f_2023_phenotypic_data.csv",
)

EXACT_RECOVERY = "B13S_2023_EXACT_PLANTING_DATES_RECOVERED"
PARTIAL_RECOVERY = "B13S_2023_PARTIAL_PLANTING_DATE_RECOVERY"
NO_RECOVERY = "B13S_2023_NO_ADMISSIBLE_PLANTING_DATE_RECOVERY"
AMBIGUOUS_MAPPING = "B13S_2023_SOURCE_MAPPING_AMBIGUOUS"
BOUNDARY_VIOLATION = "B13S_OUTCOME_BOUNDARY_VIOLATION"

PLANTING_COLUMN_CANDIDATES = (
    "Planting_Date",
    "Planting Date",
    "Date_Planted",
    "Date Planted",
    "PlantingDate",
    "planting_date",
    "Sowing_Date",
    "Sowing Date",
    "sowing_date",
)

ENVIRONMENT_COLUMN_CANDIDATES = (
    "Env",
    "Environment",
    "environment",
    "Experiment_Code",
    "Experiment Code",
)

YEAR_COLUMN_CANDIDATES = ("Year", "year", "YEAR")


class OutcomeBoundaryViolation(RuntimeError):
    pass


def assert_safe_source_path(path: str) -> None:
    lower = path.lower()
    if path != SOURCE_RELATIVE_PATH:
        raise OutcomeBoundaryViolation(
            f"B13-S source is not allow-listed: {path}"
        )
    if any(token in lower for token in FORBIDDEN_TOKENS):
        raise OutcomeBoundaryViolation(
            f"B13-S forbidden outcome-bearing source token in path: {path}"
        )


def assert_blind_tree(root: Path) -> None:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        lower = path.name.lower()
        if any(token in lower for token in FORBIDDEN_TOKENS):
            raise OutcomeBoundaryViolation(
                f"B13-S forbidden outcome-bearing file entered staging tree: {path}"
            )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    exact = {str(c): str(c) for c in frame.columns}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]

    normalized = {
        re.sub(r"[^a-z0-9]+", "", str(c).lower()): str(c)
        for c in frame.columns
    }
    for candidate in candidates:
        key = re.sub(r"[^a-z0-9]+", "", candidate.lower())
        if key in normalized:
            return normalized[key]
    return None


def _normalize_env(value: object) -> str:
    text = str(value).strip().upper()
    text = re.sub(r"\s+", "", text)
    text = text.replace("-", "_")
    if text.endswith("_2023"):
        return text
    if re.fullmatch(r"[A-Z]{2,4}\d+", text):
        return f"{text}_2023"
    # Common competition metadata form can be state/location-year, e.g. IAH1_2023.
    return text


def _parse_exact_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    return parsed.dt.normalize()


def load_b13a_environment_universe(root: Path) -> pd.DataFrame:
    path = root / B13A_ENVIRONMENT_AUDIT
    frame = pd.read_csv(path)
    required = {"environment", "source_experiment_code"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"B13-S missing B13A environment columns: {sorted(missing)}")
    out = frame[["environment", "source_experiment_code"]].copy()
    out["environment"] = out["environment"].astype(str)
    out["source_experiment_code"] = out["source_experiment_code"].astype(str)
    if len(out) != 27:
        raise ValueError(f"B13-S expected 27 frozen B13A environments, found {len(out)}")
    if out["environment"].duplicated().any():
        raise ValueError("B13-S B13A environment universe is not unique")
    return out.sort_values("environment", kind="stable").reset_index(drop=True)


def audit_metadata(
    metadata: pd.DataFrame,
    frozen_envs: pd.DataFrame,
    *,
    source_sha256: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    env_col = _resolve_column(metadata, ENVIRONMENT_COLUMN_CANDIDATES)
    planting_col = _resolve_column(metadata, PLANTING_COLUMN_CANDIDATES)
    year_col = _resolve_column(metadata, YEAR_COLUMN_CANDIDATES)

    if env_col is None:
        raise ValueError(
            f"B13-S cannot resolve environment identifier; columns={list(metadata.columns)}"
        )

    work = metadata.copy()
    if year_col is not None:
        year_numeric = pd.to_numeric(work[year_col], errors="coerce")
        work = work[year_numeric.eq(TARGET_YEAR)].copy()
    else:
        # If year is encoded in the environment string, retain only explicit 2023 rows.
        mask = work[env_col].astype(str).str.contains("2023", case=False, na=False)
        work = work[mask].copy()

    work["normalized_environment"] = work[env_col].map(_normalize_env)

    frozen = frozen_envs.copy()
    frozen["normalized_environment"] = frozen["environment"].map(_normalize_env)

    if planting_col is None:
        rows = []
        for row in frozen.itertuples(index=False):
            rows.append(
                {
                    "environment": row.environment,
                    "source_experiment_code": row.source_experiment_code,
                    "source_raw_environment": "",
                    "source_environment_column": env_col,
                    "source_planting_column": "",
                    "source_raw_planting_value": "",
                    "recovered_planting_date": "",
                    "exact_unique_mapping": False,
                    "explicit_planting_semantics": False,
                    "admissible": False,
                    "failure_reason": "NO_EXPLICIT_PLANTING_OR_SOWING_COLUMN_IN_AUTHORITATIVE_METADATA",
                }
            )
        audit = pd.DataFrame(rows)
        decision = {
            "target_year": TARGET_YEAR,
            "source_doi": SOURCE_DOI,
            "source_sha256": source_sha256,
            "source_environment_column": env_col,
            "source_planting_column": "",
            "n_frozen_environments": len(frozen),
            "n_exactly_mapped_environments": 0,
            "n_admissible_planting_dates": 0,
            "all_27_recovered": False,
            "partial_recovery": False,
            "outcome_files_accessed": False,
            "point_predictor_changed": False,
            "t1_clock_changed": False,
            "t2_branch_reopened": False,
            "post_result_tuning_permitted": False,
            "decision": NO_RECOVERY,
            "reason": "NO_EXPLICIT_PLANTING_OR_SOWING_COLUMN_IN_AUTHORITATIVE_METADATA",
        }
        return audit, pd.DataFrame(), decision

    work["parsed_planting_date"] = _parse_exact_date(work[planting_col])

    source_rows = []
    recovery_rows = []
    ambiguous = False

    for frozen_row in frozen.itertuples(index=False):
        matches = work[
            work["normalized_environment"].eq(frozen_row.normalized_environment)
        ].copy()

        valid_dates = matches["parsed_planting_date"].dropna().drop_duplicates()
        exact_unique = len(matches) > 0 and len(valid_dates) == 1
        if len(valid_dates) > 1:
            ambiguous = True

        raw_env_values = "|".join(sorted(set(matches[env_col].astype(str)))) if len(matches) else ""
        raw_date_values = "|".join(
            sorted(set(matches[planting_col].dropna().astype(str)))
        ) if len(matches) else ""
        recovered = valid_dates.iloc[0].date().isoformat() if exact_unique else ""

        if len(matches) == 0:
            reason = "NO_SOURCE_ROW_FOR_FROZEN_ENVIRONMENT"
        elif len(valid_dates) == 0:
            reason = "SOURCE_ROW_HAS_NO_PARSEABLE_EXPLICIT_PLANTING_DATE"
        elif len(valid_dates) > 1:
            reason = "MULTIPLE_DISTINCT_EXPLICIT_PLANTING_DATES_FOR_ENVIRONMENT"
        else:
            reason = ""

        recovery_rows.append(
            {
                "environment": frozen_row.environment,
                "source_experiment_code": frozen_row.source_experiment_code,
                "source_raw_environment": raw_env_values,
                "source_environment_column": env_col,
                "source_planting_column": planting_col,
                "source_raw_planting_value": raw_date_values,
                "recovered_planting_date": recovered,
                "exact_unique_mapping": bool(exact_unique),
                "explicit_planting_semantics": True,
                "admissible": bool(exact_unique),
                "failure_reason": reason,
            }
        )

        for _, src in matches.iterrows():
            source_rows.append(
                {
                    "frozen_environment": frozen_row.environment,
                    "source_environment": str(src[env_col]),
                    "source_planting_value": str(src[planting_col]),
                    "parsed_planting_date": (
                        src["parsed_planting_date"].date().isoformat()
                        if pd.notna(src["parsed_planting_date"])
                        else ""
                    ),
                }
            )

    recovery = pd.DataFrame(recovery_rows).sort_values("environment", kind="stable")
    source_subset = pd.DataFrame(source_rows)

    n_exact = int(recovery["exact_unique_mapping"].sum())
    n_admissible = int(recovery["admissible"].sum())

    if ambiguous:
        state = AMBIGUOUS_MAPPING
        reason = "AT_LEAST_ONE_FROZEN_ENVIRONMENT_HAS_MULTIPLE_DISTINCT_EXPLICIT_PLANTING_DATES"
    elif n_admissible == len(frozen):
        state = EXACT_RECOVERY
        reason = "ALL_27_FROZEN_B13A_ENVIRONMENTS_HAVE_EXACT_UNIQUE_EXPLICIT_PLANTING_DATES"
    elif n_admissible > 0:
        state = PARTIAL_RECOVERY
        reason = "ONLY_A_STRICT_SUBSET_OF_FROZEN_B13A_ENVIRONMENTS_HAS_EXACT_UNIQUE_EXPLICIT_PLANTING_DATES"
    else:
        state = NO_RECOVERY
        reason = "NO_FROZEN_B13A_ENVIRONMENT_HAS_AN_ADMISSIBLE_EXACT_EXPLICIT_PLANTING_DATE"

    decision = {
        "target_year": TARGET_YEAR,
        "source_doi": SOURCE_DOI,
        "source_sha256": source_sha256,
        "source_environment_column": env_col,
        "source_planting_column": planting_col,
        "n_frozen_environments": len(frozen),
        "n_exactly_mapped_environments": n_exact,
        "n_admissible_planting_dates": n_admissible,
        "all_27_recovered": bool(n_admissible == len(frozen)),
        "partial_recovery": bool(0 < n_admissible < len(frozen)),
        "outcome_files_accessed": False,
        "point_predictor_changed": False,
        "t1_clock_changed": False,
        "t2_branch_reopened": False,
        "post_result_tuning_permitted": False,
        "decision": state,
        "reason": reason,
    }
    return recovery, source_subset, decision


def run(root: Path, metadata_path: Path) -> dict[str, Path]:
    assert_safe_source_path(SOURCE_RELATIVE_PATH)
    staging_root = metadata_path.parent
    assert_blind_tree(staging_root)

    frozen = load_b13a_environment_universe(root)
    metadata = pd.read_csv(metadata_path, low_memory=False)
    source_sha = sha256_file(metadata_path)

    recovery, source_subset, decision = audit_metadata(
        metadata,
        frozen,
        source_sha256=source_sha,
    )

    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)
    recovery_path = results / "case_study_b13s_2023_planting_date_recovery.csv"
    subset_path = results / "case_study_b13s_2023_source_rows.csv"
    decision_path = results / "case_study_b13s_2023_lock_decision.csv"
    seal_path = results / "case_study_b13s_2023_source_seal.json"

    recovery.to_csv(recovery_path, index=False)
    source_subset.to_csv(subset_path, index=False)
    pd.DataFrame([decision]).to_csv(decision_path, index=False)

    seal = {
        "target_year": TARGET_YEAR,
        "source_doi": SOURCE_DOI,
        "source_dataset": SOURCE_DATASET,
        "source_relative_path": SOURCE_RELATIVE_PATH,
        "source_irods_path": SOURCE_IRODS_PATH,
        "source_sha256": source_sha,
        "source_size_bytes": int(metadata_path.stat().st_size),
        "outcome_files_accessed": False,
        "allowed_source_only": True,
        "frozen_environment_count": int(len(frozen)),
        "recovery_decision": decision["decision"],
    }
    seal_path.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert_blind_tree(staging_root)
    return {
        "recovery": recovery_path,
        "source_rows": subset_path,
        "decision": decision_path,
        "seal": seal_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run B13-S blind planting-date recovery audit.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    paths = run(args.output_root, args.metadata)
    print("Case Study B13-S planting-date recovery audit complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
