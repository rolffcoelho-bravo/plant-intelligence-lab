# Case Study B17-T1 — Architecture-Contraction Novelty Test

## Status

B17-T1 is the predeclared hostile kill test opened by B17. It asks whether the frozen deployed `G+E_T1` operator yields a genuinely new forecast-time certificate of within-environment response contraction.

It does not.

Machine decision:

`B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_REJECTED_TERMINATE_B17`

B17-T2 is forbidden. No model modification is promoted.

## Outcome-closed evidence boundary

The only empirical object used in B17-T1 is the immutable **B14B pre-outcome sealed prediction artifact**:

`reports/results/case_study_b14b_2024_sealed_predictions.csv`

B17-T1 does not use the B14C observed-yield cohort. It does not acquire another season, generate a new prediction, refit or rescale the model, alter intervals/support, change the B5 genomic representation, alter `T1_30DAP`, reopen T2, or reseal anything.

## Exact frozen operator

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

The entire environmental main-effect block cancels. Consequently,

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

If two environments contain the same genotype set in the same order, their centered prediction vectors are identical. If genotype sets differ, differences in predicted within-environment spread can arise from genotype composition, but **not from environment-specific modulation of genotype effects**.

This is scientifically important for diagnosing B16. It is not a new theorem: it is the elementary representational consequence of using an additive model without a `G×E` interaction.

## Distinguishing two contraction mechanisms

B17-T1 separates two phenomena that should not be conflated.

### A. Structural contrast invariance

The additive architecture has zero capacity to change a genotype pair's predicted contrast with environment. This is independent of the ridge penalty.

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

## Empirical seal-only invariance audit

B17-T1 does not need observed yields to test the exact structural property. For any two 2024 target environments, take the genotypes common to both and calculate

\[
d_g=\widehat y(g,e_a)-\widehat y(g,e_b).
\]

Under additive `G+E`, `d_g` must be constant across shared genotypes. Therefore

\[
(d_i-d_j)=0
\]

for every shared genotype pair, which is equivalent to invariance of their predicted within-environment contrasts.

The repository audit uses only the serialized B14B predictions and allows `1e-8` numerical tolerance because the seal is stored to 12 significant digits.

This empirical audit is a reproduction check of the algebra, not evidence for a new biological claim.

## Hostile prior-art equivalence

The candidate collapses into existing objects in every direction.

### 1. Genotype-difference precision and reliability are established

Schmidt, Hartung, Bennewitz and Piepho (2019), *Heritability in Plant Breeding on a Genotype-Difference Basis*, Genetics, DOI `10.1534/genetics.119.302134`, derives prediction-error variance and reliability/heritable precision directly for pairwise genotype differences, including BLUP settings and multi-environment trials.

Therefore a certificate framed as “precision/reliability of genotype contrasts” is occupied.

### 2. Outcome-free design-time contrast reliability is established in genomic selection

Rincent et al. (2012), *Maximizing the Reliability of Genomic Selection by Optimizing the Calibration Set of Reference Individuals: Comparison of Methods in Two Diverse Groups of Maize Inbreds*, Genetics, DOI `10.1534/genetics.112.141473`, computes PEV for arbitrary contrasts and generalized coefficients of determination as expected contrast reliability, and uses those quantities prospectively to optimize genomic-selection calibration sets in maize.

Therefore an outcome-free design-dependent contrast reliability certificate is not an open novelty space.

### 3. Spectral attenuation is standard ridge/KRR theory

Tomasini, Sclocchi and Wyart (2022), *Failure and success of the spectral bias prediction for Laplace Kernel Ridge Regression: the case of low-dimensional data*, ICML/PMLR 162, analyzes KRR generalization through kernel eigenspectra and spectral bias.

The frozen ridge factor `sigma^2/(sigma^2+alpha)` is substantially more elementary than that literature.

### 4. Computable KRR prediction-error bounds are active prior art

Ni and Huo (2026), *Upper Confidence Bounds for the Prediction Error of Kernel Ridge Regression via Gaussian Refitting*, arXiv:2607.28846, provides computable confidence bounds for KRR prediction error under stated noise assumptions. This is additional evidence that a generic “forecast-time ridge/kernel uncertainty certificate” would enter an already-developed area.

## Identification boundary

The one object not absorbed by a standard smoother quantity is the contraction of the prediction relative to the **unseen true environment-specific biological response**.

But that quantity is not distribution-free point identified from the forecast-time state. B17 already established this with a finite witness: the same prediction vector and the same pre-outcome information can be paired with different future target-response amplitudes.

Additional assumptions could make a model-based quantity identifiable. Once a mixed-model covariance structure is imposed, however, PEV/reliability/CD theory already supplies the natural contrast-level objects.

## Scientific interpretation

B17-T1 yields a useful diagnosis, even though it yields no new method.

The severe 2024 under-dispersion found in B16 cannot be interpreted as a single scalar shrinkage defect. The frozen architecture has two separate limitations:

1. **representational:** the additive environmental main effect cannot modulate genotype contrasts across environments at all;
2. **regularization:** ridge attenuates fitted spectral modes in the standard way.

The first can suppress true G×E response variation if such variation exists; the second can further compress modeled genomic variation. Neither mechanism establishes how much of the unseen target variation should have been recovered prospectively without additional assumptions.

This also explains why a post-hoc amplitude multiplier would be scientifically inadequate. It cannot repair missing environment-specific genotype modulation and would use revealed outcomes to compensate for an architectural restriction that should instead be tested prospectively with an interaction-capable architecture under a new predeclared experiment.

## Terminal decision

B17-T1 fails the novelty requirement on all admissible routes:

- additive contrast invariance: exact and useful, but elementary/no-interaction prior art;
- ridge contraction: standard spectral filtering;
- contrast reliability: PEV/CD/entry-difference reliability prior art;
- kernel geometry uncertainty: established leverage/KRR error-bound territory;
- contraction relative to unseen truth: not point identified without assumptions.

Therefore:

**`B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_REJECTED_TERMINATE_B17`**

No B17-T2 is permitted. No response-amplitude correction, G×E retrofit, ridge retuning, or new model is introduced inside B17.

A future interaction-capable architecture, if scientifically justified, must be opened as a separate predeclared research branch with a new hypothesis, prospective evaluation design, and hostile novelty audit. It must not be smuggled into B17 as a repair to the 2024 result.
