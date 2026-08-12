# Data

Plant Intelligence Lab uses public biological datasets to support reproducible genomic prediction, phenotype forecasting, uncertainty-aware modelling, and experimental decision support.

Large raw datasets are not committed unless their size, licence, and redistribution terms make that appropriate. The preferred pattern is reproducible acquisition from documented public sources, with provenance and checksums recorded when data are retrieved.

## Case Study A — In-Vitro Regeneration Intelligence

The first empirical case study uses public *Arabidopsis thaliana* resources that connect genetic variation with shoot-regeneration phenotypes.

### AraPheno Study 80

**Genetic dissection of shoot regeneration from root explants in Arabidopsis (Lardon et al., 2020)**

- Study DOI: `10.21958/study:80`
- Original article DOI: `10.1038/s42003-020-01274-9`
- Study design: 170 natural *Arabidopsis thaliana* accessions subjected to two shoot-regeneration protocol variants
- Public source: AraPheno REST API and phenotype pages

The focal regenerated-shoot endpoints are:

| Endpoint | AraPheno phenotype ID |
|---|---:|
| shoots 15d protocol a | 1267 |
| shoots 15d protocol b | 1274 |
| shoots 21d protocol a | 1281 |
| shoots 21d protocol b | 1288 |

These endpoints support the early biological forecasting comparison

$$
G + P + X_{15d} \rightarrow \widehat{Y}_{21d}
$$

against the genomic-treatment baseline

$$
G + P \rightarrow \widehat{Y}_{21d}.
$$

The first reproducible analysis is implemented in [`notebooks/01_data_discovery.ipynb`](../notebooks/01_data_discovery.ipynb).

### 1001 Genomes

The genomic layer is based on the public 1001 Genomes resource for *Arabidopsis thaliana*. The 2016 major phase reports 1,135 genomes and provides public genomic resources, including variant data and accession-level tools.

The modelling population is defined only after phenotype accessions are intersected with compatible genomic accessions:

$$
\mathcal{A}_{\mathrm{model}}
=
\mathcal{A}_{\mathrm{phenotype}}
\cap
\mathcal{A}_{\mathrm{genomic}}.
$$

The genomic intersection, relatedness structure, marker dimensionality, and genotype-aware validation design belong to `02_genomic_structure.ipynb`.

## Case Study B — Wheat Genotype × Environment Forecasting

Case Study B is now locked to the open Dryad dataset:

> Lopez-Cruz, Marco; de los Campos, Gustavo. (2025). *Data for: Multi-trait/environment sparse genomic prediction using the SFSI R-package*. Dryad. DOI: `10.5061/dryad.vx0k6dk3p`.

The locked public subset contains **3,731 CIMMYT wheat lines**, **9,045 filtered SNP markers**, and adjusted grain-yield records in four managed environments: `B2I`, `B5I`, `MEL`, and `LHT`.

The Case Study B target is:

$$
G + E + G\times E \rightarrow Y_{yield}.
$$

Primary validation uses whole-genotype holdout (**CV-G / CV1**) and sparse multi-environment masking (**CV2**). Leave-one-environment-out (**CV-E**) and strict genotype-plus-environment cold start (**CV-GE**) are retained as diagnostic stress tests because only four environments are available and the source does not contain a rich continuous weather/soil descriptor vector.

The complete source lock, environment definitions, limitations, and split design are documented in [`docs/case_study_b_data_lock.md`](../docs/case_study_b_data_lock.md). Reproducible acquisition and audit are implemented in `src/plant_intelligence/data/wheat_gxe.py`.

## Directory convention

```text
data/
├── raw/         # immutable source files or acquisition outputs
├── interim/     # validated intermediate representations
└── processed/   # modelling-ready datasets produced by code
```

## Reproducibility

For each source, the repository records or generates where practical:

- source URL or DOI
- retrieval date
- licence or usage terms
- original identifiers
- checksums
- filtering rules
- identifier transformations
- exclusions
- final sample counts

Processed datasets must be reproducible from documented public sources using repository code. Manual undocumented changes to modelling datasets are not part of the workflow.

## Scientific boundary

Public datasets demonstrate methodology and empirical behaviour on the evaluated evidence. They do not establish validated performance on proprietary commercial biological systems.
