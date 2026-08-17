# Case Study B12 — Sealed 2022 External Temporal Validation

## Question

After B11 admitted a strictly chronological T1 residual-interval layer on the 2018–2021 backtest, B12 asks the first genuinely untouched-time question:

> **Does the frozen `G+E_T1` architecture, together with the frozen B11 interval mechanism, survive an external 2022 season when predictions are sealed before 2022 yield is revealed?**

B12 is not another model-selection stage. It is an external temporal validation protocol.

## External source

B12 uses the public **Genomes to Fields 2022 Maize Genotype by Environment Prediction Competition** resource:

- DOI: `10.25739/tq5e-ak26`;
- historical/training period supplied by the competition: 2014–2021;
- testing year: 2022;
- testing inputs and the observed-answer file are distributed separately.

That separation allows the prediction artifact to be generated and cryptographically frozen before the official 2022 outcome file is accessed.

## Frozen scientific state

B12 inherits the following decisions unchanged:

- supported predictor: `G+E_T1`;
- horizon: `T1_30DAP`;
- genomic rank: 20;
- environmental rank: 16;
- environmental RBF gamma multiplier: 2.0;
- ridge alpha: 10.0;
- T2 adaptive branch: closed;
- B11 interval levels: 80%, 90%, 95%;
- B11 hard environmental-support boundary: unchanged;
- post-result tuning: prohibited.

No 2022 result is used to alter these settings and then re-score 2022.

## Conservative genotype-support rule

The 2022 competition contains hybrids that do not necessarily have an exact marker vector in the frozen B5 `GENO.csv` matrix. B12 therefore does **not** replace, rederive, augment, or reorder the genomic representation before the external test.

A 2022 cell is eligible only when its hybrid already has an exact row in the frozen B5 genomic matrix. Eligible cells are labeled `SUPPORTED_FROZEN_B5_GENOME`; unsupported hybrids are not assigned a manufactured genomic vector and are excluded from the external prediction set.

This deliberately narrows B12 to a portability test of the frozen model rather than changing the genomic representation in response to the new season.

## Environment-input rule

For each 2022 environment, B12 reconstructs only information available at T1:

- planting date and coordinates from the 2022 testing metadata;
- NASA POWER weather from planting through **30 DAP only**;
- static SSURGO soil identity;
- planting/management context when available.

Weather after 30 DAP is not requested by the Stage-A feature builder. An environment without the required frozen T1 context is marked `UNSUPPORTED_T1_CONTEXT` and is not included in the sealed prediction set.

## Historical encoding reproduction

Before 2022 is appended, the B12 single-horizon encoder reproduces the frozen historical T1 environment representation. This prevents a seemingly minor encoding rewrite from becoming an unregistered model change.

## Stage A — immutable prediction seal

Stage A is blind to 2022 observed yield. It acquires only the 2022 submission template and testing metadata, builds the frozen T1 input state, predicts the supported cells, attaches the frozen B11 interval layer, and writes a canonical prediction artifact containing no observed 2022 outcome.

The resulting seal is:

| Field | Frozen value |
|---|---|
| Prediction SHA-256 | `fb8347da2a5ba9fff0d106fa9b7a13037818c8e0e0d1387527dbf090c3085220` |
| Sealed predictions | **420** |
| Environments | **14** |
| Genotypes | **43** |
| Observed 2022 outcomes accessed | **False** |
| Predictive hyperparameters changed | **False** |
| T2 branch reopened | **False** |
| Post-result tuning permitted | **False** |

The Stage-A machine state is:

`SEALED_2022_PREDICTIONS_READY_FOR_REVEAL`

The 420-row artifact is retained permanently. It is not replaced or re-sealed after outcome access.

## Stage B — seal-first reveal

Stage B recomputes the prediction SHA-256 before resolving the official answer file. The answer is acquired only after the committed prediction digest matches the frozen seal.

The official answer contains **10,290 unique genotype-environment keys with observed yield**, but only **387 of the 420 sealed B12 keys** are present. The remaining **33 sealed keys are absent from the official answer entirely**; the failure is not caused by numerical yield values or NA outcomes.

