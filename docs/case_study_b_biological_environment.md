# Case Study B7 — Biological Environmental Representation

## Purpose

Step B7 asks whether the continuous environmental representation can become more biologically interpretable without changing the locked Case Study B deployment problem.

The B5 environment folds and genotype folds remain unchanged. The B6-R outer-fold representation choices also remain frozen. B7 does **not** reopen the genomic rank, environmental rank, RBF bandwidth, or ridge search. It changes only which environmental information is allowed to define similarity between environments.

The question is therefore:

\[
\text{Can biologically structured environmental information preserve or improve transfer under the same cold-start tests?}
\]

## Target-proximal environmental-variable audit

The materialized ECOV matrix used by the repository contains **202** nonconstant environmental columns. B7 classifies them before modeling.

Five columns have the `yield_*` prefix. They are crop-model predicted-yield outputs and are treated conservatively as **target-proximal** for the yield-transfer benchmark. They are excluded from every new B7 candidate representation.

The previously published B6-R `all-EC` model is retained as a frozen sensitivity reference so the project can measure whether excluding these five columns materially changes the result. It is not treated as the leakage-safe B7 candidate.

The audit leaves:

\[
202-5=197
\]

non-target-proximal environmental covariates for B7 candidates.

This is a conservative design choice. B7 does not claim that the five crop-model yield outputs are identical to the observed phenotype or that they prove target leakage. It asks the narrower and more useful sensitivity question: **does the transfer result survive when target-proximal environmental outputs are removed?**

Published audit:

- `reports/results/case_study_b7_ecov_leakage_audit.csv`
- `reports/results/case_study_b7_environment_block_summary.csv`

## Biological blocks

The 197 retained covariates are organized in two complementary ways.

### Process blocks

| Process block | Retained covariates |
|---|---:|
| Thermal | **36** |
| Water / soil | **125** |
| Canopy / growth | **36** |

The process labels are deterministic mappings from the source EC names. They are used as interpretable prediction blocks, not as causal pathway assignments.

### Phenology blocks

The nine source phenological intervals are grouped into three broader decision-oriented stages:

- **Vegetative:** germination/emergence through the pre-flowering interval;
- **Reproductive transition:** flowering and early reproductive intervals;
- **Grain fill / maturity:** later reproductive development through maturity/harvest.

After exclusion of the five target-proximal `yield_*` columns, the candidate dimensions are:

| Phenology block | Retained covariates |
|---|---:|
| Vegetative | **66** |
| Reproductive transition | **66** |
| Grain fill / maturity | **65** |

## Modeling design

Every B7 model includes the same genomic representation used by the corresponding frozen B6-R outer fold. Only the environmental representation changes.

The candidates are:

\[
\text{All non-target-proximal ECs},
\]

\[
\text{Thermal},\quad
\text{Water/soil},\quad
\text{Canopy/growth},
\]

\[
\text{Vegetative},\quad
\text{Reproductive transition},\quad
\text{Grain fill/maturity},
\]

plus process- and stage-structured multiple-kernel representations.

For a multiple-kernel candidate, each environmental block receives its own training-only RBF relationship matrix. The block kernels are averaged with equal weight **before** the Nyström eigendecomposition:

\[
K_E^{MK}=\frac{1}{B}\sum_{b=1}^{B}K_E^{(b)}.
\]

The resulting feature map keeps the same frozen environmental rank as the B6-R outer fold. This prevents a multiple-kernel candidate from receiving a dimensionality advantage simply because it contains more biological blocks.

No candidate receives a new outer-fold tuning search.

## Final out-of-sample results

### Unseen environment

| Environmental representation | RMSE | MAE | R² | Correlation |
|---|---:|---:|---:|---:|
| B6-R all-EC sensitivity reference | **2.5693** | 2.0507 | 0.1497 | 0.4002 |
| All non-target-proximal | 2.5772 | 2.0601 | 0.1444 | 0.3952 |
| Thermal | 2.6315 | 2.1166 | 0.1080 | 0.3599 |
| Water / soil | 2.6183 | 2.1018 | 0.1169 | 0.3625 |
| Canopy / growth | 2.6923 | 2.1331 | 0.0663 | 0.3527 |
| Thermal + water multiple kernel | 2.5831 | 2.0689 | 0.1405 | 0.3923 |
| Vegetative | 2.8437 | 2.2946 | -0.0416 | 0.2230 |
| Reproductive transition | **2.5729** | **2.0534** | **0.1473** | **0.4011** |
| Grain fill / maturity | 2.6510 | 2.1283 | 0.0948 | 0.3409 |
| **Process multiple kernel** | **2.5610** | **2.0416** | **0.1552** | **0.4162** |
| Stage multiple kernel | 2.6002 | 2.0833 | 0.1291 | 0.3820 |

### Unseen genotype + unseen environment

