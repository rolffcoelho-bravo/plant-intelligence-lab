# Case Study B14B — Sealed 2024 Prediction Issuance

## Purpose

B14B is the sealed prediction stage authorized by the positive B14A compatibility gate. It generates predictions for exactly the frozen 798 genotype-environment cells and stops before any 2024 observed yield is accessed.

The frozen candidate universe is:

- 798 cells;
- 92 exact frozen-B5 hybrids;
- 19 environments with complete frozen `T1_30DAP` context;
- candidate SHA-256 `32e4f308522ee849e498d2bf0614f3ec349574a27bb327fefeb80e0f4e05bf7f`.

## Point predictor

The point model remains the frozen B10/B11/B12 architecture:

`G+E_T1`, horizon `T1_30DAP`.

No point-model hyperparameter, genomic representation, environment representation, kernel rank, RBF scale, ridge penalty, or T1 clock is changed.

## Uncertainty competitors

B14B issues exactly two central 90% interval rules.

### C0 — frozen B11 control

`FROZEN_B11_90`

For each frozen B11 support group, the interval half-width is the finite-sample 0.90 quantile of the chronological 2016–2021 absolute residual pool. Sparse support groups use the already-defined global chronological fallback.

### C1 — carried-forward drift guard

`ONE_SIDED_CLUSTER_DRIFT_GUARD_90`

The adaptive quantile level remains exactly:

`0.9512813317177465`.

This level was locked from the 2022 environment-balanced undercoverage deficit. Because the 2023 branch closed without an admissible outcome-bearing prediction experiment, B14B receives no 2023 calibration feedback. The state is therefore:

`NO_2023_FEEDBACK_AVAILABLE_CARRY_FORWARD_2022_DRIFT_STATE`.

The 2023 non-result is not converted into a pseudo-observation and the adaptive level is not updated.

## Support state

The frozen B11 environmental support geometry is evaluated before outcome access. Reliability state is diagnostic only. No support threshold is tuned on 2024 outcomes.

## Source boundary

B14B may stage only the same two pre-outcome objects sealed by B14A:

- `Testing_data/1_Submission_Template_2024.csv`
- `Testing_data/2_Testing_Meta_Data_2024.csv`

Their SHA-256 hashes must match the B14A source seal exactly.

`Testing_data/7_Testing_Observed_Values.csv` is forbidden until the B14B prediction SHA-256 has been committed to Git history.

## Seal

The canonical prediction artifact is sorted by environment and genotype and serialized with deterministic floating-point formatting. The seal records:

- prediction SHA-256;
- candidate-universe SHA-256;
- prediction/genotype/environment counts;
- both interval rules and quantile levels;
- the no-2023-feedback state;
- 2016–2021 calibration chronology;
- source hashes;
- integrity flags proving no outcome access, no predictor change, no genomic representation change, no T1-clock change, no T2 reopening and no post-result tuning.

The only successful terminal state is:

`B14B_2024_SEALED_PREDICTIONS_READY_FOR_REVEAL`.

B14C may access the official 2024 observed-values file only after this sealed artifact is committed.
