# Case Study B — Step B3 High-Dimensional ML Challengers

## Question

After the classical genotype × environment benchmark was optimized and frozen, Step B3 asks a deliberately narrow question:

\[
\boxed{\text{Can nonlinear/high-dimensional ML materially beat the frozen classical G×E envelope?}}
\]

The challenger set was fixed before execution:

- PCA + RBF Kernel Ridge;
- Random Forest;
- XGBoost;
- LightGBM.

The frozen classical RMSE thresholds are 0.890109 for CV-G and 0.846926 for CV2. These thresholds were established before the ML run and are not changed after observing challenger performance.

## Validation and leakage control

Only the two pre-registered primary deployments are used for the challenger contest:

- **CV-G:** whole genotypes are unseen across all environments;
- **CV2:** one genotype × environment phenotype cell per line is withheld while the remaining environments for that genotype stay observed.

The B2-R robustness result showed that predictive covariance was predominantly environment-specific. The ML challengers therefore fit one genomic response model per represented environment. This gives each nonlinear learner a direct opportunity to learn environment-dependent marker-response structure without pretending that a categorical environment identifier can extrapolate to a genuinely unseen environment.

Every preprocessing operation and hyperparameter choice is confined to the relevant outer-training partition. PCA is fitted inside training data only. Hyperparameter selection uses deterministic two-fold inner validation within each outer-training environment. The outer CV-G/CV2 observations are not used for model selection.

## Results

| Validation | Model | RMSE | MAE | R² | Correlation |
|---|---|---:|---:|---:|---:|
| CV-G | PCA+Kernel | 0.883487 | 0.679751 | 0.218145 | 0.467271 |
| CV-G | **Random Forest** | **0.879556** | 0.678329 | **0.225087** | **0.477517** |
| CV-G | XGBoost | 0.882109 | 0.680828 | 0.220583 | 0.471950 |
| CV-G | LightGBM | 0.884948 | **0.677711** | 0.215558 | 0.473629 |
| CV2 | PCA+Kernel | 0.846240 | 0.644014 | 0.245631 | 0.497055 |
| CV2 | **Random Forest** | **0.843988** | 0.644219 | **0.249641** | **0.503024** |
| CV2 | XGBoost | 0.845221 | **0.639508** | 0.247447 | 0.500548 |
| CV2 | LightGBM | 0.855454 | 0.653169 | 0.229115 | 0.487251 |

Random Forest has the best RMSE point estimate in both primary deployment regimes. Relative to the frozen classical envelope, the point-estimate reductions are approximately 1.19% in CV-G and 0.35% in CV2.

However, point estimates are not sufficient for model admission.

## Paired comparison against the frozen classical champion

The candidate-minus-classical RMSE deltas are evaluated with a 2,000-replicate genotype-cluster bootstrap.

| Validation | Model | RMSE delta vs frozen | 95% bootstrap interval | Bootstrap improvement frequency | Robust win? |
|---|---|---:|---:|---:|---|
| CV-G | PCA+Kernel | -0.006622 | [-0.019338, 0.006714] | 0.8325 | No |
| CV-G | Random Forest | -0.010553 | [-0.023351, 0.001237] | 0.9580 | No |
| CV-G | XGBoost | -0.008001 | [-0.019617, 0.003015] | 0.9205 | No |
| CV-G | LightGBM | -0.005162 | [-0.019553, 0.009103] | 0.7595 | No |
| CV2 | PCA+Kernel | -0.000686 | [-0.022804, 0.020372] | 0.5185 | No |
| CV2 | Random Forest | -0.002939 | [-0.021055, 0.017146] | 0.6225 | No |
| CV2 | XGBoost | -0.001705 | [-0.022430, 0.020340] | 0.5650 | No |
| CV2 | LightGBM | +0.008527 | [-0.014851, 0.034300] | 0.2470 | No |

No challenger's RMSE bootstrap interval lies entirely below zero. Therefore **none of the nonlinear models robustly beats the frozen classical G×E champion under the admission rule established before Step B3**.

Random Forest is the strongest challenger: it improves the point estimate in both primary regimes and has a 95.8% bootstrap improvement frequency in CV-G, but its CV-G interval still crosses zero narrowly and its CV2 evidence is much weaker. The correct conclusion is therefore *promising but statistically unresolved incremental value*, not a nonlinear-model victory.

## Scientific interpretation

Step B3 produces a useful negative result:

\[
\boxed{\text{nonlinear complexity does not earn a decisive promotion over the optimized classical G×E benchmark}}
\]

on this dataset and validation design.

This does not mean the nonlinear learners are poor. PCA+Kernel, Random Forest, and XGBoost all slightly improve the CV-G and CV2 RMSE point estimates. The result instead shows that the optimized classical G×E model already captures most of the transferable predictive structure available from 1,279 DArT markers and four represented mega-environments.

The result also strengthens the repository's methodological principle that complexity must earn measurable value. The project does not promote a model simply because it is more modern or more computationally elaborate.

## Model status after B3

The **classical G×E family remains the reference/champion family** because no challenger establishes a robust paired improvement. Random Forest is retained as the strongest nonlinear sensitivity model, not as the new production champion.

No neural network is justified at this point. The present sample contains 599 lines and only four categorical environments; adding a neural model after four well-established nonlinear challengers fail to secure a robust win would be model chasing rather than evidence-driven development.

## Reproducibility

Implementation:

`src/plant_intelligence/models/wheat_gxe_ml.py`

Tests:

`tests/test_case_study_b_ml.py`

Workflow:

`.github/workflows/case-study-b-ml.yml`

Validated outputs:

- `reports/results/case_study_b_ml_summary.csv`
- `reports/results/case_study_b_ml_selection.csv`
- `reports/results/case_study_b_ml_predictions.csv`
- `reports/results/case_study_b_ml_challenger_bootstrap.csv`
- `reports/results/case_study_b_ml_envelope_comparison.csv`
- `reports/figures/case_study_b_ml_challengers.png`

The dedicated workflow passed all targeted tests, executed the four challenger families under the locked CV-G and CV2 definitions, verified every output, and published the compact evidence to the repository.
