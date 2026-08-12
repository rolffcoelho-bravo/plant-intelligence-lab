# Case Study B — Classical Multi-Environment Genomic Baseline

## Question

Case Study B asks whether explicit genotype × environment structure improves out-of-sample wheat prediction beyond genomic main effects and categorical environment means.

The locked information ablation is

\[
\text{Environment mean}
\rightarrow G
\rightarrow G+E
\rightarrow G+E+G\times E.
\]

The experiment is evaluated on the pre-registered Case Study B split manifests. CV-G and CV2 are primary evidence. CV-E and CV-GE are diagnostic stress tests because the public BGLR wheat data provide four categorical mega-environments but no transferable continuous weather, soil, or management covariate vector.

## Data

The reproducible BGLR 1.1.4 wheat lock contains 599 CIMMYT wheat lines, 1,279 DArT markers, four mega-environments (ME1–ME4), and 2,396 complete line × environment phenotype cells. All 1,279 markers are nonconstant in the locked matrix and the genomic relationship matrix is normalized to mean diagonal one.

The yield phenotypes in this public benchmark are standardized. Reported RMSE and MAE therefore use the standardized phenotype scale, not physical yield units.

## Classical model

Markers are centered and scaled before building the genomic relationship matrix

\[
K_G = \frac{ZZ^\top}{p},
\]

which is subsequently normalized to mean diagonal one.

For models containing an environment term, environment means are estimated only from the training partition. The interaction model uses the additive kernel

\[
K = K_G + \gamma K_{G\times E},
\]

where

\[
(K_{G\times E})_{ij}
=
(K_G)_{g_i g_j}\,\mathbf{1}(e_i=e_j).
\]

The cell-level kernel is not materialized densely. Structured matrix-vector multiplication and conjugate gradients are used to solve the ridge system. This keeps the computation explicit while avoiding unnecessary cell-level memory growth.

The ridge parameter \(\alpha\), and the interaction-kernel weight \(\gamma\) for the G×E model, are selected only inside each outer training partition using genotype-grouped inner validation. These tuning parameters are predictive regularization parameters; they are not interpreted as biological variance components or heritability estimates.

## Primary results

| Validation | Model | RMSE | MAE | R² | Correlation |
|---|---|---:|---:|---:|---:|
| CV-G | Environment mean | 0.999964 | 0.785605 | -0.001600 | -0.053283 |
| CV-G | G | 0.960027 | 0.749785 | 0.076808 | 0.277943 |
| CV-G | G+E | 0.960848 | 0.750747 | 0.075228 | 0.275325 |
| CV-G | **G+E+G×E** | **0.894899** | **0.694046** | **0.197816** | **0.444846** |
| CV2 | Environment mean | 0.975138 | 0.769053 | -0.001680 | -0.041804 |
| CV2 | G | 0.916560 | 0.710454 | 0.115052 | 0.344225 |
| CV2 | G+E | 0.917310 | 0.710639 | 0.113603 | 0.341617 |
| CV2 | **G+E+G×E** | **0.846926** | **0.653620** | **0.244407** | **0.501070** |

Under CV-G, adding the G×E kernel to G+E reduces RMSE by 0.065948, or about 6.86%, and MAE by 0.056700. A 2,000-replicate genotype-cluster bootstrap gives a 95% interval of [-0.081171, -0.052093] for the RMSE delta and [-0.069917, -0.044313] for the MAE delta.

Under CV2, the corresponding RMSE reduction is 0.070383, or about 7.67%, and the MAE reduction is 0.057018. The genotype-cluster bootstrap intervals are [-0.097549, -0.043946] for RMSE and [-0.079862, -0.034943] for MAE.

Because the delta is defined as candidate minus reference, negative values favor the G×E model. None of the four G×E bootstrap intervals cross zero in the two primary validation regimes. The bootstrap probability of improvement is 1.0 in all four primary G×E comparisons; this is an empirical bootstrap frequency, not a formal p-value.

Adding categorical environment means to G alone does not improve the primary predictions. This must be interpreted in light of the source preprocessing: the BGLR wheat yield phenotypes are standardized by environment, so environment-specific location shifts have already been largely removed. The near-zero incremental value of the additive environment-mean term is therefore expected and should not be generalized into a claim that additive environmental effects are biologically unimportant. The incremental signal in this benchmark is the environment-dependent genomic response captured by the interaction structure.

