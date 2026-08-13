# Case Study B8 — Decision-Horizon Environmental Forecasting

## Purpose

B8 asks **when environmental information becomes useful for cold-start yield prediction**. The B5 environment/genotype folds and the B6-R outer-fold representation choices remain frozen. B8 changes only the environmental information admitted at each horizon, so this is an information-ablation study rather than a new hyperparameter competition.

The sequence is

\[
G \rightarrow G+E_{history} \rightarrow G+E_{early} \rightarrow G+E_{through\ floral\ initiation} \rightarrow G+E_{reproductive} \rightarrow G+E_{full}.
\]

## Source-level availability boundary

The Genomes-to-Fields ECOV table is a retrospective research resource. Lopez-Cruz et al. (2023), *Nature Communications* 14:6904, DOI `10.1038/s41467-023-42687-4`, generated environmental covariates with APSIM, summarized daily outputs within phenological stages, and tuned year-location thermal time so simulated flowering aligned with average observed silking.

This means an information horizon can be **column-safe** while still being **retrospective at source level**. B8 therefore does not relabel current-year stage ECOVs as prospective live-deployment inputs.

The pre-season location-history representation is stricter with respect to the held-out year-location: it never reads that environment's current-year ECOV row. However, the frozen B5 environment folds are not forward-chaining calendar-time folds, so this remains an input-availability experiment under environment cold start rather than a prospective future-year trial.

## Availability audit

The five target-proximal `yield_*` outputs identified in B7 remain excluded from all B8 current-year environmental candidates.

| Horizon | Admitted source intervals | Current-year ECOV columns | Interpretation state |
|---|---|---:|---|
| Pre-season G only | none | 0 | genomics only |
| Pre-season location history | none from held-out year-location | 0 | training-environment history |
| Pre-flowering proxy | `GerEme`, `EmeEnJ` | 44 | retrospective horizon proxy |
| Through `EnJFlo` | + `EnJFlo` | 66 | retrospective horizon proxy |
| Reproductive-stage proxy | cumulative through `FlwStG` | 132 | retrospective horizon proxy |
| Full-season nonleaky | all nine source intervals | 197 | retrospective reference |

Every horizon satisfies the rule that no post-horizon ECOV column can enter an earlier representation.

### Pre-season history construction

For a held-out year-location, B8 averages non-target-proximal ECOV histories from outer-training environments at the same location. If no same-location history exists, it uses the global outer-training mean. A training environment's own ECOV row is excluded from its own history proxy, including the global fallback.

Across the 136 held-out environment assignments:

- **121 / 136 (88.97%)** have same-location history in the corresponding outer training set;
- **15 / 136** use the global training-history fallback;
- no held-out current-year ECOV row is used by the pre-season history proxy.

## Out-of-sample results

### CV-E — unseen environment

| Horizon | RMSE | MAE | R² | Correlation | RMSE change vs previous |
|---|---:|---:|---:|---:|---:|
| Pre-season G only | 2.6876 | 2.1524 | 0.0696 | 0.2722 | — |
| Pre-season location history | 2.7160 | 2.1718 | 0.0498 | 0.3535 | +1.06% |
| Pre-flowering proxy | 2.7653 | 2.2380 | 0.0150 | 0.2544 | +1.82% |
| Through `EnJFlo` | 2.8437 | 2.2946 | -0.0416 | 0.2230 | +2.84% |
| **Reproductive-stage proxy** | **2.6108** | **2.0832** | **0.1220** | **0.3789** | **-8.19%** |
| Full-season nonleaky | **2.5772** | **2.0601** | **0.1444** | **0.3952** | -1.28% |

### CV-GE — unseen genotype + unseen environment

| Horizon | RMSE | MAE | R² | Correlation | RMSE change vs previous |
|---|---:|---:|---:|---:|---:|
| Pre-season G only | 2.6917 | 2.1558 | 0.0668 | 0.2681 | — |
| Pre-season location history | 2.7177 | 2.1741 | 0.0487 | 0.3520 | +0.97% |
| Pre-flowering proxy | 2.7686 | 2.2410 | 0.0127 | 0.2517 | +1.87% |
| Through `EnJFlo` | 2.8465 | 2.2975 | -0.0437 | 0.2206 | +2.81% |
| **Reproductive-stage proxy** | **2.6141** | **2.0867** | **0.1198** | **0.3766** | **-8.16%** |
| Full-season nonleaky | **2.5805** | **2.0630** | **0.1423** | **0.3929** | -1.29% |

## Robust information transition

The B8 result is not monotonic. Pre-season history does not lower RMSE relative to G only, and the early current-year representations are weaker under the frozen architecture. The major transition occurs when the cumulative representation expands through the reproductive-stage intervals.

The paired 2,000-replicate environment-cluster bootstrap gives:

- CV-E reproductive-stage minus preceding 66-variable horizon: RMSE difference **-0.2329**, 95% interval **[-0.3688, -0.0933]**, improvement frequency **1.000**;
- CV-GE: **-0.2324**, 95% interval **[-0.3791, -0.0953]**, improvement frequency **1.000**.

The later full-season improvement beyond the reproductive-stage representation is small and its 95% environment-cluster interval crosses zero.

The reproductive-stage point estimate is also better than G only, but that broader comparison is not 95%-robust across environment clusters. B8 therefore does not claim that the retrospective reproductive-stage proxy is a validated deployment champion.

## Scientific interpretation

B8 supports the bounded statement

\[
\boxed{\text{environmental predictive value is strongly horizon-dependent}}
\]

and, within this retrospective ECOV representation,

\[
\boxed{\text{the largest information gain appears only when reproductive-stage variables enter}.}
\]

This does **not** show that early environmental conditions are biologically unimportant. It shows that the evaluated early environmental similarity representation does not convert them into lower cold-start RMSE under the frozen model.

The result strengthens the project's broader theme of finding the **minimum sufficient information for reliable biological decisions** rather than assuming that more or earlier features automatically improve prediction.

## Next deployment boundary

A genuine operational test must reconstruct environmental state from information that exists at forecast issuance time, without future observed phenology or future realized weather. Candidate inputs include pre-season historical climate and soil information, weather forecasts issued at the decision date, observed-to-date weather, and crop-state or thermal-time features constructed without future silking calibration.

Only after that prospective-input reconstruction should the project ask whether the B8 information transition survives in live-available environmental features.

## Reproducibility

Public entry point:

`src/plant_intelligence/models/maize_environment_decision_horizons.py`

Execution boundary:

`src/plant_intelligence/models/maize_environment_decision_horizon_execution.py`

Tests:

- `tests/test_case_study_b8_decision_horizons.py`
- `tests/test_case_study_b8_availability_safety.py`

Workflow:

`.github/workflows/case-study-b8-decision-horizons.yml`

Published evidence:

- `reports/results/case_study_b8_decision_horizon_summary.csv`
- `reports/results/case_study_b8_decision_horizon_bootstrap.csv`
- `reports/results/case_study_b8_environment_metrics.csv`
- `reports/results/case_study_b8_availability_audit.csv`
- `reports/results/case_study_b8_preseason_history_audit.csv`
- `reports/results/case_study_b8_design_audit.csv`
- `reports/figures/case_study_b8_decision_horizon.png`

The B5 outer folds remain controlling throughout B8.
