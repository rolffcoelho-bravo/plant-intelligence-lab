# Case Study B6-R — Environmental-Transfer Robustness

## Question

Step B6 showed that continuous environmental information produced a favorable pooled point estimate for unseen-environment prediction, but the gain over genomics alone was not stable across environment clusters. B6-R therefore asks whether that weakness is primarily a representation problem and whether environmental novelty predicts transfer difficulty.

The B5 outer folds remain unchanged. No environment or genotype split is redefined after observing B6 results.

## Pre-registered robustness neighborhood

The search is deliberately small rather than an AutoML exercise. Nine one-factor configurations probe the B6 reference around four dimensions:

- environmental RBF bandwidth: `0.5×`, `1×`, `2×` the median-distance rule;
- environmental Nyström rank: `8`, `16`, `32`;
- genomic PCA rank: `10`, `20`, `40`;
- ridge penalty: `3`, `10`, `30`.

For each outer environment fold, the other four frozen B5 environment folds are used as inner validation folds. Selection is based only on additive `G+E` RMSE. The chosen representation is then reused without further tuning for the product-kernel `G+E+G×E` challenger and for all five strict genotype folds belonging to that held-out environment fold.

This design prevents the interaction model from receiving a larger hyperparameter-search advantage and keeps the 25 strict double-cold-start scenarios confirmatory.

## Selected representations

| Outer environment fold | Selected configuration | Genomic rank | Environmental rank | Bandwidth multiplier | Ridge alpha |
|---:|---|---:|---:|---:|---:|
| 0 | environment_narrower | 20 | 16 | 2.0 | 10 |
| 1 | environment_narrower | 20 | 16 | 2.0 | 10 |
| 2 | environment_rank_32 | 20 | 32 | 1.0 | 10 |
| 3 | environment_narrower | 20 | 16 | 2.0 | 10 |
| 4 | environment_rank_32 | 20 | 32 | 1.0 | 10 |

The selected configurations change only the environmental geometry. None of the genomic-rank or ridge-penalty alternatives wins an outer-fold selection. Three folds prefer a narrower RBF neighborhood and two prefer a higher environmental rank.

This is evidence about predictive representation, not a claim that these hyperparameters are biological constants.

## Primary unseen-environment result

| Model | RMSE | MAE | R² | Correlation |
|---|---:|---:|---:|---:|
| B6 fixed G+E | 2.6495 | 2.1232 | 0.0958 | 0.3497 |
| Selected G | 2.6876 | 2.1524 | 0.0696 | 0.2722 |
| **Selected G+E** | **2.5693** | 2.0507 | 0.1497 | 0.4002 |
| Selected G+E+G×E | **2.5666** | **2.0445** | **0.1514** | **0.4260** |

Nested environmental representation selection lowers additive `G+E` RMSE by approximately **3.03%** relative to the fixed B6 `G+E` representation and by approximately **4.40%** relative to the correspondingly selected genomic-only model.

The product interaction changes pooled RMSE only from **2.5693 to 2.5666**, so its incremental RMSE value is negligible after the environmental representation is improved.

## Strict unseen-genotype + unseen-environment result

| Model | RMSE | MAE | R² | Correlation |
|---|---:|---:|---:|---:|
| B6 fixed G+E | 2.6527 | 2.1261 | 0.0936 | 0.3474 |
| Selected G | 2.6917 | 2.1558 | 0.0668 | 0.2681 |
| **Selected G+E** | **2.5726** | 2.0537 | 0.1475 | 0.3979 |
| Selected G+E+G×E | **2.5724** | **2.0499** | **0.1477** | **0.4229** |

The same pattern survives the 25 double-cold-start scenarios. The selected additive environmental representation improves RMSE by approximately **3.02%** relative to the fixed B6 `G+E` representation and by approximately **4.42%** relative to selected genomics alone.

## Environment-cluster uncertainty

The point-estimate gains remain heterogeneous across environments.

For unseen-environment prediction, `Selected-G+E − Selected-G` has RMSE difference **-0.1183**, with 95% environment-cluster bootstrap interval **[-0.2594, 0.0336]** and improvement frequency **0.935**.

For the strict double cold start the corresponding difference is **-0.1190**, with interval **[-0.2645, 0.0280]** and improvement frequency **0.9415**.

The selected representation also improves on the fixed B6 `G+E` point estimate, but its 95% bootstrap interval still narrowly crosses zero in both regimes. Therefore B6-R strengthens the evidence for environmental information without claiming a 95%-robust universal transfer gain.

The product-kernel interaction remains unsupported as an RMSE improvement: its incremental RMSE difference relative to selected additive `G+E` is approximately zero in both regimes, with improvement frequency near 0.5.

## Environmental novelty

For each held-out environment, novelty is measured from the continuous 202-dimensional environmental vector after training-only standardization. The primary diagnostic uses mean distance to the five nearest training environments; nearest-neighbor distance is also reported.

For selected additive `G+E` under unseen-environment validation:

- Spearman correlation between mean-five-neighbor novelty and environment RMSE: **0.149**, `p = 0.084`;
- Spearman correlation between nearest-environment novelty and RMSE: **0.190**, `p = 0.0267`;
- low-novelty quartile mean environment RMSE: **2.423**;
- high-novelty quartile mean environment RMSE: **2.806**;
- high-minus-low quartile difference: **0.383**.

The strict double cold start is similar: nearest-environment novelty has Spearman correlation **0.187** with RMSE (`p = 0.0296`), while the high-novelty quartile is about **0.376 RMSE units** harder than the low-novelty quartile.

The relationship is therefore **weak but directionally consistent**, not strong enough to justify a hard operational abstention threshold. It does, however, support environmental support distance as a candidate reliability feature for later deployment work.

## Scientific interpretation

B6-R changes the diagnosis in an important way.

The first B6 representation was not simply missing environmental signal. A more local or higher-rank environmental geometry materially improves the pooled transfer result, while changes to genomic rank and ridge regularization are not selected. This suggests that the dominant unresolved issue lies in **how environmental similarity is represented**, rather than in generic model complexity.

At the same time, the environment-cluster intervals still cross zero and the simple multiplicative product kernel contributes essentially no RMSE improvement after environmental representation is refined. The project therefore does not claim that environmental transfer is solved.

The current evidence supports the narrower statement:

\[
\boxed{\text{environmental geometry matters for transfer}}
\]

while

\[
\boxed{\text{transfer remains heterogeneous and representation-limited}}.
\]

## Reproducibility

Implementation:

`src/plant_intelligence/models/maize_environment_transfer_robustness.py`

Tests:

`tests/test_case_study_b6r_transfer_robustness.py`

Workflow:

`.github/workflows/case-study-b6r-transfer-robustness.yml`

Published evidence:

- `reports/results/case_study_b6r_transfer_summary.csv`
- `reports/results/case_study_b6r_nested_selection.csv`
- `reports/results/case_study_b6r_selected_configs.csv`
- `reports/results/case_study_b6r_environment_errors.csv`
- `reports/results/case_study_b6r_novelty_diagnostics.csv`
- `reports/results/case_study_b6r_bootstrap.csv`
- `reports/figures/case_study_b6r_novelty_vs_error.png`

The figure places its legend horizontally along the bottom so the data region remains unobstructed.

## Current admission boundary

B6-R is complete. The outer B5 folds remain controlling and the nine-configuration robustness neighborhood is frozen. Further work should not expand this grid to chase a better score.

The 202 environmental variables are naturally organized by environmental quantity and crop-development interval. The next high-value question is whether a **biologically structured environmental representation** can outperform an equal-weight generic distance by learning which environmental processes and growth stages carry transferable information.
