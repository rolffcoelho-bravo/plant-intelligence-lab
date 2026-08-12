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

Under CV-G, adding the G×E kernel to G+E reduces RMSE by 0.065948 and MAE by 0.056700. A 2,000-replicate genotype-cluster bootstrap gives a 95% interval of [-0.081171, -0.052093] for the RMSE delta and [-0.069917, -0.044313] for the MAE delta.

Under CV2, the corresponding RMSE reduction is 0.070383 and the MAE reduction is 0.057018. The genotype-cluster bootstrap intervals are [-0.097549, -0.043946] for RMSE and [-0.079862, -0.034943] for MAE.

Because the delta is defined as candidate minus reference, negative values favor the G×E model. None of the four G×E bootstrap intervals cross zero in the two primary validation regimes.

By contrast, adding categorical environment means to G alone does not improve the primary predictions. Under CV-G it is slightly worse, and under CV2 the paired uncertainty interval crosses zero. The useful environmental information in this benchmark is therefore not captured by a simple additive environment offset; it appears through environment-dependent genomic response.

## Environment-specific behavior

The interaction benefit is not uniform across environments. Under CV-G, the G+E+G×E model achieves RMSE values of 0.873, 0.882, 0.928, and 0.896 in ME1–ME4 respectively. The largest qualitative correction occurs in ME1: the G-only model has RMSE 1.035 and negative R² (-0.074), whereas the G×E model reduces RMSE to 0.873 and produces positive R² (0.237).

This is consistent with the earlier data audit, where ME1 had weak or negative phenotypic correlations with the other mega-environments. The result supports environment-dependent response as a predictive feature of this dataset. It does not establish a causal environmental mechanism.

## Stress tests

| Validation | Environment mean RMSE | G RMSE | G+E RMSE | G+E+G×E RMSE |
|---|---:|---:|---:|---:|
| CV-E | 0.999165 | 1.012603 | 1.012603 | **0.974996** |
| CV-GE | **0.998951** | 1.034790 | 1.034790 | 1.002064 |

The stress tests are deliberately difficult. In CV-E, one complete environment is absent from training. In CV-GE, both the test genotype and the test environment are absent from training.

For an unseen categorical environment, the environment-specific interaction kernel has no same-environment training observations from which to transfer an interaction response. A categorical identifier cannot encode how a genuinely new environment relates to the environments that were observed during training. Consequently, CV-E and CV-GE are diagnostics of the present representation boundary, not evidence of universal environmental extrapolation.

ME1 is particularly revealing. In leave-ME1-out CV-E, the G model has RMSE 1.236 and R² -0.531. The G×E model improves that failure to RMSE 1.048, but R² remains negative (-0.100). This is a failure diagnostic, not a success claim.

## Interpretation

The primary result is specific and useful:

\[
\boxed{\text{explicit G×E structure materially improves prediction for represented environments}}
\]

under both unseen-genotype CV-G and sparse multi-environment CV2.

The result does **not** imply that categorical G×E kernels solve environmental extrapolation. The stress tests show the opposite: when the environmental category itself is unseen, performance approaches the global baseline and can deteriorate sharply for a distinct environment such as ME1.

That distinction is central to the Plant Intelligence Lab architecture. Genotype × environment interaction can add genuine predictive value without providing a mechanism for extrapolating to new climates or management systems. True environmental transfer would require informative continuous environmental descriptors and a model that can learn similarity across environments.

## Reproducibility

Implementation:

`src/plant_intelligence/models/wheat_gxe_baseline.py`

Tests:

`tests/test_case_study_b_models.py`

Workflow:

`.github/workflows/case-study-b-modeling.yml`

Validated outputs:

- `reports/results/case_study_b_model_summary.csv`
- `reports/results/case_study_b_model_scenario_metrics.csv`
- `reports/results/case_study_b_model_environment_metrics.csv`
- `reports/results/case_study_b_model_predictions.csv`
- `reports/results/case_study_b_gxe_bootstrap.csv`
- `reports/results/case_study_b_genomic_kernel_audit.csv`
- `reports/figures/case_study_b_gxe_ablation.png`

The dedicated workflow passed all ten Case Study B data-lock and modeling tests, executed all locked validation regimes, verified every compact output, and published the evidence to the repository.