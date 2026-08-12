# Case Study B — Wheat Genotype × Environment Data Lock

## Scientific question

**Can genomic information retain predictive value when wheat lines are evaluated across materially different environmental and management conditions?**

Case Study B extends the repository from the longitudinal regeneration problem in Case Study A to a true multi-environment genomic-prediction problem:

\[
G + E + G\times E \rightarrow Y,
\]

where `G` is genomic information, `E` is environmental or management context, and `Y` is grain yield.

## Locked public dataset

The primary data source is:

> Lopez-Cruz, Marco; de los Campos, Gustavo. (2025). *Data for: Multi-trait/environment sparse genomic prediction using the SFSI R-package*. Dryad. DOI: `10.5061/dryad.vx0k6dk3p`.

Public landing page:

`https://datadryad.org/dataset/doi:10.5061/dryad.vx0k6dk3p`

Dryad publishes research datasets under a CC0 instrument, allowing reproducible reuse. Large source files are acquired at execution time and are not committed to this repository.

### Dataset dimensions

The published data contain:

| Component | Locked value |
|---|---:|
| Wheat lines | **3,731** |
| Filtered SNP markers | **9,045** |
| Managed environments | **4** |
| Complete line × environment yield cells | **14,924** |
| Crop | *Triticum aestivum* |
| Target | Adjusted grain yield, ton/ha |

The marker matrix is therefore high-dimensional at the line level:

\[
p=9{,}045 > n=3{,}731.
\]

The full source described by the data authors contains 29,484 lines evaluated under six environmental conditions. The locked public subset contains the 3,731 lines with complete records in four conditions and their 9,045 filtered SNPs.

## Environmental conditions

The four environments are not arbitrary labels. They correspond to materially different field-management or stress conditions used by CIMMYT in Ciudad Obregon, Mexico:

| Environment | Source description | Interpretable context |
|---|---|---|
| `B2I` | bed planting and two irrigations | water-limited / drought context |
| `B5I` | bed planting and five irrigations | optimal irrigation context |
| `MEL` | melgas flat planting and five irrigations | optimal irrigation with different planting system |
| `LHT` | late heat | heat-stress context |

Only descriptors explicitly supported by the source are encoded. For example, the public source does not provide a consistently specified irrigation count or planting system for `LHT`; those fields remain missing rather than being inferred.

## Why this dataset is locked

This dataset materially strengthens the repository relative to Case Study A because it provides a larger genomic population, a real crop-breeding target, complete multi-environment phenotypes, and environments spanning water, planting-system, and heat differences.

It is also directly reproducible from an open repository without requiring the Plant Intelligence Lab repository to redistribute proprietary or access-restricted source data.

## Validation design

Random line-level splitting is not sufficient for the deployment questions of interest. Four complementary validation regimes are therefore defined.

### CV-G / CV1 — unseen genotypes

Entire genotypes are held out across all four environments.

\[
G_{test}\cap G_{train}=\varnothing.
\]

This tests the core breeding problem: predicting new genomic lines in environments represented during training.

**Status: primary validation.**

### CV2 — sparse multi-environment testing

Each genotype is observed in three environments and withheld in one. The held-out environment is balanced across genotypes.

This tests whether information from the same line in related environments improves prediction of its missing environment-specific response.

**Status: primary validation.**

### CV-E — unseen environment

One complete environment is withheld.

\[
E_{test}\cap E_{train}=\varnothing.
\]

This is a scientifically harder question, but the locked dataset contains only four managed environments and does not provide a rich continuous weather/soil covariate vector for each environment. Environment identity alone cannot support a strong claim of generalization to genuinely new environmental conditions.

**Status: diagnostic stress test, not headline evidence.**

### CV-GE — unseen genotype in unseen environment

Both an entire genotype fold and one environment are excluded from training. Test observations are the Cartesian intersection of those withheld genotypes and the withheld environment.

\[
G_{test}\cap G_{train}=\varnothing,
\qquad
E_{test}\cap E_{train}=\varnothing.
\]

This is the strict double-cold-start problem. It is retained because it is operationally important, but interpretation must respect the same environmental-descriptor limitation as CV-E.

**Status: diagnostic stress test, not headline evidence.**

## Model sequence

The modelling stage should make complexity earn its place under the same splits. The locked comparison is:

\[
\text{Environment mean}
\rightarrow
G
\rightarrow
G+E
\rightarrow
G+E+G\times E
\rightarrow
\text{nonlinear genomic/environment interaction}.
\]

The first benchmark should include a classical genomic relationship model before nonlinear ML. Model selection must not use held-out validation outcomes.

## What Case Study B can and cannot establish

Case Study B can test genomic prediction across multiple managed environments, quantify whether explicit G×E improves held-out prediction, compare performance under unseen-genotype and sparse-environment scenarios, and expose failure under environmental distribution shift.

It cannot by itself establish universal prediction in arbitrary future climates. With only four managed conditions and incomplete continuous environmental descriptors, CV-E and CV-GE are intentionally treated as stress tests rather than proof of general unseen-environment transfer.

## Reproducible acquisition

The executable data lock is implemented in:

`src/plant_intelligence/data/wheat_gxe.py`

Running

```bash
python -m plant_intelligence.data.wheat_gxe --output-root .
```

downloads the source archive, records its SHA-256 checksum, validates the expected dimensions and identifiers, and writes compact audit and split manifests under `reports/results/`.

The raw archive and extracted matrices remain under ignored `data/raw/` and `data/interim/` paths and are not committed.
