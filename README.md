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

## Core prediction framework

The central modelling problem can be written as:

**Future plant phenotype = f(genomic information, treatment, environment, early biological observations) + uncertainty**

In compact mathematical notation:

**Ŷ(t+h) = f(G, P, E, X(t))**

where:

- **Ŷ(t+h)** = predicted biological outcome at a future time
- **G** = genomic information
- **P** = protocol or treatment
- **E** = environmental information
- **X(t)** = biological observations available at the current time

The practical objective is straightforward: use information already available about a plant or accession to estimate a later biological outcome, while also reporting how reliable that estimate is.

For example:

**Genomic profile + regeneration treatment + early growth measurements → predicted regeneration outcome**

The system is therefore designed to produce not only a forecast, but also an estimate of predictive uncertainty and, where appropriate, a warning when the available evidence is insufficient for a reliable prediction.

## Core capabilities

Plant Intelligence Lab develops and evaluates methods for:

- genomic prediction
- phenotype forecasting
- high-dimensional genomic modelling
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

## High-dimensional genomic modelling

Genomic datasets commonly contain far more molecular markers than observed plants. This is usually described as a **p > n problem**, where:

- **p** = number of genomic features or molecular markers
- **n** = number of observed plants or accessions

When **p is much larger than n**, a model can easily fit noise instead of learning biological patterns that generalize to new plants.

Plant Intelligence Lab therefore evaluates models under validation schemes designed to answer a more useful question:

> **Can the model make reliable predictions for genotypes it has not already seen?**

Classical quantitative-genetics approaches provide scientific baselines, while regularized and nonlinear machine-learning models are evaluated for additional predictive value.

Performance assessment focuses on RMSE, MAE, predictive correlation, out-of-sample reliability, and uncertainty estimates where appropriate.

## Genotype × Environment

Plant performance can change when the same genotype is exposed to different environments. Rather than assuming a genotype has one fixed expected performance, the project explicitly studies **genotype × environment interaction**.

Conceptually:

**Observed phenotype = genotype effect + environment effect + genotype-environment interaction + unexplained variation**

The corresponding prediction problem is:

**Predicted phenotype = f(genotype, environment, genotype × environment interaction)**

This allows the project to investigate whether a model trained under one set of biological conditions remains informative when conditions change.

## Early biological forecasting

A second forecasting problem asks whether observations collected early in a biological process can help predict its later outcome.

For example:

**Genomic information + treatment + Day-15 observations → Day-21 regeneration outcome**

This can be compared with:

**Genomic information + treatment → Day-21 regeneration outcome**

The comparison measures whether early biological information provides meaningful additional forecasting value.

Instead of reporting only a single predicted number, the system can estimate a probability or prediction interval around the future outcome.

## Uncertainty-aware prediction

A prediction is more useful when its uncertainty is explicit.

Rather than reporting only:

**Predicted outcome: 8.4**

the system should aim to report information such as:

**Predicted outcome: 8.4 | 90% prediction interval: 6.9–9.8**

The exact uncertainty method depends on the model and empirical setting and may include conformal prediction, bootstrap-based intervals, Bayesian approaches, or calibrated predictive distributions.

When a new genotype or biological condition is too different from the evidence used to train the model, the system can abstain rather than provide unjustified precision:

> **LOW CONFIDENCE — insufficient evidence for reliable prediction**

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
