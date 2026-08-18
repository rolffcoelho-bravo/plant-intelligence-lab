# Case Study B17-T1 — Architecture-Contraction Novelty Test

## Status

B17-T1 is the hostile kill test opened by B17. It asks whether the frozen deployed `G+E_T1` operator yields a genuinely new forecast-time certificate of within-environment response contraction.

It does not.

Machine decision:

`B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_REJECTED_TERMINATE_B17`

B17-T2 is forbidden. No model modification is promoted.

## Outcome-closed evidence boundary

The only empirical prediction object used in B17-T1 is the immutable **B14B pre-outcome sealed prediction artifact**:

`reports/results/case_study_b14b_2024_sealed_predictions.csv`

B17-T1 does not use the B14C observed-yield cohort. It does not acquire another season, generate a new prediction, refit or rescale the model, alter intervals/support, change the B5 genomic representation, alter `T1_30DAP`, reopen T2, or reseal anything.

The original B17-T1 protocol lock remains unchanged. A later numerical amendment changes only the implementation-level reproduction tolerance after the first real-seal execution exposed that the initial tolerance ignored float32 arithmetic. It does not change the scientific hypothesis, novelty decision, model, data boundary, hyperparameters, or terminal routing.

## Exact frozen operator in real arithmetic

The frozen predictor is additive ridge on standardized low-rank genomic and environmental features. For genotype `g` and environment `e`, after the already-frozen feature maps and training standardization,

\[
\widehat y(g,e)
=\widehat b_0
+z_G(g)^\top\widehat\beta_G
+z_E(e)^\top\widehat\beta_E.
\]

There is no `G×E` product block in the deployed `G+E_T1` specification.

For two genotypes `i` and `j` in the same environment,

\[
\widehat\Delta_{ij}(e)
=\widehat y(g_i,e)-\widehat y(g_j,e)
=[z_G(g_i)-z_G(g_j)]^\top\widehat\beta_G.
\]

The environmental main-effect block cancels. In exact real arithmetic,

