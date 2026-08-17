# Case Study B13 — Sequential Calibration-Drift Adaptation

## Question

B12 produced the first untouched-time warning for the admitted B11 uncertainty layer. The frozen T1 point predictor remained unchanged, but the 90% interval layer covered only 85.27% of the 387 officially observable sealed 2022 cells, outside the predeclared three-percentage-point tolerance.

B13 therefore asks a narrower and more useful question:

> **Can uncertainty be updated sequentially after a calibration-transport failure, using only information available before the next target season, without refitting the point predictor or tuning on the next outcome?**

B13 is not a new predictive-model search. It is a prospective test of an uncertainty-update rule.

## External 2023 target

The target season is 2023.

For a harmonized metadata/trait interface, B13 uses the public **Genomes to Fields 2024 Maize Genotype by Environment Prediction Competition** package, DOI `10.25739/78mn-4394`. That competition package contains training data through 2023 and distributes metadata separately from trait outcomes.

The original G2F 2023 field-season release is retained as provenance under DOI `10.25739/rzzy-3n27`.

Stage A may acquire only the harmonized metadata file:

`Training_data/2_Training_Meta_Data_2014_2023.csv`

The target trait file is forbidden during Stage A:

`Training_data/1_Training_Trait_Data_2014_2023.csv`

Only Stage B may acquire or read that trait file.

## Frozen predictive state

B13 keeps the predictive system inherited from B10/B11/B12 unchanged:

- predictor: `G+E_T1`;
- horizon: `T1_30DAP`;
- genomic rank: 20;
- environmental rank: 16;
- environmental RBF gamma multiplier: 2.0;
- ridge alpha: 10.0;
- frozen B5 genomic representation;
- B11 environmental support boundary;
- T2 branch closed.

The 2022 B12 outcomes may update **uncertainty only**. They may not refit the point predictor, alter its hyperparameters, replace the genomic representation, retune the support threshold, or reopen T2.

## The two sealed interval competitors

B13 seals two interval systems around the exact same point prediction.

### 1. `B11_FROZEN`

This is the original B11/B12 interval rule. For each nominal level and support group, its half-width is the locked chronological residual quantile obtained from the 2016–2021 forward-validation history.

Let

`q_B11(alpha, s)`

be that frozen half-width for nominal level `alpha` and support group `s`.

### 2. `B13_RECENCY_ENVELOPE`

The only adaptive rule is fixed before 2023 outcomes are seen.

From the 387 observable sealed B12 cells, compute the global finite-sample 2022 absolute-residual quantile

`q_2022(alpha)`.

Then define

`q_B13(alpha, s) = max(q_B11(alpha, s), q_2022(alpha))`.

This rule has three deliberate properties:

1. it uses only information available through 2022;
2. it can never make the inherited interval narrower;
3. it contains no target-year parameter fitted from 2023 outcomes.

No alternative decay rate, mixture weight, rolling-window length, threshold, or quantile transformation is searched after the 2023 reveal.

## Why the update is global in its 2022 component

B12 supplied only 14 environments and all 387 observable cells remained `RETAIN_SUPPORTED`. That is not enough evidence to estimate a new low-support-specific update reliably. B13 therefore uses the 2022 residual distribution only as a global recent-error envelope while preserving the frozen B11 support-group baseline underneath it.

This avoids manufacturing a subgroup effect that B12 did not actually identify.

## Stage-A environment information

For every usable 2023 environment, B13 reconstructs the same T1-safe context used by B12:

- planting date and coordinates from harmonized G2F metadata;
- NASA POWER realized weather only from planting through 30 DAP;
- SSURGO soil identity;
- planting-population context when available.

Weather after 30 DAP is not requested.

An environment lacking the required frozen T1 context is labeled:

`UNSUPPORTED_T1_CONTEXT`

and is excluded from the sealed prediction roster.

Before 2023 is appended, the historical T1 encoder must exactly reproduce the frozen B10/B11 matrix. Any mismatch aborts B13.

## Outcome-free prediction roster

B12 exposed a protocol weakness: its prediction cohort was defined from the competition submission template, but the official answer later omitted 33 exact keys.

B13 avoids that problem by defining the Stage-A roster without target outcomes and without target trait rows.

The sealed roster is the Cartesian product:

`frozen B5 genotype IDs × supported 2023 T1 environments`.

Its machine label is:

`FROZEN_B5_GENOTYPES_X_SUPPORTED_2023_ENVIRONMENTS`

The target trait file plays no role in deciding which cells are predicted.

## Predeclared Stage-B evaluation cohort

