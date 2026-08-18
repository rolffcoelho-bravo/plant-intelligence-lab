# Plant Intelligence Lab — Documentation Guide

This directory preserves the technical record behind the public research-software project. The main README summarizes the project; the documents here expose the full data-science process, including data locks, validation design, model comparisons, uncertainty, external evaluation, failure diagnosis, and scientific closure.

Stage labels such as B10, B12, or B14 are provenance identifiers. They make the experimental chronology auditable; they are not separate products.

## Core project documentation

- [`methodology.md`](methodology.md) — quantitative methodology and software architecture.
- [`biological_context.md`](biological_context.md) — biological context for the evaluated plant problems.
- [`limitations.md`](limitations.md) — project-wide interpretation and deployment boundaries.
- [`transferability.md`](transferability.md) — discussion of what parts of the workflow may transfer to other biotechnology settings.
- [`Plant_Intelligence_Lab_Technical_Architecture.pdf`](Plant_Intelligence_Lab_Technical_Architecture.pdf) — technical architecture reference.

## Case Study A — Arabidopsis

Case Study A is summarized in the repository README and supported by the reproducible notebooks, source modules, machine-readable results, empirical figures, and the existing technical decision report under `reports/`.

Useful code areas:

- `src/plant_intelligence/genetics/`
- `src/plant_intelligence/forecasting/`
- `src/plant_intelligence/optimization/`
- `src/plant_intelligence/uncertainty/`

## Case Study B — Wheat G×E benchmark

Start here for the categorical multi-environment benchmark:

- [`case_study_b_data_lock.md`](case_study_b_data_lock.md) — source, dimensions, and frozen validation design.
- [`case_study_b_modeling.md`](case_study_b_modeling.md) — classical G, E, and G×E benchmark.
- [`case_study_b_ml.md`](case_study_b_ml.md) — high-dimensional machine-learning challengers.
- [`case_study_b_uncertainty.md`](case_study_b_uncertainty.md) — uncertainty and deployment boundaries.

## Case Study B — Maize environmental transfer

These documents show how the data-science problem was extended from categorical environments to measurable environmental representations:

- [`case_study_b_environment_transfer.md`](case_study_b_environment_transfer.md) — Genomes-to-Fields data lock and first continuous-environment benchmark.
- [`case_study_b_transfer_robustness.md`](case_study_b_transfer_robustness.md) — representation robustness and environmental novelty diagnostics.
- [`case_study_b_biological_environment.md`](case_study_b_biological_environment.md) — target-proximal audit and biological process/stage ablations.
- [`case_study_b_decision_horizons.md`](case_study_b_decision_horizons.md) — retrospective decision-time information frontier.

## Forecast-time deployment program

The next sequence makes information availability explicit and then tests it under chronological validation:

- [`case_study_b_prospective_environment.md`](case_study_b_prospective_environment.md) — issuance-safe environmental states and forward-year lock.
- [`case_study_b_forecast_time_prediction.md`](case_study_b_forecast_time_prediction.md) — T0/T1/T2 prediction and Value-of-Waiting evidence.
- [`case_study_b_forward_support_diagnostics.md`](case_study_b_forward_support_diagnostics.md) — support and environmental-geometry diagnosis.
- [`case_study_b_training_only_geometry_selection.md`](case_study_b_training_only_geometry_selection.md) — strictly training-only geometry selection test.
- [`case_study_b_temporal_geometry_stability.md`](case_study_b_temporal_geometry_stability.md) — temporal persistence audit.
- [`case_study_b_geometry_robust_aggregation.md`](case_study_b_geometry_robust_aggregation.md) — symmetric aggregation and T2 branch closure.
- [`case_study_b_forward_uncertainty.md`](case_study_b_forward_uncertainty.md) — strictly chronological residual calibration and selective-risk diagnostics.

## External evaluation

The external sequence is preserved without rewriting incomplete or negative states:

- [`case_study_b_external_temporal_validation.md`](case_study_b_external_temporal_validation.md) — sealed 2022 predictions, incomplete official-key match, and separately labeled available-case diagnostic.
- [`case_study_b13_forward_drift_calibration.md`](case_study_b13_forward_drift_calibration.md) — pre-outcome uncertainty comparison lock.
- [`case_study_b13a_2023_source_audit.md`](case_study_b13a_2023_source_audit.md) and [`case_study_b13s_2023_planting_date_recovery.md`](case_study_b13s_2023_planting_date_recovery.md) — 2023 information-interface closure.
- [`case_study_b14a_2024_source_compatibility.md`](case_study_b14a_2024_source_compatibility.md) — 2024 source compatibility and candidate universe.
- [`case_study_b14b_2024_sealed_prediction.md`](case_study_b14b_2024_sealed_prediction.md) — immutable 2024 prediction seal.
- [`case_study_b14c_2024_sealed_reveal.md`](case_study_b14c_2024_sealed_reveal.md) — reveal protocol and official-key cohort.
- [`case_study_b14c_2024_results.md`](case_study_b14c_2024_results.md) — completed 2024 point and interval results.
- [`case_study_b16_error_structure_diagnostic.md`](case_study_b16_error_structure_diagnostic.md) — postoutcome error-structure diagnosis without model repair.

## Scientific closure and audit history

The repository preserves negative theory/novelty checks because they show how unsupported claims were stopped rather than promoted. They are supporting provenance, not the public identity of the project.

- [`case_study_b_closure_and_contribution_audit.md`](case_study_b_closure_and_contribution_audit.md) — final Case Study B scientific closure and contribution boundary.
- [`case_study_b15_calibration_transportability_theory.md`](case_study_b15_calibration_transportability_theory.md) and associated B15 audit files — calibration/feedback theory boundary.
- [`case_study_b17_t1_architecture_contraction_novelty.md`](case_study_b17_t1_architecture_contraction_novelty.md) — additive-architecture structural audit.
- [`case_study_b18_forecast_time_hypothesis_audit.md`](case_study_b18_forecast_time_hypothesis_audit.md) — forecast-time hypothesis/prior-art gate.

## Machine-readable evidence

The authoritative numerical and protocol artifacts live under `reports/results/`. Important entry points include:

- `case_study_b_claim_boundary.csv` — compact allowed/prohibited claim boundary;
- `case_study_b_evidence_hierarchy.csv` — evidence classification through Case Study B closure;
- `case_study_b_closure_lock.json` and `case_study_b_closure_decision.csv` — final scientific closure state;
- `case_study_b14b_2024_prediction_seal.json` — immutable 2024 prediction seal;
- `case_study_b14c_2024_primary_summary.csv` and `case_study_b14c_2024_interval_summary.csv` — authoritative 2024 evaluation summaries;
- `case_study_b16_2024_error_structure_summary.csv` — postoutcome diagnostic summary;
- `case_study_b18_decision.csv` — terminal B18 novelty decision.

Empirical graphics are under `reports/figures/`. Raw public data are excluded from Git where the acquisition/reconstruction code and provenance records are sufficient to rebuild the analysis.
