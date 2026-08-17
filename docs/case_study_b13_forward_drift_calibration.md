# Case Study B13 — Forward Drift Calibration

## Locked question

B12 showed that the frozen B11 chronological 90% interval layer did not transport cleanly into the externally held-out 2022 season. B13 asks the next genuinely forward question:

> Can a calibration rule learn from the already-revealed 2022 calibration error, freeze a new uncertainty rule before 2023 outcomes are accessed, and improve 2023 reliability without changing the frozen point predictor?

B13 is an uncertainty-update experiment. It is **not** a new point-model selection stage.

## Scientific state inherited unchanged

B13 keeps the following decisions fixed:

- point predictor: `G+E_T1`;
- horizon: `T1_30DAP`;
- genomic rank: 20;
- environmental rank: 16;
- environmental RBF gamma multiplier: 2.0;
- ridge alpha: 10.0;
- T2 adaptive branch: closed;
- genomic representation: frozen B5 marker matrix;
- no 2023 point-model refit or hyperparameter search;
- no 2023 support-threshold tuning;
- no 2023 outcome access before the prediction/interval artifact is sealed.

The B12 result remains immutable and is not rescored.

## Why B13 is needed

B11 pooled forward calibration looked acceptable inside the 2018–2021 research block, but the externally sealed 2022 diagnostic produced 90% empirical coverage of 85.27% and environment-balanced coverage of 84.87%. The environment-cluster 95% interval still contained 90%, but the absolute empirical coverage gap exceeded the predeclared three-point tolerance.

The failure suggests that the residual distribution itself is temporally nonstationary. B13 therefore treats calibration as a sequential state variable rather than assuming that a single historical residual quantile transports indefinitely.

## Literature boundary

B13 does not claim that adaptive online conformal prediction is novel. Relevant prior families include Adaptive Conformal Inference, aggregated ACI, strongly adaptive online conformal prediction, conformal PID control, and online-optimization approaches.

The narrower B13 contribution is an auditable experimental design for **season-batched, environment-clustered genotype-by-environment forecasting** under an immutable point predictor and a seal-before-reveal protocol.

## Two locked competitors

B13 compares exactly two 90% interval rules.

### C0 — `FROZEN_B11_90`

The control reproduces the B11/B12 chronological rule without using the 2022 calibration error to change its target quantile level.

For the 2023 forecast, let

\[
\mathcal R_{\le 2022}=\{|Y_i-\hat Y_i|: \text{eligible revealed residuals through 2022}\}.
\]

The control half-width is

\[
q^{(0)}_{2023}=Q_{0.90}^{\mathrm{FS}}(\mathcal R_{\le 2022}),
\]

where \(Q_p^{\mathrm{FS}}\) is the same finite-sample order-statistic quantile used in B11.

### C1 — `ONE_SIDED_CLUSTER_DRIFT_GUARD_90`

The adaptive competitor uses the previous season's **environment-balanced** 90% coverage, not cell-weighted coverage, as feedback.

Let

\[
\bar C_{2022}^{env}=\frac{1}{|\mathcal E_{2022}|}\sum_{e\in\mathcal E_{2022}} C_{e,2022},
\]

where \(C_{e,2022}\) is the fraction of officially observable sealed cells covered in environment \(e\).

Define the one-sided calibration deficit

\[
d_{2022}=\max\{0,\;0.90-\bar C_{2022}^{env}\}.
\]

The 2023 adaptive quantile level is frozen as

\[
p^{(1)}_{2023}=\min\{0.995,\;0.90+d_{2022}\}.
\]

The adaptive half-width is

\[
q^{(1)}_{2023}=Q_{p^{(1)}_{2023}}^{\mathrm{FS}}(\mathcal R_{\le 2022}).
\]

This rule has no learning-rate search. It may widen after undercoverage, but it is not allowed to narrow after a favorable prior season. The cap at 0.995 prevents an unbounded response to a pathological previous season.

Using the already-published B12 environment-balanced coverage of 0.8487186683, the pre-outcome B13 target level implied by the rule is

\[
p^{(1)}_{2023}=0.9512813317.
\]

This number is a deterministic consequence of the locked rule and the already-observed 2022 diagnostic; it is not selected using 2023.

## Why environment-balanced feedback

G2F environments contain unequal numbers of observable genotype cells. A cell-weighted feedback controller can be dominated by a few dense environments. B13 therefore gives each environment equal weight in the season-level calibration signal.

Cell-level residuals are still used to estimate finite-sample interval half-widths, but the feedback state is environment-balanced.

