# Case Study B9 — Prospective Environmental-State Reconstruction

## Purpose

Step B9 converts the deployment limitation exposed by B8 into an explicit forecast-time input contract. B8 showed that the retrospective environmental representation becomes substantially more predictive only after later-stage information enters, but the source ECOV matrix was generated with APSIM phenology aligned to observed year-location silking. B9 therefore does **not** fit another predictor. It reconstructs environmental states from information that can be bounded by an issuance date and freezes the validation design before any B9 forecasting model is fitted.

The central rule is

\[
\boxed{X(T)\text{ may contain no information realized after forecast issuance }T.}
\]

B9 also preserves the existing B5 genotype/environment cold-start manifests so the next modeling stage can compare the new prospective-input representation with the earlier continuous-environment program without rewriting the original validation problem.

## Public data sources

B9 combines four public data layers.

| Layer | Role in B9 |
|---|---|
| Curated Genomes-to-Fields maize data | environment identity, planting metadata, phenotype/genotype linkage, and the already locked B5 validation manifests |
| QuantGen/MAIZE-HUB historical metadata | year-location metadata and coordinate/planting-date reconciliation; repository commit is pinned |
| NASA POWER Daily API | date-stamped daily weather reconstructed from 2000 through the study year |
| USDA-NRCS Soil Data Access / SSURGO | static point map-unit and dominant-component soil descriptors |

The pinned MAIZE-HUB commit is `0385ac0f705eec9f4df41873467ed388e878bd1f`. The downloaded historical metadata archive is also recorded by SHA-256 in the B9 audit.

## Executed data audit

| Component | Verified result |
|---|---:|
| G2F year-location environments | **136** |
| Study years | **8 (2014–2021)** |
| Planting-date coverage | **100%** |
| Coordinate coverage | **100%** |
| Unique weather coordinates | **113** |
| NASA POWER weather missing fraction | **0.0** |
| SSURGO point-query coverage | **100%** |
| Locked forecast horizons | **3** |
| Safe environment-state rows | **408** |
| Future-weather violations | **0** |
| Observed-phenology violations | **0** |
| Forward-year test environments | **113** |
| Forward-year scenarios | **6** |

The 113 unique weather coordinates arise because several G2F environment labels resolve to the same physical coordinate. Static soil queries are therefore keyed to unique coordinates rather than environment labels.

## Forecast-time-safe horizons

B9 locks three issuance states before any new model fitting.

### T0 — pre-season

`T0_preseason` contains no realized weather from the target year. Weather information is a prior-year climatology formed from up to ten earlier years around the planting-season calendar window. Static soil information and planting/management metadata known at issuance may also be admitted.

\[
X_{T_0}=
[G,\;W_{history},\;S,\;M_{known}].
\]

### T1 — 30 days after planting

`T1_30DAP` adds realized daily weather only from planting through 30 days after planting.

\[
X_{T_1}=X_{T_0}\oplus W_{planting:T_1}.
\]

No day later than the issuance date may enter the state.

### T2 — 60 days after planting

`T2_60DAP_reproductive_window_proxy` adds realized daily weather only from planting through 60 days after planting.

\[
X_{T_2}=X_{T_0}\oplus W_{planting:T_2}.
\]

The name is deliberately explicit: **60 DAP is a fixed calendar-time proxy, not an observed flowering, anthesis, or silking event.** No observed phenology is used to define this boundary.

## Weather representation

The locked NASA POWER variables are:

- mean air temperature (`T2M`);
- minimum and maximum air temperature (`T2M_MIN`, `T2M_MAX`);
- corrected precipitation (`PRECTOTCORR`);
- surface shortwave radiation (`ALLSKY_SFC_SW_DWN`);
- relative humidity (`RH2M`);
- 2-m wind speed (`WS2M`).

The public raw daily downloads remain excluded from Git. B9 publishes compact source and coverage audits plus the final issuance-safe environment-state table.

## Explicitly forbidden variables

The B9 provenance audit identifies phenotype or future-phenology fields and forbids them from every issuance state. The excluded fields include observed yield, harvest date, anthesis, silking, ASI, and their derived growing-degree-day fields.

The safety contract is therefore stronger than the B8 retrospective horizon proxy:

\[
\boxed{
\text{no observed yield}
\;\oplus\;
\text{no observed future phenology}
\;\oplus\;
\text{no future realized weather}
}
\]

## Validation lock

B9 preserves the B5 environment and genotype manifests **unchanged** and registers a separate chronological stress test before any new B9 model is fitted.

| Validation | State |
|---|---|
| B5 CV-E | preserved unchanged |
| B5 CV-GE | preserved unchanged |
| B9 forward-year | registered before modeling |

The forward-year rule is

\[
\max(year_{train})<year_{test}.
\]

Six chronological scenarios are frozen:

| Test year | Training years | Test environments |
|---:|---|---:|
| 2016 | 2014–2015 | 18 |
| 2017 | 2014–2016 | 18 |
| 2018 | 2014–2017 | 21 |
| 2019 | 2014–2018 | 21 |
| 2020 | 2014–2019 | 16 |
| 2021 | 2014–2020 | 19 |

This gives **113** year-location tests under a genuine train-on-past, evaluate-on-later-year rule.

## What B9 establishes

B9 establishes that the project now has a reproducible environmental input substrate in which forecast-time boundaries are explicit and machine-auditable. It does **not** establish prediction performance.

The published source audit intentionally records:

`NONE_B9_IS_DATA_AND_VALIDATION_LOCK`

as the prediction-performance claim.

The distinction is important. B9 is a successful data and validation lock if the inputs are reproducible, coverage is sufficient, temporal leakage is absent, and the future evaluation design is frozen. Whether those inputs actually improve prediction is a separate empirical question for the next stage.

## Deployment boundary

B9 is still a **retrospective backtest reconstruction**, not a live prospective field trial. NASA POWER observations are retrieved historically and then truncated to the issuance date. They are not archived weather forecasts that would have been available before the future weather occurred. T1 and T2 therefore represent **observed-to-date** in-season states, not forecasted future weather.

Similarly, the SSURGO layer is a public static soil-map representation at the resolved coordinate. It is not a plot-level laboratory soil assay, and map-derived soil information should not be interpreted as exact within-field measurements.

The forward-year split is a materially stronger deployment stress than shuffled year-location folds, but it remains historical backtesting. Prospective performance can only be claimed after recommendations or predictions are generated before the corresponding future outcomes are observed.

## Reproducibility

Implementation:

`src/plant_intelligence/data/maize_prospective_environment.py`

Tests:

`tests/test_case_study_b9_prospective_environment.py`

Workflow:

`.github/workflows/case-study-b9-prospective-environment.yml`

Published evidence:

- `reports/results/case_study_b9_source_audit.csv`
- `reports/results/case_study_b9_environment_manifest.csv`
- `reports/results/case_study_b9_power_weather_audit.csv`
- `reports/results/case_study_b9_ssurgo_audit.csv`
- `reports/results/case_study_b9_safe_environment_states.csv`
- `reports/results/case_study_b9_horizon_lock.csv`
- `reports/results/case_study_b9_feature_provenance.csv`
- `reports/results/case_study_b9_forward_year_folds.csv`
- `reports/results/case_study_b9_validation_lock.csv`
- `reports/figures/case_study_b9_input_coverage.png`

The next modeling stage must consume these frozen states and manifests without redefining the horizons after seeing prediction results.
