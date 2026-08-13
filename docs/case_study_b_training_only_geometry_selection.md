# Case Study B10-S — Training-Only Forward Selection of Environmental Spectral Geometry

## Purpose

B10-S tests whether the geometry sensitivity discovered retrospectively in B10-R can be converted into a valid forecast-time procedure.

The candidate family is not expanded. It is exactly the B10-R diagnostic grid:

- environmental rank: 8, 16, 32;
- RBF gamma multiplier: 0.5, 1, 2, 4;
- genomic rank fixed at 20;
- ridge alpha fixed at 10;
- B9 T2 information horizon unchanged;
- B9 forward-year outer tests unchanged.

For outer deployment year `t`, B10-S selects geometry only from chronological inner validation years `y < t`. Each inner validation year is itself predicted only from years `< y`. The outer-year outcome is never admitted to selection.

A minimum of two chronological inner validation years is required. Therefore 2016 is explicitly classified as `INSUFFICIENT_HISTORY_FALLBACK` and uses the frozen B10 geometry (rank 16, gamma multiplier 2) without inspecting 2016 yield.

The selection criterion is the equal-weight mean of inner-year RMSE, with pooled inner RMSE and the pre-existing B10-R grid order used only as deterministic tie-breaks.

## Selected geometries

| Outer year | Status | Historical inner years | Selected T2 geometry |
|---:|---|---|---|
| 2016 | `INSUFFICIENT_HISTORY_FALLBACK` | 2015 | frozen rank 16, gamma 2 |
| 2017 | `TRAINING_ONLY_SELECTED` | 2015–2016 | rank 32, gamma 2 |
| 2018 | `TRAINING_ONLY_SELECTED` | 2015–2017 | rank 8, gamma 2 |
| 2019 | `TRAINING_ONLY_SELECTED` | 2015–2018 | rank 8, gamma 2 |
| 2020 | `TRAINING_ONLY_SELECTED` | 2015–2019 | rank 8, gamma 2 |
| 2021 | `TRAINING_ONLY_SELECTED` | 2015–2020 | rank 32, gamma 2 |

Every row in the machine-readable selection audit records `outer_outcome_used_for_selection=False`.

## Primary forward-year result

| Model | RMSE | MAE | R² | Correlation |
|---|---:|---:|---:|---:|
| Frozen T1 | **2.6614** | **2.1510** | **0.0595** | **0.3405** |
| Frozen T2 | 3.2843 | 2.4859 | -0.4322 | 0.1977 |
| **Training-only selected T2** | **3.4095** | **2.6219** | **-0.5435** | **0.1457** |

B10-S therefore produces a clear negative result. Historical chronological selection does **not** recover the useful oracle geometries identified in B10-R. It makes pooled T2 prediction worse than the already-poor frozen T2 model.

The selected T2 RMSE is **0.1252 higher** than frozen T2. The 2,000-replicate paired environment-cluster 95% interval for `Selected-T2 − Frozen-T2` is **[0.0303, 0.2323]** with improvement frequency **0.45%**. The six-year cluster interval is also above zero, **[0.0231, 0.2865]**, with improvement frequency **0.60%**.

Relative to frozen T1, selected T2 is worse by **0.7481 RMSE**. The environment-cluster 95% interval is **[0.3570, 1.1995]** and the year-cluster interval is **[0.0053, 2.0172]**. Thus the training-only selector does not justify admitting T2 over T1.

## Year-level behavior

| Test year | Frozen T1 RMSE | Frozen T2 RMSE | Selected T2 RMSE | Training-only selection outcome |
|---:|---:|---:|---:|---|
| 2016 | 2.7275 | 6.6486 | 6.6486 | fallback; no sufficient history |
| 2017 | **2.2621** | 2.9975 | **3.6281** | selection materially worsens T2 |
| 2018 | 2.5527 | 2.5926 | **2.5450** | small successful transfer |
| 2019 | 2.9195 | **2.7464** | 2.8427 | T2 remains useful, but selector loses value |
| 2020 | 2.7452 | **2.5389** | 2.7553 | selector removes the frozen T2 gain |
| 2021 | 2.4752 | **2.4619** | 2.7494 | selector materially worsens T2 |

