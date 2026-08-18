# Case Study B14C — 2024 External Reveal Results

## Status

B14C completed the prospectively locked 2024 external reveal against the official Genomes to Fields observed-values object after the B14B 798-cell prediction artifact had already been sealed and merged.

No result in this document changes the pre-reveal protocol in `docs/case_study_b14c_2024_sealed_reveal.md`.

## Provenance

Frozen B14B prediction SHA-256:

`91c765ea994f557db1911865309bca94ebc2110b87a5fea483a03c879d1fb19d`

Official 2024 outcome object:

`/iplant/home/shared/commons_repo/curated/GenomesToFields_GenotypeByEnvironment_PredictionCompetition_2025/Testing_data/7_Testing_Observed_Values.csv`

Official release DOI:

`10.25739/78mn-4394`

Outcome SHA-256 at first authorized reveal:

`8bd354c44bce50abd09a9839272112fdb34bdb96ec6e37ae644eda916aeeabcc`

The scientific seal gate verified the B14B prediction artifact before outcome acquisition. The raw official outcome file is not redistributed in this repository.

## Primary cohort

The prospectively declared estimand was:

`OFFICIALLY_OBSERVABLE_SEALED_KEYS`

Of 798 sealed prediction keys:

- 779 were present in the official 2024 key set;
- 19 were absent from the official key set;
- all 92 sealed genotypes remained represented;
- all 19 sealed environments remained represented.

Selection used exact `(environment, genotype)` key presence only. Numerical yield was not used to select the primary cohort. There was no post-reveal protocol amendment.

## Point-prediction performance

On the 779 officially observable sealed cells:

| Metric | Result |
|---|---:|
| RMSE | 2.6197348508709113 |
| MAE | 2.1234900139513737 |
| R-squared | 0.14844019270495168 |
| Pearson correlation | 0.390901094352944 |

These are external-validation diagnostics only. B14C performed no predictor refit or hyperparameter search.

## Interval comparison

B14C evaluated exactly the two intervals stored in the sealed B14B artifact.

### C0 — frozen B11 90% rule

`FROZEN_B11_90`

| Quantity | Result |
|---|---:|
| Nominal coverage | 0.90 |
| Empirical coverage | 0.9139922978177151 |
| Environment-balanced coverage | 0.8997721030003023 |
| Environment-cluster 95% CI | [0.8784860752085061, 0.9441202835715959] |
| Absolute coverage gap | 0.01399229781771505 |
| Mean half-width | 4.351707411572972 |
| Mean proper 90% interval score | 10.530072493745173 |
| Frozen calibration criterion | **PASS** |

C0 satisfied both predeclared requirements: its absolute empirical coverage gap was no larger than three percentage points and its environment-cluster confidence interval contained 0.90.

### C1 — one-sided cluster drift guard

`ONE_SIDED_CLUSTER_DRIFT_GUARD_90`

The exact semantic quantile level remained the pre-reveal value:

`0.9512813317177465`

The immutable B14B CSV represents the same value at its frozen 12-decimal serialization as `0.951281331718`.

| Quantity | Result |
|---|---:|
| Nominal coverage | 0.90 |
| Empirical coverage | 0.9576379974326059 |
| Environment-balanced coverage | 0.9521031534328204 |
| Environment-cluster 95% CI | [0.9316040863734756, 0.9786058430589681] |
| Absolute coverage gap | 0.05763799743260589 |
| Mean half-width | 5.141229360485013 |
| Mean proper 90% interval score | 11.10625188277593 |
| Frozen calibration criterion | **FAIL** |

C1 overcovered relative to the prospectively locked 90% criterion. Its environment-cluster interval sat wholly above 0.90, its mean half-width was larger than C0's, and its mean proper interval score was worse. C1 therefore cannot be promoted.

## Frozen machine state and naming audit

The pre-reveal decision function emitted:

`B14C_BOTH_INTERVAL_RULES_PASS_KEEP_FROZEN_B11`

The label is a legacy state-name defect for the realized branch. The authoritative machine booleans are:

- `control_calibration_pass = true`
- `adaptive_calibration_pass = false`

The state label is intentionally preserved rather than renamed after reveal. Introducing a new terminal label after observing 2024 outcomes would violate the prospectively frozen state machine. The scientific interpretation follows the stored booleans and scores: **retain the frozen B11 rule and reject promotion of the adaptive guard**.

Future prospective state machines should include an explicit `CONTROL_PASS_ADAPTIVE_FAIL_KEEP_CONTROL` state before any new outcomes are revealed.

## Environment heterogeneity

The aggregate result does not imply homogeneous deployment behavior.

Control 90% environment-level coverage ranged from 0.7333 in GAH1_2024 and OHH1_2024 to 1.00 in several environments. The adaptive guard increased coverage in many low-coverage environments, but its uniform widening also pushed many already-well-covered environments toward 0.98–1.00 coverage.

The adaptive interval score was lower than the control score in a subset of difficult environments, including DEH1_2024, GAH1_2024, IAH2_2024, NYH2_2024 and OHH1_2024, but was worse in aggregate. This is descriptive evidence of environment heterogeneity, not authorization to tune an environment-specific 2024 rule retrospectively.

## Support diagnostic

Every primary cell was classified as:

`WITHIN_TRAINING_NN_ENVELOPE / RETAIN_SUPPORTED`

Thus:

- support did not select the primary cohort;
- no 2024 support threshold was tuned;
- support abstention again provided no prospective selective-error separation in this cohort.

The support mechanism remains unvalidated as an abstention rule.

## Scientific interpretation

The B12 2022 undercoverage signal did not transport monotonically into 2024. Carrying the full 2022 environment-balanced coverage deficit forward as a one-sided increase in calibration level produced excessive 2024 width and overcoverage.

This rejects the simple hypothesis that a previous season's calibration deficit should be propagated one-for-one and only upward into the next admissible deployment season.

At the same time, B14C does not establish universal transportability of the original B11 rule. The 2022 failure and 2024 recovery together indicate a more difficult structure: calibration error appears temporally nonstationary and may change sign, revert, or depend on environment composition rather than follow a monotone drift process.

The evidence therefore favors a future theory of **calibration transport under signed, environment-heterogeneous temporal drift**, but 2024 outcomes must not be used to fit that theory inside B14C.

## Integrity statement

B14C closes with:

- no reseal;
- no predictor refit;
- no genomic re-encoding;
- no T1-clock modification;
- no T2 reopening;
- no quantile-level tuning;
- no interval-width tuning;
- no support-threshold tuning;
- no outcome-dependent cohort selection;
- no nominal-coverage switching;
- no raw outcome redistribution.

The negative result for the one-sided drift guard is retained as scientific evidence.