## Step B2-R — interaction-weight robustness and boundary resolution

The first classical run selected the largest allowed raw interaction weight, \(\gamma=4\), in five of the six primary outer scenarios. That required a robustness check before nonlinear models could be allowed to challenge the classical baseline.

A widened raw grid from \(\gamma=0.25\) through \(128\) improved training-only inner-CV scores, but one primary fold still selected the upper boundary and several selections moved jointly to large \(\gamma\) and large ridge \(\alpha\). The raw parameterization therefore exposed a scale dependence rather than a clean biological optimum: multiplying the interaction kernel and changing the ridge can create nearly equivalent regularization regimes.

To remove that ambiguity, the robustness layer was reparameterized as a bounded normalized kernel mixture

\[
K_{\eta}=(1-\eta)K_G+\eta K_{G\times E},
\qquad 0\leq\eta\leq1,
\]

with an independent ridge parameter \(\lambda\). The full interaction-share domain is therefore represented explicitly: \(\eta=0\) is cross-environment genomic main-effect sharing and \(\eta=1\) is a pure environment-specific genomic kernel. Selecting \(\eta=1\) is a valid endpoint result, not an unresolved search boundary.

The normalized search is resolved. Across the five CV-G folds plus CV2, selected \(\eta\) values range from 0.90 to 1.00, with median 0.9875. Five of six primary scenarios select \(\eta\geq0.95\), and three CV-G folds select the pure interaction endpoint \(\eta=1\). Selected ridge values range from 0.75 to 1.00, with no upper or lower ridge-grid boundary selections.

These values are predictive regularization choices. In particular, \(\eta=0.9875\) must **not** be interpreted as 98.75% of genetic variance being caused by G×E. The result says that, under this standardized benchmark and leakage-aware validation, prediction usually prefers environment-specific genomic covariance over a large shared genomic main component.

### Normalized robustness results

| Validation | Model | RMSE | MAE | R² | Correlation |
|---|---|---:|---:|---:|---:|
| CV-G | G+E normalized reference | 0.960487 | 0.751200 | 0.075921 | 0.277761 |
| CV-G | **Normalized G×E mixture** | **0.890109** | **0.688560** | **0.206380** | **0.456270** |
| CV2 | G+E normalized reference | 0.914113 | 0.705816 | 0.119769 | 0.347033 |
| CV2 | **Normalized G×E mixture** | **0.855236** | **0.656597** | **0.229506** | **0.480383** |

Relative to its normalized G+E reference, the mixture reduces RMSE by 0.070378 under CV-G and 0.058877 under CV2. The 2,000-replicate genotype-cluster bootstrap intervals are [-0.087992, -0.054236] and [-0.094660, -0.024189], respectively. The corresponding MAE intervals are also entirely below zero.

The normalized formulation does not dominate the original pre-registered interaction model in every deployment regime. Its CV-G RMSE is about 0.54% lower than the original 0.894899 result, while its CV2 RMSE is about 0.98% higher than the original 0.846926 result. This sub-1% sensitivity is retained rather than hidden. The central conclusion is therefore robust to the interaction-weight parameterization, while the exact optimum is task-dependent.

### Frozen classical challenger threshold

The classical G×E family is now frozen before nonlinear ML. Future challengers must not be compared only with the easier formulation. The benchmark threshold is the strongest leakage-safe classical result already observed within each primary deployment regime:

| Primary regime | Frozen classical RMSE threshold | Source formulation |
|---|---:|---|
| CV-G | **0.890109** | normalized G×E mixture |
| CV2 | **0.846926** | pre-registered classical G×E |

This threshold is a challenger benchmark, not a replacement of the pre-registered evidence. The original B2 results remain reported as the primary classical information-ablation experiment; B2-R establishes that their G×E conclusion survives a resolved and more interpretable regularization parameterization.

## Environment-specific behavior

The interaction benefit is not uniform across environments. Under CV-G, the original G+E+G×E model achieves RMSE values of 0.873, 0.882, 0.928, and 0.896 in ME1–ME4 respectively. The largest qualitative correction occurs in ME1: the G-only model has RMSE 1.035 and negative R² (-0.074), whereas the G×E model reduces RMSE to 0.873 and produces positive R² (0.237).

This is consistent with the earlier data audit, where ME1 had weak or negative phenotypic correlations with the other mega-environments. The result supports environment-dependent response as a predictive feature of this dataset. It does not establish a causal environmental mechanism.