Therefore the strict original B12 primary test cannot evaluate the complete sealed cohort. Its formal state is:

`B12_PRIMARY_INCOMPLETE_OFFICIAL_OUTCOME_MATCH`

This is an evaluation-cohort completeness failure, not a model-performance pass or failure. The original confirmatory B12 test remains incomplete.

## Post-reveal available-case diagnostic

After the incomplete official-key match was discovered, a separate diagnostic was added without modifying the 420-row seal.

The diagnostic includes a sealed prediction if and only if its exact `(genotype, environment)` key exists in the official answer file. Cohort membership is constructed from identifier presence before numerical outcomes are merged. It therefore does not select cases by yield magnitude, prediction error, interval coverage, environmental support, or any other result-dependent quantity.

The diagnostic is explicitly labeled:

`POST_REVEAL_AVAILABLE_CASE_DIAGNOSTIC`

and:

- `confirmatory = False`;
- `post_reveal_protocol_amendment = True`;
- `selection_uses_outcome_value = False`;
- `sealed_artifact_replaced_or_resealed = False`;
- `predictive_model_refit_after_reveal = False`;
- `interval_retuned_after_reveal = False`;
- `support_threshold_retuned_after_reveal = False`;
- `t2_branch_reopened = False`;
- `post_result_tuning_permitted = False`.

Unit tests additionally verify that replacing the numerical yields with radically different values while preserving the same official key set cannot change the diagnostic cohort.

## 2022 available-case prediction result

The outcome-observable diagnostic contains **387 sealed predictions**, **43 genotypes**, and **14 environments**.

| Metric | 2022 diagnostic |
|---|---:|
| RMSE | **2.8037** |
| MAE | **2.2800** |
| R² | **0.0890** |
| Correlation | **0.3588** |

These are external 2022 measurements for the officially observable portion of the frozen sealed cohort. They are not a replacement confirmatory score for the 420-row primary test.

## External interval transport

The B11 interval mechanism was frozen before the 2022 reveal. Its available-case external coverage is:

| Nominal | Empirical coverage | Environment-balanced coverage | Environment-cluster 95% interval | Mean width | Absolute gap |
|---|---:|---:|---:|---:|---:|
| 80% | **75.97%** | 77.19% | [62.79%, 87.71%] | 6.914 | 4.03 pp |
| 90% | **85.27%** | 84.87% | [77.40%, 92.54%] | 8.703 | **4.73 pp** |
| 95% | **93.80%** | 93.21% | [90.55%, 96.63%] | 10.230 | 1.20 pp |

The predeclared B11/B12 90% criterion required both:

1. an absolute coverage gap of at most three percentage points; and
2. an environment-cluster 95% interval containing 90%.

The second condition holds, but the first does not: 85.27% coverage is **4.73 percentage points below nominal**. Therefore the diagnostic machine decision is:

`B12_AVAILABLE_CASE_DIAGNOSTIC_90_CRITERION_NOT_MET`

Because the available-case analysis was defined after the official key incompleteness was revealed, this is not renamed as the original confirmatory `B12_2022_CALIBRATION_TRANSPORT_FAILURE`. The scientifically correct interpretation is narrower:

> **The frozen B11 chronological interval layer does not transport cleanly to the officially observable 2022 sealed subset under its predeclared 90% tolerance.**

The result is negative external evidence for calibration stability and is retained without interval inflation or retrospective correction.

## Temporal heterogeneity

The pooled 2022 coverage miss is not uniform across environments. Available-case 90% coverage ranges from approximately **47.1%** in `WIH1_2022` to **100%** in several Texas and North Carolina environments. Environment-level RMSE also varies substantially.

This strengthens the central warning already visible in B11: pooled chronological calibration can appear approximately adequate while local or seasonal coverage changes materially under temporal/environmental shift.