| Environmental representation | RMSE | MAE | R² | Correlation |
|---|---:|---:|---:|---:|
| B6-R all-EC sensitivity reference | **2.5726** | 2.0537 | 0.1475 | 0.3979 |
| All non-target-proximal | 2.5805 | 2.0630 | 0.1423 | 0.3929 |
| Thermal | 2.6351 | 2.1198 | 0.1056 | 0.3575 |
| Water / soil | 2.6215 | 2.1047 | 0.1148 | 0.3602 |
| Canopy / growth | 2.6963 | 2.1368 | 0.0636 | 0.3503 |
| Thermal + water multiple kernel | 2.5870 | 2.0725 | 0.1380 | 0.3897 |
| Vegetative | 2.8465 | 2.2975 | -0.0437 | 0.2206 |
| Reproductive transition | **2.5765** | **2.0567** | **0.1449** | **0.3987** |
| Grain fill / maturity | 2.6547 | 2.1314 | 0.0922 | 0.3383 |
| **Process multiple kernel** | **2.5642** | **2.0445** | **0.1531** | **0.4141** |
| Stage multiple kernel | 2.6037 | 2.0863 | 0.1268 | 0.3796 |

## What survives the target-proximal exclusion

Removing the five `yield_*` environmental outputs changes RMSE by only about **+0.008** in either deployment regime:

\[
2.5693\rightarrow2.5772
\]

for unseen environments and

\[
2.5726\rightarrow2.5805
\]

for the double cold start.

The paired 2,000-replicate environment-cluster bootstrap gives intervals that cross zero:

- unseen environment: **[-0.0023, 0.0202]**;
- double cold start: **[-0.0025, 0.0188]**.

The defensible conclusion is therefore that the B6-R point performance is **not materially dependent on those five target-proximal outputs in this sensitivity test**. This is not a claim that every remaining environmental covariate is prospectively available or causally valid.

## Stage-ablation result

The strongest stage-level finding is not a tiny champion-model difference. It is the contrast between early and reproductive environmental information.

The **66-variable reproductive-transition block** nearly reproduces the all-EC reference:

\[
RMSE_{CV-E}=2.5729,
\qquad
RMSE_{CV-GE}=2.5765.
\]

Its environment-cluster intervals versus the all-EC reference comfortably cross zero, so B7 does not make a formal equivalence or noninferiority claim.

By contrast, the vegetative-only representation is clearly inadequate:

\[
RMSE_{CV-E}=2.8437,
\qquad
RMSE_{CV-GE}=2.8465.
\]

Relative to the all-EC reference, the paired environment-cluster RMSE difference is approximately **+0.274** in both regimes, with 95% intervals entirely above zero:

- unseen environment: **[0.1234, 0.4276]**;
- double cold start: **[0.1143, 0.4327]**.

Thus, under the locked representation, **vegetative-stage environmental information alone is insufficient for this yield-transfer task**.

## Multiple-kernel result

The equal-weight process multiple kernel produces the best pooled point estimate:

\[
RMSE_{CV-E}=2.5610,
\qquad
RMSE_{CV-GE}=2.5642.
\]

However, its gain is small and not robust across environment clusters. Relative to the all-EC sensitivity reference, the RMSE differences are only about **-0.0083** and **-0.0085**, with 95% intervals crossing zero. Relative to the 197-variable non-target-proximal representation, the improvements are about **-0.0162** and **-0.0163**, again with intervals crossing zero.

The project therefore treats process structuring as an **interpretability and representation result**, not as a demonstrated accuracy breakthrough.

The equal-weight stage multiple kernel does not improve the benchmark. Biological partitioning is not automatically beneficial merely because the partition has a plausible interpretation.

## Scientific interpretation

B7 supports three bounded conclusions.

1. The continuous-environment result survives conservative removal of the five crop-model predicted-yield outputs with only a very small change in pooled error.
2. The timing of environmental information matters: reproductive-transition information is much more useful for this yield-transfer task than vegetative information alone.
3. Process-aware environmental kernels can match or slightly improve the pooled point estimate, but that advantage is not robust enough to claim a general transfer improvement.

These are predictive statements. The process and stage blocks do not establish causal environmental mechanisms.

## Deployment-time boundary

B7 also exposes the next limitation. A variable can be scientifically informative in a retrospective year-location representation while still being unavailable at the time a real breeding or crop-management decision must be made.

The current environmental resource includes crop-model quantities accumulated over phenological intervals. Therefore a reproductive-stage representation should not be presented as a pre-season forecast without a separate data-availability audit.

The next deployment-oriented experiment must distinguish environmental variables by **when they are knowable** and ensure that a forecast at time \(t\) uses no information from later stages.

## Reproducibility

Implementation:

`src/plant_intelligence/models/maize_environment_process_kernels.py`

Tests:

`tests/test_case_study_b7_process_kernels.py`

Workflow:

`.github/workflows/case-study-b7-process-kernels.yml`

Published evidence:

- `reports/results/case_study_b7_process_kernel_summary.csv`
- `reports/results/case_study_b7_process_kernel_bootstrap.csv`
- `reports/results/case_study_b7_environment_metrics.csv`
- `reports/results/case_study_b7_ecov_leakage_audit.csv`
- `reports/results/case_study_b7_environment_block_summary.csv`
- `reports/results/case_study_b7_design_audit.csv`
- `reports/figures/case_study_b7_process_kernel_ablation.png`

The B5 outer folds remain controlling throughout B7.
