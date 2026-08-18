# Case Study B14C — Seal-First 2024 External Reveal and Drift-Guard Test

## Purpose

B14C is the outcome-reveal stage for the already-sealed B14B 2024 prediction artifact. It tests the frozen `G+E_T1` point predictor and exactly two predeclared 90% interval competitors against the official 2024 observed-values object.

B14C is not a refit stage. It cannot alter the B14B prediction artifact, candidate universe, point-predictor parameters, frozen B5 genomic representation, `T1_30DAP` clock, support threshold, interval construction, adaptive level, calibration chronology, or closed T2 branch.

## Pre-reveal seal gate

Before the official outcome object may be acquired, B14C must verify on `main`:

- B14B decision: `B14B_2024_SEALED_PREDICTIONS_READY_FOR_REVEAL`;
- prediction SHA-256: `91c765ea994f557db1911865309bca94ebc2110b87a5fea483a03c879d1fb19d`;
- candidate-universe SHA-256: `32e4f308522ee849e498d2bf0614f3ec349574a27bb327fefeb80e0f4e05bf7f`;
- 798 predictions, 92 genotypes, 19 environments;
- `observed_values_accessed=false`;
- `prediction_generated_pre_outcome=true`;
- no point-predictor, genomic representation, T1-clock or T2 change;
- no post-result tuning permission.

Any mismatch aborts before outcome acquisition.

## Official outcome source

The only outcome-bearing object authorized for B14C is the official Genomes to Fields 2024 competition object:

`/iplant/home/shared/commons_repo/curated/GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2025/Testing_data/7_Testing_Observed_Values.csv`

The release is associated with DOI `10.25739/78mn-4394`.

The acquired object is SHA-256 hashed immediately and preserved in the reveal manifest. No alternative answer source may replace it after results are seen.

## Primary estimand

The primary estimand is prospectively fixed as:

`OFFICIALLY_OBSERVABLE_SEALED_KEYS`

A B14B prediction belongs to the primary cohort if and only if its exact `(Env, Hybrid)` key is present in the official observed-values object. Cohort membership therefore uses key presence only and never the numerical yield value.

The official source is normalized to:

- `Hybrid` -> `genotype`
- `Env` -> `environment`
- `Yield_Mg_ha` -> `observed`

No fuzzy matching, aliasing, genotype reconstruction, environment-name repair, outcome-dependent filtering, imputation or aggregation is permitted.

If the official file contains duplicate `(Env, Hybrid)` keys, B14C aborts. If a sealed key is present but its `Yield_Mg_ha` is missing or non-numeric, B14C aborts rather than silently deleting that row. Sealed keys absent from the official key set remain in the key audit but are outside the primary estimand by the predeclared rule.

## Point-prediction evaluation

On the primary cohort, B14C reports:

- RMSE;
- MAE;
- R-squared;
- Pearson correlation.

These metrics are descriptive external-validation results. They do not trigger model retuning.

## Locked interval competitors

B14C evaluates exactly the intervals already stored in the B14B sealed artifact.

### C0

`FROZEN_B11_90`

Control quantile level: `0.90`.

### C1

`ONE_SIDED_CLUSTER_DRIFT_GUARD_90`

Adaptive quantile level: `0.9512813317177465`.

The 2023 branch supplied no admissible calibration feedback, so the carried-forward state remains:

`NO_2023_FEEDBACK_AVAILABLE_CARRY_FORWARD_2022_DRIFT_STATE`.

No interval is recomputed from 2024 outcomes.

## Calibration criterion

For each competitor, empirical coverage is

`mean(lower <= observed <= upper)`.

The inherited B11/B12 calibration criterion is passed only when both conditions hold:

1. absolute gap from 0.90 is at most 0.03; and
2. the B11 environment-cluster bootstrap 95% confidence interval contains 0.90.

B14C also reports environment-balanced coverage, but it does not replace the inherited pass criterion.

## Efficiency criterion

The proper central-90% interval score is the already-locked B13 score:

`S = (U-L) + 20(L-y) I(y<L) + 20(y-U) I(y>U)`.

C1 is promoted only if C1 passes calibration and its mean interval score is strictly lower than C0's mean interval score. Equality or numerical ties retain the simpler frozen B11 rule.

## Predeclared terminal decisions

- `B14C_ADAPTIVE_DRIFT_GUARD_PROMOTED`
- `B14C_ADAPTIVE_CALIBRATION_PASS_BUT_INEFFICIENT`
- `B14C_BOTH_INTERVAL_RULES_PASS_KEEP_FROZEN_B11`
- `B14C_BOTH_INTERVAL_RULES_FAIL`
- `B14C_PRIMARY_EVALUATION_ABORTED_DATA_INTEGRITY`
- `B14C_PRE_REVEAL_SEAL_MISMATCH`

No fifth performance interpretation may be invented after reveal.

## Support diagnostic

The B14B support/reliability state is evaluated only as a frozen diagnostic. B14C may report counts and retrospective error/coverage by the pre-existing reliability state, but support cannot change primary-cohort membership and no support threshold may be tuned on 2024.

## Post-reveal prohibition

After outcome access, B14C forbids:

- resealing predictions;
- predictor refitting or hyperparameter search;
- genomic re-encoding or import of the release's 2,425-SNP representation;
- T1-clock modification;
- T2 reopening;
- quantile-level tuning;
- interval-width tuning;
- support-threshold tuning;
- changing the estimand or missing-key rule;
- switching nominal coverage because another level looks better.

A negative B14C result is retained as scientific evidence.

## Operational reveal audit

The first automated reveal attempt failed before the pre-reveal gate artifact was written and before the official outcome object was acquired. That failure therefore exposed no 2024 yield values and changed no scientific rule. The subsequent workflow hardening only reorders operational steps so that the immutable B14B seal is verified before external CyVerse tooling is installed and adds bounded network retries. This documentation-only commit is an explicit retry trigger; it changes no B14C estimand, model, interval, calibration, promotion, or missing-key rule.