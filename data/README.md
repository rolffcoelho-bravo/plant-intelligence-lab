# Data

This repository uses public biological datasets for reproducible demonstration of genomic prediction, phenotype forecasting, uncertainty-aware modelling, and experiment selection.

Large raw datasets should not be committed directly unless their licences and size make that appropriate. Prefer reproducible acquisition scripts and documented provenance.

## Planned public sources

### Case Study A — In-vitro Regeneration Intelligence

Primary target resources:

- AraPheno phenotype data for *Arabidopsis thaliana*
- 1001 Genomes genomic resources for compatible accessions

The first task is to verify:

- exact phenotype identifiers and definitions
- accession identifiers
- genotype/phenotype intersection
- protocol or treatment variables
- sample size after matching
- genomic dimensionality
- missingness
- population structure
- licensing and redistribution conditions

No modelling result should be published until these checks are complete.

### Case Study B — Genotype × Environment Forecasting

Planned public resource:

- multi-environment wheat data available through the `sommer` ecosystem and associated source material

The objective is to demonstrate environment-aware genomic prediction and biological generalization under changing conditions.

## Directory convention

```text
data/
├── raw/         # immutable source files or acquisition outputs
├── interim/     # validated intermediate representations
└── processed/   # modelling-ready datasets produced by code
```

## Reproducibility rule

Every processed dataset must be reproducible from documented public sources using repository code. Manual undocumented edits to modelling datasets are not acceptable.

## Data integrity

For each source, the repository should record:

- source URL or DOI
- retrieval date
- licence or usage terms
- original file names
- checksums when practical
- filtering rules
- identifier transformations
- exclusions
- final sample counts

## Important boundary

Public datasets demonstrate methodology. They do not establish performance on proprietary commercial biological systems.