\[
\widehat\Delta_{ij}(e)=\widehat\Delta_{ij}(e')
\]

for every pair of environments in which the same two genotypes are present.

Equivalently, with the within-environment centering matrix

\[
C_e=I-\frac{1}{n_e}\mathbf 1\mathbf 1^\top,
\]

we have

\[
C_e\widehat y_e=C_e Z_{G,e}\widehat\beta_G.
\]

If two environments contain the same genotype set in the same order, their centered prediction vectors are identical in exact arithmetic. If genotype sets differ, differences in predicted within-environment spread can arise from genotype composition, but not from environment-specific modulation of genotype effects.

This is scientifically important for diagnosing B16. It is not a new theorem: it is the elementary representational consequence of using an additive model without a `G×E` interaction.

## Frozen implementation and float32 arithmetic

The exact algebra above is a statement about the mathematical model. The repository implementation is finite precision.

The frozen B5/B14B path constructs genomic and environmental feature maps in `float32`, stacks cell features in `float32`, and then sends that standardized design to ridge prediction. Therefore an empirical reproduction check on the serialized B14B predictions cannot be judged solely by the decimal serialization precision of the final CSV.

This distinction was not correctly encoded in the first B17-T1 CI implementation.

## Preserved first execution failure

The first dedicated B17-T1 workflow execution, run **`32145134703`**, passed the unit tests and outcome-boundary guards but failed at the seal-only operator audit:

`AssertionError: B17-T1 sealed predictions violate the exact additive contrast restriction beyond serialization tolerance.`

The original audit used an absolute tolerance of `1e-8`, chosen to cover the final 12-significant-digit CSV serialization. That check was too strict for the actual frozen float32 computational path.

The failure is preserved. The repository does not overwrite it, relabel it as a pass, or silently enlarge the original threshold.

## Diagnostic probes

Two temporary diagnostic-only CI probes were used to determine the source and scale of the discrepancy. They accessed only the B14B sealed prediction artifact and no target outcomes.

Across all **171** unordered pairs of the 19 target environments:

- minimum common genotypes: **15**;
- maximum common genotypes: **53**;
- total shared unordered genotype-pair comparisons: **72,059**;
- maximum absolute pairwise-contrast deviation: **`1.9074399997265346e-06`**;
- maximum absolute centered-prediction deviation: **`1.1921049978269593e-06`**;
- maximum standard deviation of the environment offset across shared genotypes: **`5.090156109497395e-07`**.

The second probe established the numerical scale:

- maximum difference between the sealed decimal prediction and its nearest `float32` representation: **`4.970779343693721e-11`**;
- minimum float32 ULP across the sealed prediction scale: **`4.76837158203125e-07`**;
- median float32 ULP: **`9.5367431640625e-07`**;
- maximum float32 ULP: **`9.5367431640625e-07`**;
- maximum pairwise-contrast deviation divided by the global maximum ULP: **`2.0000958051532507`**.

The discrepancy is therefore at approximately two float32 ULPs, while final CSV decimal serialization contributes only about `5e-11` at this scale.

## Post-execution numerical amendment

The repository records this explicitly in:

`reports/results/case_study_b17_t1_numerical_amendment.json`

The amendment is labeled:

`POST_EXECUTION_NUMERICAL_AMENDMENT_NO_SCIENTIFIC_DECISION_CHANGE`

It leaves the original protocol lock unchanged and records the failed run and both diagnostic probes.

The replacement implementation-level check is not fitted to the observed maximum. A pairwise contrast-invariance residual is the four-prediction identity

\[
[\widehat y(i,e_a)-\widehat y(j,e_a)]
-[\widehat y(i,e_b)-\widehat y(j,e_b)].
\]

The audit therefore grants a fixed arithmetic budget of **one float32 ULP per participating stored prediction**, or four local ULPs in total, plus the unchanged `1e-8` CSV serialization allowance:

\[
B_{ab}=4\,\max_{g\in G_{ab}}\operatorname{ULP}_{32}(\widehat y_{g,a},\widehat y_{g,b})+10^{-8}.
\]

This four-term ULP budget is derived from the arithmetic identity, not from the observed `1.90744e-06` maximum. The amendment explicitly records `replacement_policy_selected_from_observed_maximum=false`.

The repository retains two separate facts:

1. **the original CSV-only `1e-8` check is false**;
2. **the sealed predictions are tested separately for consistency with the frozen float32 implementation under the fixed four-term ULP budget**.

No biological conclusion or novelty claim depends on converting the first failure into a numerical pass.

## Distinguishing two contraction mechanisms

B17-T1 separates two phenomena that should not be conflated.

### A. Structural contrast invariance

In exact arithmetic, the additive architecture has zero capacity to change a genotype pair's predicted contrast with environment. This is independent of the ridge penalty. The finite-precision implementation should reproduce that identity only up to its arithmetic error budget.

### B. Ridge spectral attenuation

Let `Z` be the centered standardized training design and write its SVD as

\[
Z=U\Sigma V^\top.
\]

For ridge penalty `alpha`, the training fitted-value smoother is

\[
H_\alpha
=Z(Z^\top Z+\alpha I)^{-1}Z^\top
=U\,\mathrm{diag}\left(
\frac{\sigma_k^2}{\sigma_k^2+\alpha}
\right)U^\top.
\]

Thus every nonzero spectral mode is attenuated by the familiar ridge factor

\[
0<\frac{\sigma_k^2}{\sigma_k^2+\alpha}<1.
\]

For the frozen `alpha=10`, a mode with `sigma^2=10` has fitted-value filter exactly `1/2`.

That is standard ridge/KRR spectral filtering, not a new architecture-contraction certificate.

## Hostile prior-art equivalence

The candidate collapses into existing objects in every direction.

### 1. Genotype-difference precision and reliability are established

Schmidt, Hartung, Bennewitz and Piepho (2019), *Heritability in Plant Breeding on a Genotype-Difference Basis*, Genetics, DOI `10.1534/genetics.119.302134`, derives prediction-error variance and reliability/heritable precision directly for pairwise genotype differences, including BLUP settings and multi-environment trials.

Therefore a certificate framed as precision or reliability of genotype contrasts is occupied.

### 2. Outcome-free design-time contrast reliability is established in genomic selection

Rincent et al. (2012), *Maximizing the Reliability of Genomic Selection by Optimizing the Calibration Set of Reference Individuals: Comparison of Methods in Two Diverse Groups of Maize Inbreds*, Genetics, DOI `10.1534/genetics.112.141473`, computes PEV for arbitrary contrasts and generalized coefficients of determination as expected contrast reliability and uses those quantities prospectively to optimize genomic-selection calibration sets in maize.

Therefore an outcome-free design-dependent contrast reliability certificate is not an open novelty space.

### 3. Spectral attenuation is standard ridge/KRR theory

Tomasini, Sclocchi and Wyart (2022), *Failure and success of the spectral bias prediction for Laplace Kernel Ridge Regression: the case of low-dimensional data*, ICML/PMLR 162, analyzes KRR generalization through kernel eigenspectra and spectral bias.

The frozen ridge factor `sigma^2/(sigma^2+alpha)` is substantially more elementary than that literature.

### 4. Computable KRR prediction-error bounds are active prior art

Ni and Huo (2026), *Upper Confidence Bounds for the Prediction Error of Kernel Ridge Regression via Gaussian Refitting*, arXiv:2607.28846, provides computable confidence bounds for KRR prediction error under stated noise assumptions. A generic forecast-time ridge/kernel uncertainty certificate therefore enters an already-developed area.

## Identification boundary

The one object not absorbed by a standard smoother quantity is contraction relative to the **unseen true environment-specific biological response**.

That quantity is not distribution-free point identified from the forecast-time state. B17 already established this with a finite witness: the same prediction vector and the same pre-outcome information can be paired with different future target-response amplitudes.

Additional assumptions could make a model-based quantity identifiable. Once a mixed-model covariance structure is imposed, however, PEV/reliability/CD theory already supplies natural contrast-level objects.

## Scientific interpretation

B17-T1 yields a useful diagnosis even though it yields no new method.

The severe 2024 under-dispersion found in B16 cannot be interpreted as a single scalar shrinkage defect. The frozen system combines two distinct limitations:

1. **representational:** the additive environmental main effect cannot modulate genotype contrasts across environments in exact arithmetic;
2. **regularization:** ridge attenuates fitted spectral modes in the standard way.

The first can suppress true G×E response variation if such variation exists; the second can further compress modeled genomic variation. Neither mechanism establishes how much unseen target variation should have been recovered prospectively without additional assumptions.

The float32 finding is a numerical implementation detail, not a third biological mechanism. Its magnitude is around machine-resolution scale and does not create meaningful environment-specific genotype modulation.

A post-hoc amplitude multiplier would therefore be scientifically inadequate. It cannot repair missing environment-specific genotype modulation and would use revealed outcomes to compensate for an architectural restriction that should instead be tested prospectively with an interaction-capable architecture under a new predeclared experiment.

## Terminal decision

B17-T1 fails the novelty requirement on all admissible routes:

- additive contrast invariance: exact in real arithmetic and useful diagnostically, but elementary no-interaction theory;
- ridge contraction: standard spectral filtering;
- contrast reliability: PEV/CD/entry-difference reliability prior art;
- kernel geometry uncertainty: established leverage/KRR error-bound territory;
- contraction relative to unseen truth: not point identified without assumptions.

Therefore:

**`B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_REJECTED_TERMINATE_B17`**

No B17-T2 is permitted. No response-amplitude correction, G×E retrofit, ridge retuning, or new model is introduced inside B17.

A future interaction-capable architecture, if scientifically justified, must be opened as a separate predeclared research branch with a new hypothesis, prospective evaluation design, and hostile novelty audit. It must not be inserted into B17 as a repair to the revealed 2024 result.
