# Limitations

Plant Intelligence Lab is a public proof of concept in computational plant biotechnology. Its conclusions must remain bounded by the data and validation design used in each case study.

## Public-data limitation

Public datasets are useful for demonstrating methodology, but they do not reproduce the full complexity of proprietary commercial biotechnology systems. Results obtained on public plant datasets should not be interpreted as validated performance for another species, laboratory, production environment, or commercial process.

## Sample-size limitation

Genomic problems frequently operate in a high-dimensional regime with far more predictors than observations. This increases the risk of overfitting, unstable feature attribution, and optimistic validation if data splitting is not designed carefully.

## Population structure and relatedness

Closely related accessions can make prediction easier than true deployment on genetically distinct material. Validation must therefore account for relatedness where possible. Performance under naive random splitting may be reported only as a diagnostic comparison, not as the primary estimate of generalization.

## Phenotype quality

No model can recover information that is absent from noisy or weakly measured phenotypes. Measurement error, batch effects, inconsistent experimental conditions, and missing covariates can materially limit predictive performance.

## Environment and protocol coverage

A model trained on a narrow range of environments or protocols may not generalize to conditions outside that range. Out-of-distribution detection and explicit abstention are therefore part of the project design.

## Causality

Predictive importance, association, SHAP values, regression coefficients, or genomic signal do not by themselves establish causal biological mechanisms.

## Cross-species transfer

Demonstrations using *Arabidopsis thaliana*, wheat, or other public systems should not be treated as evidence that the same model architecture or fitted parameters will transfer unchanged to commercially important species.

## Early forecasting

Early-outcome prediction is only meaningful when the data preserve real temporal ordering. Features recorded after the intended prediction time must never be used in training or evaluation.

## Active learning and Bayesian optimization

Experiment-selection methods depend on the validity of the surrogate model and acquisition assumptions. A recommended experiment is a quantitative prioritization, not a substitute for biological expertise, safety requirements, or experimental judgement.

## GenAI

Generative AI is limited to interaction with verified data and model outputs. It should not generate unsupported biological claims, fabricate experimental history, or override uncertainty information.

## Industrial applicability

The repository is intended to show transferable computational capability. Any industrial deployment would require a new audit of the biological objective, available data, measurement process, operational constraints, economics, and prospective performance.