The training-only rule helps only modestly in 2018. It is harmful in 2017, 2020 and 2021, and does not improve the 2016 fallback case.

## Oracle regret audit

B10-R's held-out-outcome diagnostic grid remains useful only as an explanatory upper bound. It is never admitted for deployment selection.

| Year | Training-only selected | Selected RMSE | Oracle diagnostic | Oracle RMSE | Regret |
|---:|---|---:|---|---:|---:|
| 2016 | frozen rank16/gamma2 | 6.6486 | rank8/gamma4 | 2.2283 | **4.4203** |
| 2017 | rank32/gamma2 | 3.6281 | rank16/gamma4 | 2.5550 | **1.0732** |
| 2018 | rank8/gamma2 | 2.5450 | rank32/gamma4 | 2.3571 | 0.1879 |
| 2019 | rank8/gamma2 | 2.8427 | rank32/gamma0.5 | 2.6144 | 0.2283 |
| 2020 | rank8/gamma2 | 2.7553 | rank32/gamma0.5 | 2.4048 | 0.3505 |
| 2021 | rank32/gamma2 | 2.7494 | rank16/gamma4 | 2.4168 | 0.3326 |

The oracle geometry changes sharply through time: rank8/gamma4, rank16/gamma4, rank32/gamma4, rank32/gamma0.5, rank32/gamma0.5, then rank16/gamma4. By contrast, expanding historical selection repeatedly favors gamma multiplier 2. This mismatch is strong evidence that **historical average predictive performance is not a stable proxy for next-year optimal environmental geometry**.

## Scientific interpretation

B10-S falsifies an attractive but unsupported idea: that the B10-R geometry sensitivity can be solved simply by nested chronological hyperparameter selection.

The correct conclusion is:

> Environmental spectral geometry is temporally nonstationary enough that expanding-window historical yield performance does not reliably select the next deployment year's T2 representation.

This is more informative than a failed model leaderboard. It separates three distinct concepts:

1. **Oracle information exists:** B10-R shows that some T2 geometries can perform very well after seeing the held-out outcome.
2. **Historical selection is inadequate:** B10-S shows that prior-year predictive performance does not identify those geometries prospectively.
3. **A safe controller therefore cannot be based on ordinary expanding-window CV alone.**

The result strengthens the project's central decision-system principle: information availability and model flexibility are not sufficient. The system also needs a deployment-stable criterion for whether a representation is admissible before the biological outcome is known.

## What B10-S does not establish

B10-S does not establish:

- that adaptive environmental geometry is impossible;
- that gamma multiplier 2 is intrinsically bad;
- that rank 8 or rank 32 should be rejected;
- that the B10-R oracle configurations were prospectively attainable;
- that temporal nonstationarity has a single biological cause;
- a support threshold or abstention rule;
- a production T1/T2 controller;
- live prospective field performance.

The negative result specifically rejects **this expanding-window outcome-based geometry-selection rule** under the frozen B9/B10 design.

## Reproducibility

```bash
python -m plant_intelligence.data.maize_environment_transfer --output-root .
python -m plant_intelligence.models.maize_training_only_geometry_selection --output-root .
```

Primary evidence:

- `reports/results/case_study_b10s_inner_chronological_evidence.csv`
- `reports/results/case_study_b10s_selection_audit.csv`
- `reports/results/case_study_b10s_forward_summary.csv`
- `reports/results/case_study_b10s_forward_year_metrics.csv`
- `reports/results/case_study_b10s_environment_metrics.csv`
- `reports/results/case_study_b10s_paired_bootstrap.csv`
- `reports/results/case_study_b10s_b10_reproduction_audit.csv`
- `reports/results/case_study_b10s_oracle_regret.csv`
- `reports/figures/case_study_b10s_training_only_geometry.png`
