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

The central forecasting problem is:

$$
\widehat{Y}_{t+h}=f\left(G,P,E,X_t\right)
$$

where:

- $\widehat{Y}_{t+h}$ is the predicted biological outcome at future horizon $t+h$;
- $G$ denotes genomic information;
- $P$ denotes protocol or treatment information;
- $E$ denotes environmental information;
- $X_t$ denotes biological observations available up to time $t$.

For the regeneration setting, an early-forecasting specification can be written as:

$$
\widehat{Y}_{21}=f\left(G,P,X_{15}\right)
$$

and compared with a genomic-treatment baseline:

$$
\widehat{Y}_{21}=f\left(G,P\right)
$$

The comparison measures whether early biological observations add predictive information beyond genotype and treatment alone.

## Quantitative-genetics baseline

The first genomic benchmark is **GBLUP: Genomic Best Linear Unbiased Prediction**. It is a standard quantitative-genetics method that uses genome-wide markers to construct a genomic relationship matrix and predict genetic values or biological outcomes from realized genomic similarity.

The name describes the estimator directly:

- **Genomic** — genome-wide marker information is used to quantify genetic relatedness;
- **Best Linear** — under the mixed-model assumptions, the predictor minimizes prediction-error variance within the class of linear unbiased predictors;
- **Unbiased** — the prediction rule does not systematically shift random genetic effects upward or downward under the model;
- **Prediction** — the fitted genetic structure is used to predict outcomes for held-out genotypes.

The model is represented by

$$
\mathbf{y}=\mathbf{X}\boldsymbol{\beta}+\mathbf{Z}\mathbf{u}+\boldsymbol{\varepsilon}
$$

with

$$
\mathbf{u}\sim\mathcal{N}\left(\mathbf{0},\mathbf{K}\sigma_g^2\right),
\qquad
\boldsymbol{\varepsilon}\sim\mathcal{N}\left(\mathbf{0},\mathbf{I}\sigma_e^2\right),
$$

where $\mathbf{K}$ is the genomic relationship matrix, $\sigma_g^2$ is the genomic variance component, and $\sigma_e^2$ is the residual variance component.

In the regeneration case study, GBLUP asks a concrete question: **can genome-wide relatedness predict shoot-regeneration performance for genotypes that were not used to fit the model?** It provides a serious classical reference point against which regularized and nonlinear machine-learning models can be evaluated under the same genotype-aware validation folds.

## High-dimensional genomic modelling

Genomic prediction frequently operates in the regime

$$
p\gg n
$$

where $p$ is the number of genomic markers and $n$ is the number of observed plants or accessions.

This creates a high-dimensional estimation problem in which naive fitting can capture noise rather than biological signal. The repository therefore evaluates models under validation schemes designed to measure generalization to genuinely unseen genotypes.

Candidate approaches include regularized linear models, tree ensembles, gradient boosting, kernel methods, and carefully regularized neural networks.

Performance assessment focuses on quantities such as root mean squared error,

$$
\mathrm{RMSE}=\sqrt{\frac{1}{n}\sum_{i=1}^{n}\left(y_i-\widehat{y}_i\right)^2}
$$

mean absolute error,

$$
\mathrm{MAE}=\frac{1}{n}\sum_{i=1}^{n}\left|y_i-\widehat{y}_i\right|
$$

and predictive correlation,

$$
\rho\left(y,\widehat{y}\right).
$$

## Genotype × Environment forecasting

Plant performance can change when the same genotype is exposed to different environments. A standard decomposition is

$$
Y_{ij}=\mu+G_i+E_j+\left(G\times E\right)_{ij}+\varepsilon_{ij}
$$

where $G_i$ is the genotype effect, $E_j$ is the environment effect, and $(G\times E)_{ij}$ captures their interaction.

A flexible predictive extension is

$$
\widehat{Y}=f\left(G,E,G\times E\right).
$$

The objective is to evaluate whether biological performance can be forecast under environmental change rather than assuming a stable response across conditions.

## Early biological forecasting

Where longitudinal measurements are available, the project evaluates whether earlier biological observations improve forecasts of later outcomes.

A general formulation is

$$
P\left(Y_T\mid G,P,E,X_{0:t}\right)
$$

where $X_{0:t}$ contains the information observed from the beginning of the experiment through time $t$, and $Y_T$ is the later biological outcome of interest.

## Uncertainty-aware prediction

Predictions are accompanied by uncertainty rather than reported as isolated point estimates.

A predictive interval can be represented as

$$
P\left(L_{1-\alpha}(x)\leq Y_{\mathrm{new}}\leq U_{1-\alpha}(x)\right)\approx 1-\alpha
$$

where $L_{1-\alpha}(x)$ and $U_{1-\alpha}(x)$ are the lower and upper predictive bounds for a new observation $x$.

Methods may include conformal prediction, bootstrap-based intervals, Bayesian modelling, or calibrated predictive distributions.

When a new genotype or biological condition lies outside the model's reliable evidence base, the system can abstain rather than return unjustified precision.

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
│
├── README.md
├── LICENSE
├── CITATION.cff
├── pyproject.toml
│
├── data/
│   ├── README.md
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── notebooks/
│   ├── 01_data_discovery.ipynb
│   ├── 02_genomic_structure.ipynb
│   ├── 03_genomic_prediction.ipynb
│   ├── 04_gxe_forecasting.ipynb
│   ├── 05_uncertainty.ipynb
│   └── 06_active_learning.ipynb
│
├── src/
│   └── plant_intelligence/
│       ├── data/
│       ├── genetics/
│       ├── models/
│       ├── forecasting/
│       ├── uncertainty/
│       ├── optimization/
│       └── explainability/
│
├── experiments/
│   ├── baselines/
│   ├── ml/
│   └── genomic/
│
├── reports/
│   ├── figures/
│   ├── model_cards/
│   └── results/
│
├── app/
│   └── dashboard/
│
├── tests/
│
└── docs/
    ├── methodology.md
    ├── biological_context.md
    ├── limitations.md
    └── transferability.md
```

## PhytoForecast

**Genomic Intelligence for Plant Performance**

PhytoForecast is the forecasting component within Plant Intelligence Lab, combining genomic information, biological observations, environmental context, and uncertainty-aware prediction.

> *An open-source computational biotechnology project exploring how quantitative genetics, machine learning, probabilistic forecasting, and AI-assisted experimental analysis can support plant science and biotechnology.*