## Stress tests

| Validation | Environment mean RMSE | G RMSE | G+E RMSE | G+E+G×E RMSE |
|---|---:|---:|---:|---:|
| CV-E | 0.999165 | 1.012603 | 1.012603 | 0.974996 |
| CV-GE | 0.998951 | 1.034790 | 1.034790 | 1.002064 |

The stress tests are deliberately difficult. In CV-E, one complete environment is absent from training. In CV-GE, both the test genotype and the test environment are absent from training.

For an unseen categorical environment, the environment-specific interaction kernel has no same-environment training observations from which to transfer an interaction response. A categorical identifier cannot encode how a genuinely new environment relates to the environments that were observed during training. Consequently, CV-E and CV-GE are diagnostics of the present representation boundary, not evidence of universal environmental extrapolation.

The pooled CV-E G×E row should not be interpreted as successful interaction transfer. For a held-out environment the interaction cross-kernel is unavailable; the fitted coefficients and regularization learned on represented environments can still change the genomic main-effect prediction, but the environment-specific interaction itself cannot transfer to the unseen category.

ME1 is particularly revealing. In leave-ME1-out CV-E, the G model has RMSE 1.236 and R² -0.531. The G×E specification improves that failure to RMSE 1.048, but R² remains negative (-0.100). In strict CV-GE the pooled G×E specification has RMSE 1.002 and R² -0.006, essentially failing to beat the environment-mean baseline. These are failure diagnostics, not success claims.

## Interpretation

The primary result is specific and useful:

\[
\boxed{\text{explicit G×E structure materially improves prediction for represented environments}}
\]

under both unseen-genotype CV-G and sparse multi-environment CV2.

B2-R strengthens that conclusion rather than changing it. Once the raw \(\gamma\)-scale ambiguity is removed, the normalized mixture still favors very strong environment-specific genomic structure and still materially outperforms its genomic-plus-environment reference in both primary regimes.

The result does **not** imply that categorical G×E kernels solve environmental extrapolation. The stress tests show the opposite: when the environmental category itself is unseen, performance approaches the global baseline and can deteriorate sharply for a distinct environment such as ME1.

That distinction is central to the Plant Intelligence Lab architecture. Genotype × environment interaction can add genuine predictive value without providing a mechanism for extrapolating to new climates or management systems. True environmental transfer would require informative continuous environmental descriptors and a model that can learn similarity across environments.

## Reproducibility

Implementations:

- `src/plant_intelligence/models/wheat_gxe_baseline.py`
- `src/plant_intelligence/models/wheat_gxe_robustness.py`
- `src/plant_intelligence/models/wheat_gxe_mixture_robustness.py`

Tests:

- `tests/test_case_study_b_models.py`
- `tests/test_case_study_b_robustness.py`
- `tests/test_case_study_b_mixture_robustness.py`

Workflow:

`.github/workflows/case-study-b-modeling.yml`

Core validated outputs:

- `reports/results/case_study_b_model_summary.csv`
- `reports/results/case_study_b_model_scenario_metrics.csv`
- `reports/results/case_study_b_model_environment_metrics.csv`
- `reports/results/case_study_b_model_predictions.csv`
- `reports/results/case_study_b_gxe_bootstrap.csv`
- `reports/results/case_study_b_genomic_kernel_audit.csv`
- `reports/results/case_study_b_gxe_robustness_audit.csv`
- `reports/results/case_study_b_gxe_robustness_selection.csv`
- `reports/results/case_study_b_gxe_robustness_tuning_profile.csv`
- `reports/results/case_study_b_gxe_mixture_audit.csv`
- `reports/results/case_study_b_gxe_mixture_selection.csv`
- `reports/results/case_study_b_gxe_mixture_profile.csv`
- `reports/results/case_study_b_gxe_mixture_summary.csv`
- `reports/results/case_study_b_gxe_mixture_bootstrap.csv`
- `reports/figures/case_study_b_gxe_ablation.png`
- `reports/figures/case_study_b_gxe_gamma_robustness.png`
- `reports/figures/case_study_b_gxe_mixture_robustness.png`

The dedicated workflow passed **15/15 targeted Case Study B tests**, reproduced the locked classical baseline, executed both robustness stages, verified every compact output, and published the evidence to the repository.