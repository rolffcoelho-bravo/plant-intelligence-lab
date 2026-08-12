# Case Study B — Wheat Genotype × Environment Data Lock

## Scientific question

**Can genomic information retain predictive value when wheat lines are evaluated across different target environments, and does explicit genotype × environment structure improve prediction?**

Case Study B extends the repository from the longitudinal regeneration problem in Case Study A to a genuine multi-environment genomic-prediction problem:

\[
G + E + G\times E \rightarrow Y,
\]

where `G` is genomic information, `E` is target-environment context, and `Y` is grain yield.

## Executable public data lock

The reproducible source is the canonical `wheat` dataset distributed with **BGLR** on CRAN. The source documentation identifies the data as historical material from CIMMYT's Global Wheat Program.

The acquisition pipeline locks BGLR version `1.1.4` and downloads the CRAN source package at execution time. Raw package files are not committed to this repository.

### Dataset dimensions

| Component | Locked value |
|---|---:|
| Historical wheat lines | **599** |
| Edited DArT markers | **1,279** |
| Mega-environments | **4** |
| Line × environment phenotype cells | **2,396** |
| Crop | *Triticum aestivum* |
| Target | Standardized average grain yield |

The marker matrix remains high-dimensional at the line level:

\[
p=1{,}279 > n=599.
\]

BGLR documentation describes the four phenotype columns as grain yield in four target sets of environments representing CIMMYT mega-environments. The dataset also contains a pedigree-derived relationship matrix, although the first Case Study B data lock centers on markers and phenotypes.

## Why this source is used for the executable lock

Case Study B requires more than a scientifically attractive dataset: a public repository must also be able to rebuild its evidence automatically without private credentials. The BGLR wheat data satisfy that requirement through a versioned CRAN package while preserving the core multi-environment genomic-prediction problem.

The source provides a canonical breeding dataset, a real crop-yield target, four target environments, and a marker dimension larger than the number of lines. It is therefore appropriate for testing whether G×E structure earns predictive value beyond simpler genomic baselines.

## Environmental information boundary

The four environments are encoded as `ME1`–`ME4`. They represent target sets of environments / major agroclimatic regions in the source documentation, but the distributed dataset does not provide a transferable continuous weather, soil, or management vector for each mega-environment.

This matters for validation. The project can test prediction across observed environment categories and sparse line × environment cells, but it must not claim universal transfer to arbitrary future climates from four categorical environment labels alone.

## Validation design

### CV-G / CV1 — unseen genotypes

Entire genotypes are held out across all four environments:

\[
G_{test}\cap G_{train}=\varnothing.
\]

This tests prediction of new genomic lines in environment categories represented during training.

**Status: primary validation.**

### CV2 — sparse multi-environment testing

Each genotype is observed in three environments and withheld in one, with held-out cells balanced across environments.

This tests whether observations from the same line in other environments improve its missing environment-specific prediction.

**Status: primary validation.**

### CV-E — unseen environment

One complete mega-environment is withheld:

\[
E_{test}\cap E_{train}=\varnothing.
\]

Because no continuous environmental descriptor vector is available, a model based only on categorical environment identity has no strong basis for interpolation into a never-seen category.

**Status: diagnostic stress test, not headline evidence.**

### CV-GE — unseen genotype in unseen environment

Both an entire genotype fold and one environment are excluded from training:

\[
G_{test}\cap G_{train}=\varnothing,
\qquad
E_{test}\cap E_{train}=\varnothing.
\]

This double-cold-start scenario is retained to expose failure rather than manufacture claims of universal environmental transfer.

**Status: diagnostic stress test, not headline evidence.**

## Locked model sequence

The modelling stage should compare increasing information and interaction structure under identical splits:

\[
\text{Environment mean}
\rightarrow
G
\rightarrow
G+E
\rightarrow
G+E+G\times E
\rightarrow
\text{nonlinear G×E model if justified}.
\]

A classical genomic relationship baseline comes before nonlinear ML. Hyperparameters must be selected only inside training data; held-out outcomes cannot be used for model choice.

## What Case Study B can and cannot establish

Case Study B can quantify whether explicit G×E improves held-out prediction, compare whole-genotype and sparse multi-environment prediction, characterize cross-environment phenotype structure, and expose performance degradation under environment cold-start stress tests.

It cannot establish universal prediction in arbitrary future climates or external breeding programs without richer environment descriptors and external validation.

## Reproducible acquisition

The executable lock is implemented in:

`src/plant_intelligence/data/wheat_gxe.py`

Install its small optional reader dependency and execute with:

```bash
python -m pip install -e '.[case-study-b]'
python -m plant_intelligence.data.wheat_gxe --output-root .
```

The pipeline downloads the version-locked CRAN source archive, records its SHA-256 checksum, loads `wheat.Y` and `wheat.X`, validates dimensions, and writes compact audit and split manifests under `reports/results/`.

Raw source and extracted package files remain under ignored `data/raw/` and `data/interim/` paths and are not committed.
