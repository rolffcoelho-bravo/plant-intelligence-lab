# Case Study B5 — Continuous-Environment Transfer Data Lock

## Motivation

The original wheat benchmark deliberately exposed a deployment boundary: categorical mega-environment identifiers support prediction within represented environments but do not provide a physical representation for a genuinely unseen environment. Step B5 addresses that limitation at the data level before any new modeling is attempted.

The environmental-transfer extension therefore uses a separate public multi-environment maize resource with observed genomic markers, yield phenotypes, and continuous environmental covariates.

The locked source is the curated Genomes-to-Fields dataset distributed through Figshare:

- DOI: `10.6084/m9.figshare.22776806`
- public archive: `curated_data.zip`
- required matrices: `PHENO.csv`, `GENO.csv`, `ECOV.csv`

The repository downloads the public archive at execution time, extracts the three required matrices, verifies their intersections, records cryptographic provenance, and publishes only compact validation evidence.

## Executed data audit

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

B5 then introduces the missing object:

\[
\mathbf E_{continuous}
\]

so that environmental similarity can be represented quantitatively rather than inferred from an arbitrary category label.

The intended next model class is therefore based on genomic and environmental relationships such as

\[
K_G,
\qquad
K_E,
\qquad
K_{G\times E}=K_G\odot K_E,
\]

with every transformation estimated from the relevant training partition.

No B5 prediction-performance claim is made at the data-lock stage.

## Validation manifests locked before modeling

### Environment cold-start

The 136 environments are assigned once to five deterministic environment folds using seed `20260812`.

For each outer fold, complete year-location environments are held out. Their phenotype outcomes are unavailable to training, but their continuous environmental vectors remain available as deployment-time descriptors.

This is the primary environmental-transfer question:

\[
E_{test}\cap E_{train}=\varnothing,
\qquad
\mathbf e_{test}\;\text{observed}.
\]

### Genotype cold-start

The 4,372 genotypes are independently assigned to five deterministic genotype folds. This allows a separate assessment of unseen-genotype transfer.

### Strict crossed G×E cold-start

The environment and genotype manifests define 25 crossed scenarios:

\[
5\;\text{environment folds}\times5\;\text{genotype folds}=25.
\]

Each scenario simultaneously holds out one genotype fold and one environment fold. These scenarios are explicitly marked `strict_GxE_transfer`.

The hardest deployment question therefore becomes

\[
G_{test}\cap G_{train}=\varnothing,
\qquad
E_{test}\cap E_{train}=\varnothing,
\qquad
\mathbf e_{test}\;\text{observed}.
\]

This is qualitatively different from the earlier wheat CV-GE stress test because the unseen environment now has a measurable continuous representation.

## Environmental-covariate audit

All 202 environmental columns resolved as numeric, nonconstant covariates with observations for all 136 environments. The audit is stored in:

`reports/results/case_study_b5_environment_covariate_audit.csv`

The repository does not yet assign causal biological meaning to individual covariates. They are treated as measured environmental descriptors until modeling and interpretation establish otherwise.

## Reproducibility

Implementation:

`src/plant_intelligence/data/maize_environment_transfer.py`

Tests:

`tests/test_case_study_b5_data_lock.py`

Workflow:

`.github/workflows/case-study-b5-data-lock.yml`

Published evidence:

- `reports/results/case_study_b5_data_lock_summary.csv`
- `reports/results/case_study_b5_environment_covariate_audit.csv`
- `reports/results/case_study_b5_environment_transfer_folds.csv`
- `reports/results/case_study_b5_genotype_transfer_folds.csv`
- `reports/results/case_study_b5_gxe_transfer_scenarios.csv`

The workflow downloads the archive from Figshare at execution time. Raw data remain outside Git; only compact audit and split manifests are committed.

## Admission boundary for the next stage

Step B5 is considered complete because the public source is reproducibly accessible, all three modalities intersect completely at their corresponding genotype/environment level, continuous environmental covariates are present without missingness in the locked environment matrix, and the environment/genotype cold-start manifests were fixed before predictive modeling.

The next stage must preserve these manifests. It may not redefine folds after observing model performance.
