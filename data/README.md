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

## Case Study B — Genotype × Environment Forecasting

A later public case study will use multi-environment plant data to evaluate genomic prediction under environmental heterogeneity and distribution shift.

The objective is to test whether predictive information survives changes in biological context, rather than simply maximizing performance under random train-test splits.

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
