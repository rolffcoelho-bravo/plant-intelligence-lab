# Methodology

Plant Intelligence Lab is designed around a sequence that starts with a biologically meaningful prediction problem and ends with decision support. The methodology is intentionally model-agnostic: no algorithm is treated as valuable unless it improves out-of-sample biological prediction or experimental decisions.

## 1. Prediction target

The general forecasting problem is:

\[
G + P + E + X_t \rightarrow \widehat{Y}_{t+h}
\]

where:

- `G` = genomic information
- `P` = protocol or treatment
- `E` = environment
- `X_t` = observations available up to time `t`
- `Y_(t+h)` = future biological outcome

Depending on the case study, not every component is required.

## 2. Classical quantitative-genetics baseline

A serious benchmark begins with a mixed-model representation:

\[
y = X\beta + Zu + \epsilon
\]

with genomic relationship information used to model relatedness among accessions or lines.

The baseline is intended to answer a practical question: how much predictive value is available from established quantitative-genetics methods before more complex ML models are considered?

## 3. High-dimensional learning

Genomic prediction frequently operates in the regime:

\[
p \gg n
\]

with many more markers than biological observations.

Candidate methods include:

- Elastic Net
- kernel methods
- Random Forest
- XGBoost / LightGBM
- carefully regularized neural networks

Models will be judged on biological generalization, not algorithmic novelty alone.

## 4. Validation strategy

Random train/test splitting can overstate performance when genetically related observations are present in both sets.

Validation should therefore reflect the deployment question. Depending on the dataset, this can include:

- grouped cross-validation by genotype or accession cluster
- leave-group-out validation
- environment holdout
- protocol holdout where scientifically meaningful
- nested cross-validation for model selection

The most important criterion is whether the test set represents a genuinely harder and more realistic biological prediction problem.

## 5. Evaluation

Core predictive metrics include:

- RMSE
- MAE
- R²
- Pearson or rank correlation between observed and predicted phenotype

Performance should be accompanied by uncertainty metrics where possible, including:

- interval coverage
- interval width
- calibration error
- abstention rate
- performance conditional on confidence

## 6. Genotype × environment and genotype × protocol

A classical interaction structure is:

\[
Y_{ij} = \mu + G_i + E_j + (G \times E)_{ij} + \epsilon_{ij}
\]

and similarly for genotype × protocol effects.

Machine-learning extensions may estimate nonlinear response surfaces:

\[
\widehat{Y}=f(G,E,P,G\times E,G\times P)
\]

The goal is to forecast conditional biological performance, not to assume a genotype has one fixed response independent of context.

## 7. Early biological forecasting

When longitudinal observations are available, models should estimate future outcomes using only information that would genuinely have been available at prediction time.

\[
P(Y_T \mid X_{0:t}), \qquad t<T
\]

This prevents temporal leakage and directly tests whether biological decisions can be made earlier.

## 8. Uncertainty quantification

Candidate approaches include:

- bootstrap predictive intervals
- conformal prediction
- Bayesian posterior predictive distributions
- calibrated ensemble uncertainty

The repository should never present a point estimate as sufficient evidence for high-stakes biological decisions.

## 9. Out-of-distribution detection and abstention

Predictions should be screened for evidence that the query lies outside the reliable training domain.

Potential indicators include:

- genomic distance from training observations
- environmental covariate distance
- model disagreement
- predictive uncertainty
- conformal nonconformity measures

The system should be able to return a low-confidence state instead of manufacturing precision.

## 10. AI-assisted experiment selection

Where a validated predictive model exists, candidate experiments can be ranked using acquisition functions balancing expected improvement and uncertainty:

\[
x^*=\arg\max_x \left[E(\text{improvement}\mid x)+\lambda U(x)\right]
\]

The objective is not to automate biology blindly. It is to make constrained experimental capacity more informative.

## 11. Explainability

Interpretation methods should be selected according to the model and biological question. Candidate approaches include:

- coefficient inspection for sparse linear models
- permutation importance
- SHAP values where appropriate
- partial dependence or accumulated local effects
- variance-component interpretation

Interpretability outputs are treated as predictive evidence, not proof of biological causation.

## 12. Grounded GenAI scientific interface

The scientific interface is built only after validated quantitative outputs exist. The implemented architecture is evidence-first:

\[
\text{question}
\rightarrow
\text{validated result tables}
\rightarrow
\text{grounding packet}
\rightarrow
\text{provider adapter}
\rightarrow
\text{claim verification}
\rightarrow
\text{answer or withholding}
\]

The grounding packet contains the user question, selected quantitative evidence, exact repository source files, an explicit answerability state, and instructions preserving uncertainty, causality limits, and retrospective-versus-prospective distinctions.

### 12.1 Answerability boundary

Questions that ask the repository to establish evidence it does not contain are marked `unsupported` before generation. Current examples include causal-gene claims, molecular mechanisms, prospective laboratory savings, commercial validation, and transfer to another laboratory. Unsupported questions are required to return an evidence-boundary response rather than an inferred scientific answer.

### 12.2 Provider-independent adapter

The generative layer implements a common adapter contract. Any external provider SDK, local model, or callable generation function can be wrapped behind the same interface. Provider-specific code therefore remains outside the scientific evidence layer.

A deterministic `GroundedTemplateAdapter` is included as the reproducible reference implementation used in CI. It is not represented as an LLM benchmark result.

### 12.3 Claim verification

Generated drafts are checked before release. The verifier currently tests:

- numerical claims against the values carried in the grounding packet;
- source-file traceability for material quantitative claims;
- uncertainty omission when uncertainty evidence is relevant;
- omission of the retrospective boundary for experiment-selection claims;
- omission of abstention/reliability information when supplied;
- positive causality inflation;
- prospective or commercial-performance inflation.

If verification fails, the runtime withholds the generated draft rather than returning it as a scientific answer.

### 12.4 Grounding evaluation benchmark

The repository includes a compact benchmark with supported questions and adversarial boundary cases. It covers forecast accuracy, uncertainty calibration, abstention, experiment selection, protocol response, genomic-only prediction, multi-claim summaries, causal-gene traps, prospective-savings traps, external-laboratory transfer, and overgeneralization about genomics.

The benchmark records a **Grounded Scientific Answer Rate**, supported-case pass rate, unsupported-safe-response rate, source-traceability rate, number of numerical claims checked, and verification failures.

The committed reference-adapter benchmark is a deterministic software-validation baseline. A score of 100% for the reference adapter demonstrates that the evidence-routing and verification machinery behaves as specified; it must not be interpreted as empirical performance of an external language model. External providers should be evaluated through the same benchmark before their output is treated as acceptable scientific rendering.
