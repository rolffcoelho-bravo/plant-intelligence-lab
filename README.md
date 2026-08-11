# Plant Intelligence Lab

## Genomic Prediction, Phenotype Forecasting & AI-Assisted Biological Decision Systems

**Can biological performance be predicted before an experiment is complete?**

Plant Intelligence Lab is a public computational plant biotechnology project exploring how quantitative genetics, machine learning, probabilistic forecasting, uncertainty quantification, and AI-assisted experimental design can support biological decision-making.

The repository is built around a concrete forecasting problem:

```text
GENETICS + ENVIRONMENT + PROTOCOL + EARLY OBSERVATIONS
                         |
                         v
               PLANT INTELLIGENCE ENGINE
                         |
                         v
      PHENOTYPE FORECAST | UNCERTAINTY | RISK
                         |
                         v
              RECOMMENDED EXPERIMENT
```

The core modelling target is:

\[
G + P + E + X_t \rightarrow \widehat{Y}_{t+h}
\]

where `G` is genomic information, `P` is protocol or treatment, `E` is environment, `X_t` is information observed up to time `t`, and `Y_(t+h)` is a future biological outcome.

This project prioritizes **real public biological data**, realistic biological generalization, high-dimensional modelling where `p >> n`, uncertainty-aware prediction, and direct decision value.

## What this repository demonstrates

- quantitative genetics and genomic prediction
- high-dimensional machine learning
- genotype-aware validation
- genotype × environment forecasting
- genotype × protocol interactions
- early biological outcome prediction
- uncertainty quantification and calibrated prediction intervals
- out-of-distribution detection and model abstention
- active learning and Bayesian experiment selection
- explainability
- GenAI as an interface to validated scientific outputs
- reproducible scientific computing

The objective is not to maximize an attractive in-sample score. The objective is to test whether models generalize to genuinely unseen biological conditions and whether their outputs are reliable enough to support real scientific and industrial decisions.

## Case studies

### A. In-vitro Regeneration Intelligence

The first case study investigates whether genomic variation and protocol information can predict regeneration-related phenotypes for unseen *Arabidopsis thaliana* accessions using public phenotype and genomic resources.

Key questions:

- Can regeneration outcomes be predicted for unseen accessions?
- Does protocol information materially improve prediction?
- Are genotype × protocol interactions identifiable?
- How much uncertainty surrounds each prediction?
- When should the model abstain?

### B. Genotype × Environment Forecasting

The second case study studies whether biological performance can be forecast across changing environmental conditions using public multi-environment plant data.

The target is not merely yield prediction. The emphasis is on biological generalization under environment shift.

### C. AI-Guided Experiment Selection

Validated predictive models are extended into experimental decision support. Under limited experimental capacity, the system estimates which genotype, protocol, or environment combination should be tested next to maximize expected information or improvement.

## Scientific principles

**Prediction is not biological causation.** Predictive associations are not presented as causal mechanisms without appropriate experimental evidence.

**Generalization matters more than in-sample performance.** Validation is designed around the intended biological deployment problem.

**Genetic leakage must be prevented.** Related samples must not make the test set unrealistically easy.

**Uncertainty is part of the prediction.** Point estimates alone are insufficient for decision support.

**Abstention is a feature.** When evidence is insufficient or an observation lies outside the training distribution, the system should return low confidence rather than false precision.

**GenAI does not generate scientific truth.** Language models operate over verified data, model outputs, and traceable evidence.

## Repository structure

```text
plant-intelligence-lab/
├── README.md
├── CITATION.cff
├── pyproject.toml
├── data/
│   ├── README.md
│   ├── raw/
│   ├── interim/
│   └── processed/
├── notebooks/
│   ├── 01_data_discovery.ipynb
│   ├── 02_genomic_structure.ipynb
│   ├── 03_genomic_prediction.ipynb
│   ├── 04_gxe_forecasting.ipynb
│   ├── 05_uncertainty.ipynb
│   └── 06_active_learning.ipynb
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
│   ├── baselines/
│   ├── ml/
│   └── genomic/
├── reports/
│   ├── figures/
│   ├── model_cards/
│   └── results/
├── app/
│   └── dashboard/
├── tests/
└── docs/
    ├── methodology.md
    ├── biological_context.md
    ├── limitations.md
    └── industrial_transferability.md
```

## Development sequence

1. **Biological and data feasibility** — verify phenotype definitions, genomic availability, accession matching, sample size, dimensionality, missingness, population structure, licensing, and prediction-task feasibility.
2. **Genomic prediction benchmark** — classical quantitative-genetics baselines, GBLUP, regularized high-dimensional models, selected ML methods, genotype-aware validation.
3. **Biological forecasting** — genotype × environment, genotype × protocol, longitudinal information, distribution shift, uncertainty, out-of-distribution detection, abstention.
4. **Decision intelligence** — active learning, Bayesian optimization, experiment prioritization, information value, interpretable recommendations.
5. **GenAI interface** — natural-language access to validated model outputs, scientific retrieval, experiment-history interrogation, and uncertainty-aware explanations.

## Industrial relevance

The project is designed as a transferable computational architecture for plant biotechnology. Public datasets are used to demonstrate methods; no claim is made that a public-data proof of concept automatically transfers to a proprietary industrial process.

The intended value chain is:

```text
Biological Data
    -> Quantitative Genetics
    -> Machine Learning
    -> Forecasting
    -> Uncertainty
    -> Experiment Optimization
    -> Decision Intelligence
```

A detailed discussion is available in [`docs/industrial_transferability.md`](docs/industrial_transferability.md).

## Status

The project is currently beginning with biological and data feasibility for the first public case study. The next visible deliverables will be the validated data map, reproducible preprocessing pipeline, and first genomic-prediction benchmark.