B12 therefore identifies **calibration transport under nonstationarity** as the next reliability problem. It does not justify widening every interval by a retrospectively selected constant or tuning an environment-specific correction on 2022 and calling the result external validation.

## Environmental support and abstention

All **387 officially observable B12 predictions** remain `RETAIN_SUPPORTED` under the frozen B11 environmental-support envelope. There are no `ABSTAIN_LOW_ENVIRONMENT_SUPPORT` cases in the observable 2022 diagnostic cohort.

Consequently:

- no external retained-versus-abstained risk comparison is available;
- support-based abstention is still not admitted;
- the B11 support boundary remains diagnostic;
- the absence of a low-support case is not converted into a softer post-hoc threshold.

The external year therefore reinforces the earlier conclusion that the current support geometry has not yet earned promotion to a deployment abstention rule.

## Scientific interpretation

B12 produces three separate results that must not be conflated.

First, the **sealed forecasting protocol works**: the model and intervals were generated without observed 2022 outcomes, frozen to an immutable SHA-256 artifact, and later evaluated through a seal-first reveal path.

Second, the **original primary cohort is incomplete** because the official answer omits 33 of the 420 sealed genotype-environment keys. This prevents a full confirmatory B12 verdict and is preserved transparently rather than solved by silently shrinking and re-sealing the cohort.

Third, the **387-case post-reveal diagnostic supplies adverse external calibration evidence**. The 90% interval covers only 85.27%, exceeding the predeclared three-percentage-point tolerance. The 95% interval remains closer to nominal, but B12 does not switch the primary level after seeing outcomes.

The practical architecture therefore remains:

\[
G+E_{T1}
\rightarrow \widehat Y
\rightarrow \text{chronological residual interval}
\rightarrow \text{external calibration audit},
\]

with an explicit warning that the interval layer is sensitive to temporal/environmental transport.

## Locked consequences

B12 does **not** authorize any of the following on 2022:

- refitting the predictor and reporting the new score as external validation;
- increasing interval widths until 90% coverage passes;
- choosing a new nominal level because 95% happened to behave better;
- changing the environmental-support threshold;
- selecting a new genomic representation;
- reopening T2;
- deleting hard 2022 environments based on errors;
- re-sealing the prediction artifact around the 387 observable outcomes.

The 2022 outcome information may be used only as historical information in a separately predeclared future-year protocol.

## Reproducibility

Core implementation:

- `src/plant_intelligence/uncertainty/maize_external_temporal_validation.py`
- `src/plant_intelligence/uncertainty/maize_b12_reveal_runner.py`
- `src/plant_intelligence/uncertainty/maize_b12_available_case_diagnostic.py`
- `tests/test_case_study_b12_external_temporal_validation.py`
- `tests/test_case_study_b12_available_case_diagnostic.py`

Workflows:

- `.github/workflows/case-study-b12a-sealed-2022-prediction.yml`
- `.github/workflows/case-study-b12b-reveal-2022-evaluation.yml`
- `.github/workflows/case-study-b12b-available-case-diagnostic.yml`

Published evidence:

- `reports/results/case_study_b12_2022_sealed_predictions.csv`
- `reports/results/case_study_b12_2022_prediction_seal.json`
- `reports/results/case_study_b12a_seal_decision.csv`
- `reports/results/case_study_b12_2022_answer_key_audit.csv`
- `reports/results/case_study_b12_2022_missing_answer_keys.csv`
- `reports/results/case_study_b12_2022_primary_status.csv`
- `reports/results/case_study_b12_2022_available_case_summary.csv`
- `reports/results/case_study_b12_2022_available_case_coverage.csv`
- `reports/results/case_study_b12_2022_available_case_reliability.csv`
- `reports/results/case_study_b12_2022_available_case_by_environment.csv`
- `reports/results/case_study_b12_2022_available_case_cohort_audit.csv`

The successful available-case workflow verifies the immutable Stage-A seal before answer access, resolves a schema-valid official answer through the seal-first CyVerse path, runs the diagnostic guardrails, and publishes only explicitly non-confirmatory evidence.