## Outcome-availability policy — frozen before 2023 reveal

B12 discovered that the official answer key can omit some sealed genotype-environment keys. B13 resolves this prospectively.

The B13 primary evaluation estimand is defined **before Stage A** as:

`OFFICIALLY_OBSERVABLE_SEALED_KEYS`

That is the exact intersection between the immutable sealed prediction keys and the official answer-key membership after reveal.

Rules:

1. key membership, never numerical yield, determines inclusion;
2. a key present in the official answer with a missing/non-numeric outcome causes evaluation failure rather than row deletion;
3. the sealed prediction artifact is never replaced or resealed;
4. observable fractions are reported overall and by environment;
5. the primary estimand is not expanded to unsupported genotypes or unsupported T1 contexts.

Because this policy is declared before 2023 outcome access, an answer-key mismatch is no longer a post-reveal protocol amendment.

## Stage A — 2023 blind seal

Before any 2023 observed yield is accessed:

1. acquire only 2023 predictor-safe inputs;
2. preserve the frozen B5 genomic representation;
3. reconstruct T1 environmental context using information available through 30 DAP only;
4. reproduce the frozen historical encoding before appending 2023;
5. compute the frozen point prediction;
6. compute both C0 and C1 interval half-widths from residual information available through 2022;
7. write both interval candidates into one canonical prediction artifact;
8. hash the artifact with SHA-256;
9. record the deterministic C1 target level and all calibration-source years;
10. set `observed_2023_outcomes_accessed = false` and `post_result_tuning_permitted = false`.

The Stage-A state is:

`B13_2023_TWO_COMPETITOR_ARTIFACT_SEALED`

## Stage B — 2023 reveal

Stage B must verify the exact Stage-A SHA-256 before reading the official 2023 answer.

After reveal, no point prediction, interval width, calibration level, residual window, genomic representation, support threshold, or cohort rule may change.

## Primary admission test

The primary target is the 90% interval.

For each competitor, B13 reports:

- empirical coverage;
- environment-balanced coverage;
- environment-cluster bootstrap 95% interval;
- mean interval width;
- mean 90% interval score;
- overall and environment-level coverage dispersion.

A competitor passes the calibration criterion only if:

1. absolute empirical coverage gap from 90% is at most 3 percentage points; and
2. the environment-cluster 95% interval contains 90%.

The adaptive competitor C1 is promoted over C0 only if it passes the calibration criterion **and** its mean 90% interval score is no worse than C0.

This efficiency condition prevents B13 from declaring success merely by making intervals very wide.

The 90% interval score for lower/upper bounds \(L,U\) and outcome \(Y\) is

\[
S_{0.10}(L,U;Y)
=(U-L)+\frac{2}{0.10}(L-Y)\mathbf 1\{Y<L\}
+\frac{2}{0.10}(Y-U)\mathbf 1\{Y>U\}.
\]

## Locked decision states

Possible B13 decisions are:

- `B13_ADAPTIVE_DRIFT_GUARD_PROMOTED`
- `B13_ADAPTIVE_CALIBRATION_PASS_BUT_INEFFICIENT`
- `B13_BOTH_INTERVAL_RULES_PASS_KEEP_FROZEN_B11`
- `B13_BOTH_INTERVAL_RULES_FAIL`
- `B13_PRIMARY_EVALUATION_ABORTED_DATA_INTEGRITY`

Tie policy: if both rules pass calibration and C1 does not strictly improve mean interval score, retain C0. Complexity receives no free promotion.

## Hostile audit

B13 must be interpreted against, not confused with, existing online conformal methods.

At minimum the discussion must compare its assumptions and update granularity with:

- Gibbs & Candès Adaptive Conformal Inference;
- Zaffran et al. AgACI;
- strongly adaptive online conformal prediction;
- conformal PID control;
- online conformal prediction via online optimization;
- formal nonstationary coverage/backtesting tests.

B13 should not make a broad methodological novelty claim unless a later theorem-level analysis establishes one.

## What B13 can establish

A successful B13 would show that a simple, predeclared, environment-cluster-aware season feedback rule can repair part of the calibration transport failure discovered in B12 on a genuinely later season without changing the point predictor.

## What B13 cannot establish

B13 cannot establish universal calibration, universal genotype portability, a useful abstention rule, superiority to every online conformal method, or a new T2 result.

## Next implementation lock

Implementation must first unit-test the B13 mathematical primitives and protocol invariants before any 2023 outcome acquisition is added.
