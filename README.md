# Plant Intelligence Lab

## Genomic Prediction, Phenotype Forecasting & AI-Assisted Biological Decision Systems

> **Can we predict a plant phenotype from genomic information, environmental variables and early biological observations, while quantifying uncertainty?**

Plant Intelligence Lab is a public computational plant biotechnology project focused on genomic prediction, phenotype forecasting, uncertainty-aware machine learning, and AI-assisted experimental decision support.

The project uses public plant-genomics resources to develop reproducible methods with direct relevance to research and biotechnology applications. The **1001 Genomes Project** provides genomic variation across more than 1,100 *Arabidopsis thaliana* accessions, while **AraPheno** provides phenotype datasets linked to those accessions. A particularly relevant public study examines **shoot regeneration from root explants** across 170 natural accessions under two protocol variants, with regenerated shoots and related *in vitro* traits measured.

This creates a realistic setting for evaluating how genomic information, treatment conditions, environmental variation, and early biological observations can be integrated into predictive systems.

## Core modelling problem

\[
G + P + E + X_t \rightarrow \widehat{Y}_{t+h}
\]

where:

- `G` = genomic information
- `P` = protocol or treatment
- `E` = environmental information
- `X_t` = observations available at time `t`
- `Y_(t+h)` = future biological outcome

The project is designed around four capabilities:

```text
Genomic & Biological Data
          ↓
Predictive Modelling
          ↓
Uncertainty Quantification
          ↓
Decision Support
```

## Quantitative genetics

A classical quantitative-genetics baseline is established with mixed-model methods such as GBLUP:

\[
y = X\beta + Zu + \epsilon
\]

This provides a scientifically meaningful benchmark before comparison with modern machine-learning approaches.

## High-dimensional machine learning

Genomic prediction is frequently a high-dimensional problem:

\[
p \gg n
\]

The repository evaluates regularized and nonlinear models including Elastic Net, Random Forest, gradient boosting, kernel methods, and carefully regularized neural networks.

Performance is evaluated with RMSE, MAE, R², predictive correlation, and biologically meaningful out-of-sample validation. Particular attention is given to generalization across unseen genotypes and to preventing relatedness leakage between training and test data.

## Genotype × environment forecasting

Biological performance can vary substantially across environmental conditions. The project models this through genotype × environment interactions:

\[
Y_{ij}=\mu+G_i+E_j+(G\times E)_{ij}+\epsilon_{ij}
\]

and machine-learning extensions of the form:

\[
\widehat{Y}=f(G,E,G\times E)
\]

The objective is to forecast biological performance under environmental change rather than assuming stable responses across conditions.

## Early biological forecasting

Where longitudinal measurements are available, the project evaluates whether early observations can improve prediction of later biological outcomes.

```text
Early observation → Updated forecast → Final biological outcome
```

This supports applications where earlier identification of likely outcomes can improve experimental planning, resource allocation, and biological decision-making.

## Uncertainty-aware prediction

Predictions are accompanied by uncertainty estimates rather than reported as isolated point values.

Methods may include:

- bootstrapping
- conformal prediction
- Bayesian modelling
- calibrated prediction intervals
- out-of-distribution detection

When evidence is insufficient, the system can abstain rather than return false precision.

## AI-assisted experimental decision support

Validated predictive models can be extended to rank candidate experiments under limited experimental capacity.

The objective is to identify experiments that offer high expected biological value, high information value, or both.

```text
Prediction → Uncertainty → Experiment Ranking → Decision Support
```

This creates a bridge between predictive modelling and experimental optimization.

## GenAI scientific interface

Generative AI is used as an interface to validated data and model outputs rather than as a replacement for scientific modelling.

```text
Scientist ↔ GenAI ↔ Models + Database
```

Natural-language queries can be grounded in reproducible model results, uncertainty estimates, and traceable data sources.

## Public case studies

### Case Study A — In-Vitro Regeneration Intelligence

Uses public *Arabidopsis thaliana* genomic and phenotype resources to evaluate regeneration-related prediction across accessions and protocol variants.

Key questions:

- Can regeneration outcomes be predicted for unseen accessions?
- Does protocol information improve prediction?
- Are genotype × protocol interactions informative?
- How reliable are the resulting predictions?

### Case Study B — Genotype × Environment Forecasting

Uses public multi-environment plant data to evaluate genomic prediction under changing environmental conditions.

### Case Study C — AI-Guided Experiment Selection

Extends validated predictive models into experimental prioritization under constrained testing capacity.

## Industrial relevance

The methods demonstrated here are applicable to plant biotechnology problems involving genomic selection, phenotype prediction, treatment-response modelling, environmental adaptation, experimental prioritization, and uncertainty-aware biological decision support.

Potential application areas include:

- genomic selection and breeding support
- plant propagation and regeneration analysis
- genotype × environment prediction
- early outcome forecasting
- experimental prioritization
- uncertainty-aware decision systems
- scientific data and AI interfaces

Public datasets are used for reproducibility and benchmarking. Performance claims in this repository apply only to the evaluated public datasets and should not be interpreted as validated performance on proprietary industrial processes.

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

## Project identity

### PhytoForecast
**Genomic Intelligence for Plant Performance**

PhytoForecast is the forecasting component within Plant Intelligence Lab, combining genomic information, biological observations, environmental context, and uncertainty-aware prediction.

> *An open-source computational biotechnology project exploring how quantitative genetics, machine learning, probabilistic forecasting, and AI-assisted experimental analysis can support plant science and biotechnology.*
