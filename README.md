# Plant Intelligence Lab

## Genomic Prediction, Phenotype Forecasting & AI-Assisted Biological Decision Systems

> **Can we predict a plant phenotype from genomic information, environmental variables and early biological observations, while quantifying uncertainty?**

Plant Intelligence Lab is an open computational biotechnology project focused on applying quantitative genetics, machine learning, statistical modelling, and probabilistic forecasting to plant-science problems with direct research and industrial relevance.

The repository uses real public biological data to evaluate predictive models under realistic high-dimensional conditions, with particular attention to biological generalization, uncertainty, reproducibility, and decision support.

## Public data foundation

The project uses established public plant-genomics resources, including:

- **1001 Genomes Project** — genomic variation across more than 1,100 *Arabidopsis thaliana* accessions.
- **AraPheno** — public phenotype datasets linked to *Arabidopsis* accessions.
- **Shoot-regeneration data** — a public study covering 170 natural accessions tested under two regeneration protocol variants, with regenerated shoots and related *in vitro* traits measured.

These resources provide a real setting for studying genomic prediction and phenotype forecasting without relying on synthetic biological results.

## Core capabilities

Plant Intelligence Lab develops and evaluates methods for:

- genomic prediction
- phenotype forecasting
- high-dimensional modelling where `p >> n`
- quantitative-genetics baselines
- machine-learning prediction
- genotype × environment analysis
- genotype × treatment analysis
- early biological outcome forecasting
- uncertainty quantification
- out-of-distribution detection
- model abstention when evidence is insufficient
- explainable predictions
- experimental decision support
- scientific AI interfaces grounded in validated outputs

## Scientific focus

A central statistical challenge in genomic prediction is that the number of molecular features can be far larger than the number of observed plants:

\[
p \gg n
\]

The repository therefore evaluates models under validation schemes designed to measure generalization rather than simply maximize in-sample fit.

Classical quantitative-genetics approaches provide scientific baselines, while regularized and nonlinear machine-learning models are evaluated for additional predictive value.

Performance assessment focuses on RMSE, MAE, predictive correlation, out-of-sample reliability, and uncertainty estimates where appropriate.

## Public applications

### In-Vitro Regeneration Intelligence

Uses public *Arabidopsis thaliana* genomic and phenotype resources to evaluate regeneration-related prediction across accessions and treatment conditions.

### Genotype × Environment Forecasting

Uses public multi-environment plant data to evaluate whether genomic models remain informative when biological performance changes across environmental conditions.

### AI-Assisted Experimental Analysis

Extends validated predictive models toward uncertainty-aware experimental prioritization and biological decision support.

## Industrial relevance

The methods demonstrated here are applicable to plant-biotechnology problems involving:

- genomic selection and breeding support
- plant propagation and regeneration analysis
- genotype × environment prediction
- treatment-response modelling
- early biological outcome forecasting
- experimental prioritization
- uncertainty-aware decision systems
- scientific data and AI interfaces

Public datasets are used for reproducibility and benchmarking. Performance claims apply only to the evaluated public datasets and should not be interpreted as validated performance on proprietary industrial processes.

## Scientific principles

1. **Real public data before synthetic demonstrations**
2. **Prediction is not biological causation**
3. **Generalization matters more than in-sample performance**
4. **Genetic leakage must be prevented**
5. **Uncertainty is part of the prediction**
6. **Models should abstain when evidence is insufficient**
7. **GenAI operates over verified scientific outputs**
8. **Results should be reproducible**

## Repository structure

```text
plant-intelligence-lab/
├── README.md
├── CITATION.cff
├── pyproject.toml
├── data/
├── notebooks/
├── src/
│   └── plant_intelligence/
│       ├── data/
│       ├── genetics/
│       ├── models/
│       ├── forecasting/
│       ├── uncertainty/
│       ├── optimization/
│       └── explainability/
├── experiments/
├── reports/
├── app/
├── tests/
└── docs/
```

## PhytoForecast

**Genomic Intelligence for Plant Performance**

PhytoForecast is the forecasting component within Plant Intelligence Lab, combining genomic information, biological observations, environmental context, and uncertainty-aware prediction.

> *An open-source computational biotechnology project exploring how quantitative genetics, machine learning, probabilistic forecasting, and AI-assisted experimental analysis can support plant science and biotechnology.*
