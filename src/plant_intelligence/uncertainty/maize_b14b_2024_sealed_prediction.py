"""Case Study B14B: sealed 2024 prediction issuance with no outcome access.

B14B consumes only the B14A frozen 798-cell candidate universe and the same
pre-outcome 2024 metadata used by B14A. It reconstructs the frozen G+E_T1 point
predictor, carries the B13 drift-guard level forward unchanged because 2023 had
no admissible feedback, attaches both locked 90% interval competitors and the
frozen support diagnostic, then writes an immutable SHA-256 prediction seal.

The official 2024 observed-values file is forbidden throughout this module.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from plant_intelligence.models.maize_forecast_time_prediction import FROZEN_CONFIG
from plant_intelligence.models.maize_forward_support_diagnostics import support_geometry
from plant_intelligence.uncertainty import maize_b14a_2024_source_compatibility as b14a
from plant_intelligence.uncertainty import maize_b13_forward_drift_calibration as b13
from plant_intelligence.uncertainty import maize_external_temporal_validation as b12
from plant_intelligence.uncertainty.maize_forward_uncertainty import (
    ABSTAIN,
    HORIZON,
    MODEL,
    RETAIN,
    SUPPORT_EDGE,
    SUPPORT_WITHIN,
    finite_sample_quantile,
    support_group,
)

TARGET_YEAR = 2024
EXPECTED_B14A_DECISION = "B14A_2024_READY_FOR_PREOUTCOME_SEAL"
EXPECTED_CANDIDATE_SHA256 = "32e4f308522ee849e498d2bf0614f3ec349574a27bb327fefeb80e0f4e05bf7f"
EXPECTED_N_CELLS = 798
EXPECTED_N_GENOTYPES = 92
EXPECTED_N_ENVIRONMENTS = 19
EXPECTED_ADAPTIVE_LEVEL = 0.9512813317177465
CONTROL_LEVEL = 0.90
CONTROL = b13.CONTROL
ADAPTIVE = b13.ADAPTIVE
NO_2023_FEEDBACK = "NO_2023_FEEDBACK_AVAILABLE_CARRY_FORWARD_2022_DRIFT_STATE"
SEAL_SCHEMA = "plant-intelligence-lab/b14b-2024-prediction-seal/v1"
SEALED_DECISION = "B14B_2024_SEALED_PREDICTIONS_READY_FOR_REVEAL"
FORBIDDEN_BASENAME = b14a.FORBIDDEN_BASENAME


class B14BSealViolation(RuntimeError):
    pass


def _bool_false(value: object) -> bool:
    return str(value).strip().lower() == "false"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_b14a_gate(results: Path) -> pd.DataFrame:
    decision = pd.read_csv(results / "case_study_b14a_2024_lock_decision.csv")
    if len(decision) != 1:
        raise B14BSealViolation("B14B requires exactly one B14A decision row.")
    row = decision.iloc[0]
    checks = (
        int(row["target_year"]) == TARGET_YEAR,
        str(row["decision"]) == EXPECTED_B14A_DECISION,
        int(row["n_candidate_cells"]) == EXPECTED_N_CELLS,
        int(row["n_candidate_genotypes"]) == EXPECTED_N_GENOTYPES,
        int(row["n_candidate_environments"]) == EXPECTED_N_ENVIRONMENTS,
        str(row["candidate_universe_sha256"]) == EXPECTED_CANDIDATE_SHA256,
        str(row["historical_t1_encoder_exactly_reproduced"]).strip().lower() == "true",
        str(row["combined_t1_matrix_constructed"]).strip().lower() == "true",
        _bool_false(row["observed_values_accessed"]),
        _bool_false(row["prediction_generated"]),
        _bool_false(row["point_predictor_changed"]),
        _bool_false(row["b5_genotype_representation_changed"]),
        _bool_false(row["new_2425_snp_representation_imported"]),
        _bool_false(row["t1_clock_changed"]),
        _bool_false(row["t2_branch_reopened"]),
        _bool_false(row["post_result_tuning_permitted"]),
    )
    if not all(checks):
        raise B14BSealViolation("B14B detected a change in the merged B14A gate.")
    return decision


def verify_b13_carry_forward(results: Path) -> pd.DataFrame:
    lock = pd.read_csv(results / "case_study_b13_preoutcome_lock.csv")
    if len(lock) != 1:
        raise B14BSealViolation("B14B requires exactly one B13 lock row.")
    row = lock.iloc[0]
    if str(row["control_rule"]) != CONTROL or str(row["adaptive_rule"]) != ADAPTIVE:
        raise B14BSealViolation("B14B B13 competitor identities changed.")
    if not np.isclose(float(row["adaptive_quantile_level"]), EXPECTED_ADAPTIVE_LEVEL, rtol=0, atol=1e-15):
        raise B14BSealViolation("B14B adaptive quantile level differs from the frozen B13 lock.")
    if not _bool_false(row["point_predictor_changed"]) or not _bool_false(row["t2_branch_reopened"]):
        raise B14BSealViolation("B14B refuses a B13 lock that changes the predictor or reopens T2.")

    closure = pd.read_csv(results / "case_study_b13s_2023_lock_decision.csv")
    if len(closure) != 1 or str(closure.iloc[0]["decision"]) != "B13S_2023_NO_ADMISSIBLE_PLANTING_DATE_RECOVERY":
        raise B14BSealViolation("B14B requires the immutable B13-S 2023 no-feedback closure.")
    if not _bool_false(closure.iloc[0]["outcome_files_accessed"]):
        raise B14BSealViolation("B14B refuses 2023 outcome access.")
    return lock


def verify_candidate_universe(path: Path) -> pd.DataFrame:
    cells = pd.read_csv(path)
    if list(cells.columns) != ["genotype", "environment"]:
        raise B14BSealViolation("B14B candidate-universe schema changed.")
    cells["genotype"] = cells["genotype"].astype(str)
    cells["environment"] = cells["environment"].astype(str)
    if cells.duplicated(["genotype", "environment"]).any():
        raise B14BSealViolation("B14B candidate universe contains duplicate keys.")
    digest = b14a.canonical_hash(cells)
    if digest != EXPECTED_CANDIDATE_SHA256:
        raise B14BSealViolation("B14B candidate-universe SHA-256 mismatch.")
    if len(cells) != EXPECTED_N_CELLS:
        raise B14BSealViolation("B14B candidate-universe row count changed.")
    if cells["genotype"].nunique() != EXPECTED_N_GENOTYPES:
        raise B14BSealViolation("B14B candidate genotype count changed.")
    if cells["environment"].nunique() != EXPECTED_N_ENVIRONMENTS:
        raise B14BSealViolation("B14B candidate environment count changed.")
    return cells.sort_values(["environment", "genotype"], kind="mergesort").reset_index(drop=True)


def reconstruct_frozen_2024_t1(root: Path, candidate: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    results = root / "reports" / "results"
    raw = root / "data" / "raw" / "case_study_b14a_2024_safe"
    b14a.assert_blind_tree(raw)
    paths, source_manifest, _ = b14a.read_safe_sources(root)
    metadata = pd.read_csv(paths["metadata"], low_memory=False)
    environment_audit = b14a.build_environment_metadata_audit(
        metadata, set(candidate["environment"].astype(str))
    )
    states_2024, reconstruction = b14a.reconstruct_t1_states(environment_audit)
    supported = set(states_2024["environment"].astype(str)) if not states_2024.empty else set()
    required = set(candidate["environment"].astype(str))
    if supported != required:
        missing = sorted(required - supported)
        extra = sorted(supported - required)
        raise B14BSealViolation(
            f"B14B could not reproduce the exact frozen 19-environment T1 set; missing={missing}, extra={extra}."
        )

    states_hist = pd.read_csv(results / "case_study_b9_safe_environment_states.csv", low_memory=False)
    manifest_hist = pd.read_csv(results / "case_study_b9_environment_manifest.csv", low_memory=False)
    b12.audit_historical_t1_encoding(states_hist, manifest_hist)
    manifest_2024 = environment_audit[environment_audit["environment"].isin(required)].copy()
    t1_matrix = b12.build_combined_t1_matrix(
        states_hist, manifest_hist, states_2024, manifest_2024
    )
    b14a.assert_blind_tree(raw)
    return t1_matrix, source_manifest, reconstruction


def calibration_half_widths(calibration: pd.DataFrame, state: str) -> tuple[float, float, str]:
    group = calibration[calibration["support_group"].astype(str).eq(state)]
    enough = int(group["environment"].nunique()) >= 5 and len(group) >= 200
    residuals = group["absolute_error"] if enough else calibration["absolute_error"]
    source = "SUPPORT_GROUP_CHRONOLOGICAL_2016_2021" if enough else "GLOBAL_CHRONOLOGICAL_2016_2021_FALLBACK"
    control = finite_sample_quantile(residuals, CONTROL_LEVEL)
    adaptive = finite_sample_quantile(residuals, EXPECTED_ADAPTIVE_LEVEL)
    if adaptive + 1e-12 < control:
        raise B14BSealViolation("Adaptive B14B interval became narrower than control.")
    return float(control), float(adaptive), source


def attach_locked_uncertainty(
    predictions: pd.DataFrame,
    t1_matrix: pd.DataFrame,
    train_envs: set[str],
    calibration: pd.DataFrame,
) -> pd.DataFrame:
    support, _ = support_geometry(
        t1_matrix,
        train_envs,
        set(predictions["environment"].astype(str)),
        gamma_multiplier=FROZEN_CONFIG.gamma_multiplier,
        retained_rank=FROZEN_CONFIG.e_rank,
        prefix="full",
    )
    if "full_nearest_distance" not in support.columns and "full_nearest_z" in support.columns:
        support = support.copy()
        support["full_nearest_distance"] = support["full_nearest_z"]
    support["support_group"] = support["full_nearest_percentile"].map(support_group)
    support["reliability_state"] = np.where(
        support["support_group"].eq(SUPPORT_EDGE), ABSTAIN, RETAIN
    )
    keep = [
        "environment",
        "full_nearest_distance",
        "full_nearest_percentile",
        "full_max_training_kernel_similarity",
        "support_group",
        "reliability_state",
    ]
    out = predictions.merge(support[keep], on="environment", validate="many_to_one")
    for state in (SUPPORT_WITHIN, SUPPORT_EDGE):
        control, adaptive, source = calibration_half_widths(calibration, state)
        mask = out["support_group"].astype(str).eq(state)
        out.loc[mask, "control_half_width_90"] = control
        out.loc[mask, "adaptive_half_width_90"] = adaptive
        out.loc[mask, "calibration_source"] = source
    if out[["control_half_width_90", "adaptive_half_width_90"]].isna().any().any():
        raise B14BSealViolation("B14B failed to assign locked half-widths to every prediction.")
    out["control_lower_90"] = out["predicted"] - out["control_half_width_90"]
    out["control_upper_90"] = out["predicted"] + out["control_half_width_90"]
    out["adaptive_lower_90"] = out["predicted"] - out["adaptive_half_width_90"]
    out["adaptive_upper_90"] = out["predicted"] + out["adaptive_half_width_90"]
    out["control_rule"] = CONTROL
    out["adaptive_rule"] = ADAPTIVE
    out["control_quantile_level"] = CONTROL_LEVEL
    out["adaptive_quantile_level"] = EXPECTED_ADAPTIVE_LEVEL
    out["calibration_feedback_state"] = NO_2023_FEEDBACK
    out["test_year"] = TARGET_YEAR
    out["model"] = MODEL
    out["horizon"] = HORIZON
    out["genotype_support_state"] = "SUPPORTED_FROZEN_B5_GENOME"
    out["environment_input_state"] = "SUPPORTED_T1_CONTEXT"
    out["support_boundary_uses_outcome"] = False
    out["observed_values_accessed"] = False
    return out


def canonical_prediction_bytes(frame: pd.DataFrame) -> bytes:
    required = {
        "genotype", "environment", "predicted", "control_lower_90", "control_upper_90",
        "adaptive_lower_90", "adaptive_upper_90", "support_group", "reliability_state",
        "calibration_feedback_state",
    }
    missing = required - set(frame.columns)
    if missing:
        raise B14BSealViolation(f"B14B seal frame missing columns: {sorted(missing)}")
    canonical = frame.sort_values(["environment", "genotype"], kind="mergesort").reset_index(drop=True)
    buffer = io.StringIO()
    canonical.to_csv(buffer, index=False, lineterminator="\n", float_format="%.12g")
    return buffer.getvalue().encode("utf-8")


def write_seal(frame: pd.DataFrame, prediction_path: Path, seal_path: Path, source_manifest: pd.DataFrame) -> dict[str, object]:
    body = canonical_prediction_bytes(frame)
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    prediction_path.write_bytes(body)
    seal = {
        "schema": SEAL_SCHEMA,
        "stage": "B14B_2024_SEALED_PREDICTION_ISSUANCE",
        "target_year": TARGET_YEAR,
        "prediction_file": prediction_path.name,
        "prediction_sha256": hashlib.sha256(body).hexdigest(),
        "candidate_universe_sha256": EXPECTED_CANDIDATE_SHA256,
        "n_predictions": int(len(frame)),
        "n_genotypes": int(frame["genotype"].nunique()),
        "n_environments": int(frame["environment"].nunique()),
        "control_rule": CONTROL,
        "control_quantile_level": CONTROL_LEVEL,
        "adaptive_rule": ADAPTIVE,
        "adaptive_quantile_level": EXPECTED_ADAPTIVE_LEVEL,
        "calibration_feedback_state": NO_2023_FEEDBACK,
        "calibration_years": "2016-2021",
        "source_sha256": {row["logical_name"]: row["sha256"] for row in source_manifest.to_dict("records")},
        "observed_values_accessed": False,
        "prediction_generated_pre_outcome": True,
        "point_predictor_changed": False,
        "b5_genotype_representation_changed": False,
        "t1_clock_changed": False,
        "t2_branch_reopened": False,
        "post_result_tuning_permitted": False,
    }
    seal_path.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return seal


def verify_seal(prediction_path: Path, seal_path: Path) -> dict[str, object]:
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("schema") != SEAL_SCHEMA:
        raise B14BSealViolation("B14B prediction seal schema mismatch.")
    if sha256_file(prediction_path) != seal.get("prediction_sha256"):
        raise B14BSealViolation("B14B prediction artifact does not match its SHA-256 seal.")
    if seal.get("candidate_universe_sha256") != EXPECTED_CANDIDATE_SHA256:
        raise B14BSealViolation("B14B seal points to a different candidate universe.")
    if bool(seal.get("observed_values_accessed", True)):
        raise B14BSealViolation("B14B seal reports outcome access.")
    return seal


def run(root: Path) -> dict[str, Path]:
    root = root.resolve()
    results = root / "reports" / "results"
    results.mkdir(parents=True, exist_ok=True)
    verify_b14a_gate(results)
    verify_b13_carry_forward(results)
    candidate = verify_candidate_universe(results / "case_study_b14a_2024_candidate_universe.csv")

    t1_matrix, source_manifest, reconstruction = reconstruct_frozen_2024_t1(root, candidate)
    states_hist = pd.read_csv(results / "case_study_b9_safe_environment_states.csv", low_memory=False)
    manifest_hist = pd.read_csv(results / "case_study_b9_environment_manifest.csv", low_memory=False)
    forward = pd.read_csv(results / "case_study_b9_forward_year_folds.csv", low_memory=False)

    predicted, train_envs = b12._predict_supported(root, candidate, t1_matrix)
    calibration = b12.historical_calibration_table(root, states_hist, manifest_hist, forward)
    if int(calibration["test_year"].min()) != 2016 or int(calibration["test_year"].max()) != 2021:
        raise B14BSealViolation("B14B calibration pool changed from frozen 2016-2021 chronology.")
    sealed = attach_locked_uncertainty(predicted, t1_matrix, train_envs, calibration)
    if len(sealed) != EXPECTED_N_CELLS:
        raise B14BSealViolation("B14B did not generate exactly 798 sealed predictions.")

    prediction_path = results / "case_study_b14b_2024_sealed_predictions.csv"
    seal_path = results / "case_study_b14b_2024_prediction_seal.json"
    decision_path = results / "case_study_b14b_2024_seal_decision.csv"
    reconstruction_path = results / "case_study_b14b_2024_t1_reconstruction_audit.csv"
    source_path = results / "case_study_b14b_2024_source_manifest.csv"

    reconstruction.to_csv(reconstruction_path, index=False)
    source_manifest.to_csv(source_path, index=False)
    seal = write_seal(sealed, prediction_path, seal_path, source_manifest)
    verify_seal(prediction_path, seal_path)
    pd.DataFrame([
        {
            "stage": "B14B",
            "decision": SEALED_DECISION,
            "prediction_sha256": seal["prediction_sha256"],
            "candidate_universe_sha256": EXPECTED_CANDIDATE_SHA256,
            "n_predictions": EXPECTED_N_CELLS,
            "n_genotypes": EXPECTED_N_GENOTYPES,
            "n_environments": EXPECTED_N_ENVIRONMENTS,
            "control_rule": CONTROL,
            "adaptive_rule": ADAPTIVE,
            "adaptive_quantile_level": EXPECTED_ADAPTIVE_LEVEL,
            "calibration_feedback_state": NO_2023_FEEDBACK,
            "observed_values_accessed": False,
            "point_predictor_changed": False,
            "b5_genotype_representation_changed": False,
            "t1_clock_changed": False,
            "t2_branch_reopened": False,
            "post_result_tuning_permitted": False,
        }
    ]).to_csv(decision_path, index=False)
    b14a.assert_blind_tree(root / "data" / "raw" / "case_study_b14a_2024_safe")
    return {
        "predictions": prediction_path,
        "seal": seal_path,
        "decision": decision_path,
        "t1_reconstruction_audit": reconstruction_path,
        "source_manifest": source_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run sealed B14B 2024 pre-outcome prediction issuance.")
    parser.add_argument("--output-root", type=Path, default=Path("."))
    args = parser.parse_args()
    paths = run(args.output_root)
    print("Case Study B14B sealed 2024 prediction issuance complete")
    for key, path in paths.items():
        print(f"{key}: {path}")


if __name__ == "__main__":
    main()
