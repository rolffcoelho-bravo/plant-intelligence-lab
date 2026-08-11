# Plant Intelligence Lab

## Genomic Prediction, Phenotype Forecasting & AI-Assisted Biological Decision Systems

> **Can we predict a plant phenotype from genomic information, environmental variables and early biological observations, while quantifying uncertainty?**

That gives the project genetics + machine learning + statistics + forecasting + optimization in one coherent system.

Public plant-genomics resources make this feasible without inventing synthetic data. The **1001 Genomes Project** contains genomic variation for more than 1,100 *Arabidopsis thaliana* accessions, while **AraPheno** provides public phenotype datasets linked to those accessions. Of particular interest, AraPheno contains a study of **shoot regeneration from root explants**, involving 170 natural accessions tested under two protocol variants and measuring regenerated shoots and other *in vitro* traits.

This makes the first case study substantially more relevant to computational plant biotechnology than a generic yield-prediction exercise.

The project begins with the biological forecasting problem:

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

where:

- `G` = genomic information
- `P` = protocol or treatment
- `E` = environmental information
- `X_t` = observations available at time `t`
- `Y_(t+h)` = future biological outcome

The first public demonstration does not require every component simultaneously. Development begins with genomic, phenotype, and protocol information and progressively extends the architecture to environmental and longitudinal observations.

The guiding scientific question is not simply whether an algorithm can fit historical data. The objective is to determine whether biological outcomes can be predicted for genuinely unseen biological conditions while representing uncertainty honestly.

## Model 1 — Classical Quantitative Genetics

The project does not begin with neural networks.

A serious quantitative-genetics baseline is established first:

\[
y = X\beta + Zu + \epsilon
\]

using genomic relationship matrices and methods such as GBLUP.

This provides a scientifically meaningful benchmark before comparison with modern machine-learning approaches.

## Model 2 — High-Dimensional Machine Learning

A central statistical challenge is:

\[
p \gg n
\]

There may be thousands or potentially millions of genomic markers but comparatively few biological samples. This high-dimensional structure is treated as a core methodological feature rather than ignored.

Candidate models include:

**Elastic Net → Random Forest → XGBoost/LightGBM → kernel methods → carefully regularized neural networks**

The project is not an algorithmic horse race for the most attractive `R²`. Evaluation includes RMSE, MAE, R², predictive correlation and, critically, **generalization to unseen genotypes**.

Naive random train/test splitting can create misleading performance estimates because genetically related plants may leak information between training and test sets. Validation is therefore genotype-aware and designed around the biological generalization question.

## Genotype × Environment Forecasting

The second module asks:

> **A genotype performed well under environment A. What happens in environment B?**

A classical representation is:

\[
Y_{ij}=\mu+G_i+E_j+(G\times E)_{ij}+\epsilon_{ij}
\]

Machine learning extends this into:

\[
\widehat{Y}=f(G,E,G\times E)
\]

Biological performance is not necessarily stable across environmental conditions. The scientific question becomes:

> **Can we forecast biological performance when the environment changes?**

This module provides a natural setting for studying nonstationarity, distribution shift, genotype-environment interaction, and robust out-of-sample forecasting.

## Early Biological Forecasting

This module investigates whether final biological outcomes can be anticipated from information available earlier in the biological process.

```text
Day 5 → Day 10 → Day 15 → Day 30 → Final Outcome
```

The model observes only information available up to time `t` and forecasts the probability or distribution of a later biological outcome.

A future decision-support interface could report a predicted probability of successful development, a prediction interval, and the primary predictive drivers such as genomic profile, early growth, treatment, and environmental condition.

The point is the **decision architecture**: early biological observations become probabilistic forecasts rather than merely descriptive measurements.

## Uncertainty, Not Just Predictions

A scientific prediction system should not report a point forecast without communicating uncertainty.

Outputs should include predictive intervals or, preferably, predictive distributions:

\[
p(Y_{future}\mid G,E,X)
\]

Candidate approaches include bootstrapping, conformal prediction, Bayesian modelling, and calibrated predictive intervals.

### Abstention

If a genotype, environment, protocol, or combination is sufficiently different from the training distribution, the system should be capable of returning:

> **LOW CONFIDENCE — insufficient evidence for reliable prediction**

Abstention is treated as a scientific capability rather than a failure. A trustworthy system should know when it does not know.

## AI-Assisted Experiment Selection

This module moves beyond prediction toward experimental decision intelligence.

Suppose researchers can test only another 20 combinations. Instead of choosing genotype, protocol, and environment combinations arbitrarily, the system asks:

> **Which experiment would provide the greatest expected information or improvement?**

A Bayesian-optimization or active-learning framework can prioritize experiments according to expected improvement and information value.