Because not every frozen genotype is necessarily planted and phenotyped in every 2023 environment, B13 predeclares the evaluation rule **before reveal**:

`PREDECLARED_2023_FINITE_YIELD_KEY_INTERSECTION`

After the seal is verified, the 2023 trait file is read and finite yields are aggregated by exact genotype-environment key using:

`ARITHMETIC_MEAN_OF_FINITE_PLOT_YIELDS_BY_EXACT_KEY`

The evaluation cohort is then the exact intersection of:

- sealed Stage-A prediction keys; and
- exact 2023 genotype-environment keys having at least one finite yield.

Selection therefore uses **outcome availability**, because a key must have a finite observation to be evaluable, but it does **not** use outcome magnitude. Once an exact key is eligible, no post-reveal deletion based on the value of yield or prediction error is permitted.

For a meaningful external comparison, B13 requires at least:

- 100 evaluated exact keys; and
- 5 evaluated environments.

Otherwise the state is:

`B13_INSUFFICIENT_EXTERNAL_OVERLAP`.

## Stage A — dual-interval seal

Before 2023 yield is accessed, Stage A freezes:

- every 2023 point prediction;
- every B11 interval;
- every B13 recency-envelope interval;
- support and reliability fields;
- the complete drift-policy table;
- the evaluation-cohort policy;
- the trait aggregation policy.

The prediction CSV and drift-policy CSV receive separate SHA-256 digests. The prediction seal stores both hashes.

The sealed machine state is:

`SEALED_2023_DUAL_INTERVALS_READY_FOR_REVEAL`.

The seal records explicitly:

- `target_outcomes_accessed = false`;
- `historical_2022_outcomes_used_for_uncertainty_update = true`;
- `predictive_model_refit_for_b13 = false`;
- `support_threshold_retuned = false`;
- `t2_branch_reopened = false`;
- `post_target_tuning_permitted = false`.

## Stage B — reveal

Stage B must verify both frozen SHA-256 digests **before** acquiring or reading the target trait file.

After reveal, neither interval system may be modified.

The two methods are evaluated on exactly the same predeclared 2023 cohort.

## Primary interval criterion

The primary comparison remains the B11/B12 90% criterion.

For each method independently:

1. the absolute empirical-coverage gap from 90% must be at most 3 percentage points; and
2. the environment-cluster 95% interval for coverage must contain 90%.

The decision states are fixed before reveal:

- adaptive passes, frozen B11 fails: `B13_DRIFT_ADAPTATION_RESTORES_90_CALIBRATION`;
- both pass: `B13_BOTH_INTERVAL_RULES_PASS_90_CALIBRATION`;
- frozen B11 passes, adaptive fails: `B13_DRIFT_ADAPTATION_DEGRADES_90_CALIBRATION`;
- both fail: `B13_DRIFT_ADAPTATION_INSUFFICIENT`;
- insufficient cohort: `B13_INSUFFICIENT_EXTERNAL_OVERLAP`.

The 80% and 95% levels remain secondary calibration diagnostics. They may not replace the predeclared 90% decision after seeing results.

## Point-prediction metrics

B13 also reports RMSE, MAE, R² and correlation on the predeclared 2023 evaluation cohort. These diagnose temporal transport of the frozen point predictor but do not control the B13 uncertainty decision.

## Environmental support

The B11 environmental-support boundary remains frozen and diagnostic. B13 reports retained/abstained states but does not search for a new support threshold from 2023 errors.

If B13 happens to produce external abstention cases, they may be analyzed under the already-frozen boundary. They cannot be used to retrospectively optimize that boundary and re-score 2023.

## Interpretation boundary

A successful B13 result would support a specific claim:

> a one-step recency envelope, fixed after observing 2022 and before seeing 2023, can improve or preserve external interval calibration for the frozen T1 predictor.

It would not prove universal calibration, optimal online conformal prediction, universal genotype transport, or superiority of the point predictor.

A failed B13 result is equally informative. It would show that the B12 calibration drift cannot be repaired by this simple nonshrinking one-step update and would motivate a later methodology that models the dynamics of residual distributions themselves.

## Implementation

- `src/plant_intelligence/uncertainty/maize_b13_sequential_drift_calibration.py`
- `tests/test_case_study_b13_sequential_drift_calibration.py`
- `.github/workflows/case-study-b13a-sealed-2023-drift-calibration.yml`
- `.github/workflows/case-study-b13b-reveal-2023-evaluation.yml`

No 2023 result belongs in this document until the Stage-A prediction and drift-policy hashes have been frozen and Stage B has completed against those exact artifacts.
