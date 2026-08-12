# Case Study B5–B6 — Continuous-Environment Transfer

## Motivation

The original wheat benchmark deliberately exposed a deployment boundary: categorical mega-environment identifiers support prediction within represented environments but do not provide a physical representation for a genuinely unseen environment. Steps B5–B6 address that limitation by introducing a public multi-environment maize resource with observed genomic markers, yield phenotypes, and continuous environmental covariates, then testing whether those covariates create out-of-environment predictive value.

The locked source is the curated Genomes-to-Fields dataset distributed through Figshare:

- DOI: `10.6084/m9.figshare.22776806`
- public archive: `curated_data.zip`
- required matrices: `PHENO.csv`, `GENO.csv`, `ECOV.csv`

The repository downloads the public archive at execution time, extracts the three required matrices, verifies their intersections, records cryptographic provenance, and publishes only compact validation evidence.

## Step B5 — Executed data audit

| Component | Verified result |
|---|---:|
| Phenotype records | **78,686** |
| Phenotyped genotypes | **4,372** |
| Genotyped hybrids | **4,372** |
| SNP markers | **98,026** |
| Observed year-location environments | **136** |
| Environments with continuous covariates | **136** |
| Environmental covariates | **202** |
| Nonconstant environmental covariates | **202** |
| Phenotype–environment overlap | **136 / 136** |
| Phenotype–genomic overlap | **4,372 / 4,372** |
| Nonmissing yield observations | **78,686** |
| Environmental-covariate missing fraction | **0.0** |
| Study years represented | **2014–2021** |

This is a materially different transfer substrate from the four-category wheat benchmark. It supplies an explicit environmental vector for each observed environment rather than only an environment label.

## Why this extension remains part of Case Study B

The purpose is not to replace the wheat benchmark. The two components answer sequential questions.

The wheat benchmark establishes that explicit genomic G×E structure adds out-of-sample value when environmental regimes are represented during training, and it shows that categorical environment IDs fail under true cold-environment transfer.

B5 introduces the missing object

\[
\mathbf E_{continuous}
\]

so that environmental similarity can be represented quantitatively rather than inferred from an arbitrary category label.

B6 then evaluates low-rank genomic and environmental relationship representations:

\[
K_G,
\qquad
K_E,
\qquad
K_{G\times E}=K_G\odot K_E.
\]

## Validation manifests locked before modeling

### Environment cold-start

The 136 environments were assigned once to five deterministic environment folds using seed `20260812` before B6 was implemented.

For each outer fold, complete year-location environments are held out. Their phenotype outcomes are unavailable to training, but their continuous environmental vectors remain available as deployment-time descriptors:

\[
E_{test}\cap E_{train}=\varnothing,
\qquad
\mathbf e_{test}\;\text{observed}.
\]

### Genotype cold-start

The 4,372 genotypes were independently assigned to five deterministic genotype folds.

### Strict crossed G×E cold-start

The environment and genotype manifests define 25 crossed scenarios:

\[
5\;\text{environment folds}\times5\;\text{genotype folds}=25.
\]

Each scenario simultaneously holds out one genotype fold and one environment fold:

\[
G_{test}\cap G_{train}=\varnothing,
\qquad
E_{test}\cap E_{train}=\varnothing,
\qquad
\mathbf e_{test}\;\text{observed}.
\]

This is qualitatively different from the earlier wheat CV-GE stress test because the unseen environment now has a measurable continuous representation.

## Step B6 — Kernel construction and scalable representation

The 98,026-marker genomic matrix is too large for a dense cell-level dual kernel over tens of thousands of genotype-environment observations. B6 therefore uses a reproducible low-rank approximation rather than silently subsampling the biological problem.

For genomics, marker values are centered and scaled using the relevant outer training genotype partition, compressed with a deterministic CountSketch, and then mapped through training-partition PCA. The resulting feature map defines a low-rank approximation to a linear genomic kernel.

For environment, all 202 continuous covariates are standardized using the relevant training environments. An exact RBF relationship matrix is formed among training environments, and a Nyström feature map is obtained from its leading eigenvectors. Across the five primary environment folds the 16 retained environmental kernel dimensions account for approximately **72.6%–73.4%** of the training-kernel trace, while the 20 genomic dimensions explain approximately **60.6%–60.8%** of the CountSketch variance.

The interaction map is the row-wise tensor product of the genomic and environmental maps. Its inner product satisfies

\[
\langle \phi_G(g_i)\otimes\phi_E(e_i),\phi_G(g_j)\otimes\phi_E(e_j)\rangle
=
K_G(g_i,g_j)K_E(e_i,e_j),
\]

so it is a low-rank feature representation of the product kernel.

Phenotype plot records are aggregated to genotype-environment means before prediction, leaving **52,167 observed genotype-environment cells**. Replicate plots are therefore not treated as independent deployment cases.

The first B6 information ablation deliberately uses the same fixed ridge penalty for all non-mean models. This stage asks whether added information helps under a common regularization rule; it is not an optimized hyperparameter leaderboard.

## Step B6 — Primary unseen-environment results

The primary five-fold environment cold start evaluates environments absent from phenotype training while retaining their measured 202-dimensional environmental descriptors.

| Model | RMSE | MAE | R² | Correlation |
|---|---:|---:|---:|---:|
| Mean | 2.8105 | 2.2412 | -0.0175 | -0.1694 |
| G | 2.6876 | 2.1524 | 0.0696 | 0.2722 |
| E | 2.6935 | 2.1581 | 0.0655 | 0.2940 |
| **G+E** | **2.6495** | 2.1232 | **0.0958** | 0.3497 |
| G+E+G×E | 2.6812 | **2.1160** | 0.0740 | **0.3859** |