A future application could recommend the next genotype-treatment-environment combination to test and explain whether the recommendation is driven by high predicted potential, high uncertainty, or both.

This demonstrates how machine learning can potentially change not only how experiments are analysed, but also how subsequent experiments are selected.

## GenAI Scientific Interface

GenAI is deliberately developed **after** the quantitative engine.

The project does not place a generic chatbot at its centre. GenAI becomes an interface to validated scientific data, model outputs, uncertainty estimates, and experimental information.

```text
Scientist ↔ GenAI ↔ Models + Database
```

A researcher might ask which genotypes show unusually high regeneration under a treatment or why a model downgraded a particular accession. The language model should query the underlying data and modelling layer and summarize verified outputs rather than invent scientific answers.

## Case Studies

### Case Study A — In-Vitro Regeneration Intelligence

The first case study investigates whether genetic information and protocol variation contain sufficient predictive signal to model regeneration-related phenotypes.

The public AraPheno setting provides the key structure:

**Genetic variation + in-vitro propagation + different protocols + measured regeneration outcome**

Core questions include:

- Can regeneration outcomes be predicted for unseen accessions?
- How much predictive information is contained in genomic structure?
- Does protocol information materially improve prediction?
- Are genotype × protocol interactions identifiable?
- How much uncertainty surrounds predictions?
- When should the system abstain?
- Which biological observations drive model predictions?

### Case Study B — Genotype × Environment Forecasting

The second case study demonstrates generalization across environmental conditions using public multi-environment plant data.

The objective is not simply to predict yield. It is to demonstrate genomic prediction, genotype × environment interaction, environment-aware validation, forecasting under distribution shift, uncertainty, and biological generalization.

### Case Study C — AI-Guided Experiment Selection

The third case study extends validated predictive models into experimental decision support under constrained experimental capacity.

```text
Prediction → Uncertainty → Information Value → Experiment Selection
```

The purpose is to show how quantitative modelling can potentially reduce inefficient experimentation and prioritize informative biological experiments.

## Industrial Transferability

This repository uses public biological datasets and does not use proprietary company information. It demonstrates methodological capabilities that could potentially be adapted to commercial plant biotechnology where suitable genotype, phenotype, protocol, environmental, longitudinal, or production information exists.

```text
Public Dataset
      ↓
Genomic / Phenotypic Modelling
      ↓
Prediction
      ↓
Uncertainty
      ↓
Experiment Selection
      ↓
Decision Support
```

> **The appropriate industrial application can only be defined after understanding the biological process, available data, operational constraints, and business objective.**

A public-data proof of concept does not automatically establish performance on a proprietary commercial biological system.

See [`docs/industrial_transferability.md`](docs/industrial_transferability.md) for the detailed industrial perspective.

## Repository Structure

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

## Scientific and Engineering Principles

1. **Real public data before synthetic demonstrations.** Public biological data support the principal empirical claims.
2. **Prediction is not biological causation.** Predictive associations are not presented as causal mechanisms without appropriate experimental evidence.
3. **Generalization matters more than in-sample performance.** Validation reflects the intended biological deployment problem.
4. **Prevent genetic leakage.** Relatedness must not make the test set unrealistically easy.
5. **Quantify uncertainty.** Point predictions alone are insufficient for scientific decision support.
6. **Allow abstention.** The model must recognize observations outside its reliable evidence base.
7. **GenAI does not generate scientific truth.** Language models operate over verified data and model outputs.
8. **Reproducibility.** Data provenance, preprocessing, random seeds, environments, model configuration, validation protocols, and reported results should be reproducible.
9. **Industrial claims remain conditional.** Transferable methodology is not equivalent to validated performance on an unobserved proprietary process.

## Project Direction

Plant Intelligence Lab is an independent initiative in **computational plant biotechnology**.

A future forecasting component may use the identity:

### PhytoForecast
**Genomic Intelligence for Plant Performance**

The completed repository is intended to demonstrate competence across high-dimensional genomics (`p >> n`), quantitative genetics, genomic prediction, statistical learning, machine learning, nonstationarity and distribution shift, genotype × environment effects, probabilistic forecasting, uncertainty quantification, model abstention, optimization, active learning, Bayesian experimental design, explainability, GenAI, scientific data architecture, reproducible computational research, and biological decision science.

These capabilities are connected by a genuine biological problem rather than presented as a disconnected collection of algorithms.

The intended progression is:

```text
Biological Data
    → Quantitative Genetics
    → Machine Learning
    → Forecasting
    → Uncertainty
    → Experiment Optimization
    → Decision Intelligence
```

> *An open-source proof of concept exploring how quantitative genetics, machine learning, probabilistic forecasting and AI-assisted experimental design can support decision-making in plant biotechnology.*
