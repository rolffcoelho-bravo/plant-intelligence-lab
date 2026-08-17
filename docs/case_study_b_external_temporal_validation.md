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
- testing inputs and the observed-answer file are distributed as separate files.

The separation between test inputs and `Test_Set_Observed_Values_ANSWER.csv` makes a computational seal possible.

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

No B12 result may be used to retroactively change these settings and then re-score 2022.

## Conservative genotype-support rule

The 2022 competition contains hybrids that may not have an exact marker vector in the frozen B5 `GENO.csv` matrix.

B12 does **not** replace, rederive, augment, or reorder the frozen marker representation before the external test. A 2022 cell is eligible only when its hybrid already has an exact row in the frozen B5 genomic matrix.

Eligible cells are labeled:

`SUPPORTED_FROZEN_B5_GENOME`

Other cells are labeled:

`UNSUPPORTED_GENOTYPE_NOT_IN_FROZEN_B5_GENOME`

They are not assigned a manufactured genomic vector and are not included in the external performance claim.

This intentionally narrows B12 to a strict portability test of the frozen model rather than silently changing the genomic representation to improve 2022 coverage.

## Environment-input rule

For each 2022 environment, B12 reconstructs only the information allowed at T1:

- planting date and coordinates from the 2022 testing metadata;
- NASA POWER weather from planting through **30 DAP only**;
- static SSURGO soil identity;
- planting/management context when available.

The Stage-A weather request ends at the T1 issuance date. Weather after 30 DAP is not requested by the feature builder.

If the required frozen T1 context cannot be reconstructed, the environment is labeled:

`UNSUPPORTED_T1_CONTEXT`

and its cells are excluded from the sealed prediction set.

## Historical encoding reproduction

Before 2022 is appended, the B12 single-horizon encoder must exactly reproduce the frozen B10 historical T1 environment matrix. A mismatch in row order, feature columns, or numeric values aborts B12.

This prevents an apparently minor encoding rewrite from becoming an unregistered model change.

## Stage A — prediction seal

Stage A is blind to 2022 observed yield.

It may acquire only:

- `Testing_Data/1_Submission_Template_2022.csv`;
- `Testing_Data/2_Testing_Meta_Data_2022.csv`.

The Stage-A raw directory is scanned for the official answer basename. If `Test_Set_Observed_Values_ANSWER.csv` is present, Stage A aborts.

The frozen predictor is fit on the existing B5 2014–2021 materialized training cells. Intervals for 2022 are calibrated only from the already-locked B10/B11 forward residuals from 2016–2021.

The Stage-A output contains prediction, interval, support, and reliability fields but **no observed 2022 outcome**.

The prediction CSV is canonicalized, sorted by environment and genotype, and hashed with SHA-256. The resulting seal records:

- exact prediction hash;
- number of predictions, environments, and genotypes;
- target year;
- model/horizon identity;
- calibration years;
- support rules;
- `observed_outcomes_accessed = false`;
- `t2_branch_reopened = false`;
- `predictive_hyperparameters_changed = false`;
- `post_result_tuning_permitted = false`.

The Stage-A machine state is:

`SEALED_2022_PREDICTIONS_READY_FOR_REVEAL`

## Stage B — reveal

Stage B is a separate manual workflow.

Before the official answer is read, B12 recomputes the SHA-256 digest of the sealed prediction CSV. If even one byte differs, evaluation aborts.

Only after the seal passes may Stage B acquire `Test_Set_Observed_Values_ANSWER.csv` and merge observed yield with the sealed supported subset.

No predictor is refit after reveal.

No interval is recalibrated after reveal.

No support threshold is changed after reveal.

T2 remains closed.

## External admission rule

The main B12 interval check remains the predeclared 90% criterion inherited from B11:

1. absolute empirical-coverage gap from 90% must be at most 3 percentage points; and
2. the environment-cluster 95% interval for coverage must contain 90%.

If this fails, the result is:

`B12_2022_CALIBRATION_TRANSPORT_FAILURE`

The failure is retained. The 2022 outcomes may then become historical information for a separately predeclared 2023 procedure, but they may not be used to repair and re-score 2022.

If the interval criterion passes while environmental abstention remains unsupported, the result is:

`B12_2022_EXTERNAL_INTERVALS_PASS_SUPPORT_ABSTENTION_DIAGNOSTIC`

If 2022 contains enough environments beyond the frozen support boundary and the predeclared retained-versus-abstained risk condition succeeds, the stronger state is:

`B12_2022_EXTERNAL_INTERVALS_AND_SUPPORT_ABSTENTION_PASS`

## What B12 can establish

A successful B12 result would provide evidence that the frozen T1 prediction-and-uncertainty architecture transports from the 2014–2021 research block into a later 2022 season for the explicitly supported genotype/environment subset.

It would be materially stronger than another resampling exercise inside 2016–2021.

## What B12 cannot establish

B12 does not establish:

- universal performance on every 2022 competition hybrid;
- performance for genotypes lacking the frozen B5 marker vector;
- universal future-year calibration;
- live prospective field coverage;
- a new T2 result;
- permission to tune the model on 2022 and report the tuned score as external validation;
- that environmental support is a useful abstention rule unless 2022 independently supplies enough low-support environments and the locked criterion passes.

## Implementation

- `src/plant_intelligence/uncertainty/maize_external_temporal_validation.py`
- `tests/test_case_study_b12_external_temporal_validation.py`
- `.github/workflows/case-study-b12a-sealed-2022-prediction.yml`
- `.github/workflows/case-study-b12b-reveal-2022-evaluation.yml`

Stage A and Stage B are intentionally separate workflows so the prediction artifact can be committed and independently identified before the outcome file is ever accessed by the evaluation stage.