Relative to the mean-only benchmark, `G+E` reduces pooled RMSE by approximately **5.73%**. Relative to genomic information alone, the point estimate improves RMSE by approximately **1.42%**.

However, the pre-specified 2,000-replicate paired environment-cluster bootstrap does **not** establish that the `G+E` improvement over `G` is stable across environments. The observed RMSE difference is **-0.0381**, with a 95% bootstrap interval of **[-0.1844, 0.1132]** and an improvement frequency of **0.6495**. The interval crosses zero.

The explicit product-kernel interaction also does not improve pooled RMSE relative to additive `G+E`: its RMSE difference is **+0.0317**, with a 95% bootstrap interval of **[-0.1215, 0.1947]**. It slightly lowers MAE and raises pooled correlation, but those point-estimate differences are not sufficient to claim a robust interaction advantage under cold-environment transfer.

## Step B6 — Strict unseen-genotype + unseen-environment results

The 25 double-cold-start scenarios produce one pooled out-of-fold prediction for every modeled genotype-environment cell while excluding both the cell's genotype fold and environment fold from training.

| Model | RMSE | MAE | R² | Correlation |
|---|---:|---:|---:|---:|
| Mean | 2.8109 | 2.2414 | -0.0178 | -0.1705 |
| G | 2.6917 | 2.1558 | 0.0668 | 0.2681 |
| E | 2.6939 | 2.1586 | 0.0652 | 0.2936 |
| **G+E** | **2.6527** | 2.1261 | **0.0936** | 0.3474 |
| G+E+G×E | 2.6825 | **2.1167** | 0.0731 | **0.3845** |

The point-estimate pattern is almost unchanged under the harder double cold start. `G+E` reduces RMSE by approximately **5.63%** relative to the mean benchmark and by approximately **1.45%** relative to `G` alone.

Again, environment-cluster uncertainty is decisive. The `G+E` minus `G` RMSE difference is **-0.0390**, with a 95% interval of **[-0.1997, 0.1175]**. The product-kernel interaction is worse than additive `G+E` in pooled RMSE by **+0.0298**, with interval **[-0.1177, 0.1881]**.

## What B6 establishes

B6 provides three useful results.

First, physically characterized unseen environments are no longer forced into an `UNSUPPORTED_ENVIRONMENT` state. A model can now produce a genuine transfer forecast using deployment-time environmental descriptors.

Second, continuous environmental information contributes a favorable pooled point estimate when combined with genomics, but the incremental RMSE advantage over genomic information alone is **small and not robust across environment clusters** under the current representation.

Third, the simple multiplicative genomic × environmental kernel does not earn a pooled RMSE advantage under true environmental transfer. The project therefore does not claim that adding a mathematically valid G×E kernel automatically solves environmental generalization.

This is the intended scientific distinction:

\[
\boxed{\text{environment representation enables the transfer problem}}
\]

but

\[
\boxed{\text{the current representation does not yet establish a robust transfer gain}}.
\]

## Heterogeneity across environment folds

The pooled average hides substantial fold heterogeneity. For example, in primary environment fold 0 the full product-kernel model improves RMSE to **2.5869** versus **2.7077** for `G+E`, while in fold 1 it deteriorates to **3.0972** versus **2.8978**. Other folds also change ordering. This heterogeneity is why the environment-cluster bootstrap is treated as more important than a small pooled point-estimate advantage.

The next scientific problem is therefore not to add arbitrary model families. It is to understand **which environmental representations transfer and why some held-out environment groups benefit while others fail**.

## Environmental-covariate audit

All 202 environmental columns resolve as numeric, nonconstant covariates with observations for all 136 environments. They are treated as measured environmental descriptors rather than causal variables. B6 does not infer that any individual covariate causes yield variation.

## Reproducibility

Data lock implementation:

`src/plant_intelligence/data/maize_environment_transfer.py`

B6 modeling implementation:

`src/plant_intelligence/models/maize_environment_transfer.py`

Tests:

- `tests/test_case_study_b5_data_lock.py`
- `tests/test_case_study_b6_environment_transfer.py`

Workflows:

- `.github/workflows/case-study-b5-data-lock.yml`
- `.github/workflows/case-study-b6-environment-transfer.yml`

Published B5 evidence:

- `reports/results/case_study_b5_data_lock_summary.csv`
- `reports/results/case_study_b5_environment_covariate_audit.csv`
- `reports/results/case_study_b5_environment_transfer_folds.csv`
- `reports/results/case_study_b5_genotype_transfer_folds.csv`
- `reports/results/case_study_b5_gxe_transfer_scenarios.csv`

Published B6 evidence:

- `reports/results/case_study_b6_transfer_summary.csv`
- `reports/results/case_study_b6_transfer_fold_metrics.csv`
- `reports/results/case_study_b6_transfer_bootstrap.csv`
- `reports/results/case_study_b6_feature_audit.csv`
- `reports/figures/case_study_b6_environment_transfer.png`

The B6 figure places the model legend horizontally below the plot to preserve a clear scientific comparison without covering the data region.

## Current admission boundary

The B5 data lock and B6 first transfer benchmark are complete. The frozen folds remain controlling. The next stage may refine the **environmental representation and regularization** but may not redefine the outer validation splits or suppress difficult environment folds.
