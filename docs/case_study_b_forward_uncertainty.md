# Case Study B11 — Forward-Time Uncertainty Calibration and Selective Prediction

## Question

After B10-U closed the adaptive T2 geometry branch, B11 asks a narrower deployment question:

> **Can the supported 30-DAP T1 predictor be accompanied by uncertainty estimates and a reliability state using only information available before the forecast year?**

B11 does not fit a new prediction model. It freezes the B10 `G+E_T1` predictor and adds a chronological residual-calibration layer plus outcome-free environmental-support diagnostics.

## Frozen predictor and chronology

The predictive model is unchanged from B10:

- predictor: `G+E_T1`;
- horizon: `T1_30DAP`;
- genomic rank: 20;
- environmental rank: 16;
- environmental RBF gamma multiplier: 2.0;
- ridge alpha: 10.0.

The B9 forward-year manifest remains frozen. B11 exactly reproduces the six published B10 T1 RMSE values with absolute difference `0.0` for every year.

For a target year \(t\), calibration residuals obey

\[
\mathcal C_t \subset \{ |Y-\hat Y| : \text{forward validation year}<t \}.
\]

The current test year and all future years are excluded. A minimum of two earlier forward-validation years is required. Consequently:

| Test year | Calibration state | Prior calibration years | Calibration cells | Calibration environments |
|---|---|---:|---:|---:|
| 2016 | `INSUFFICIENT_CALIBRATION_HISTORY` | 0 | 0 | 0 |
| 2017 | `INSUFFICIENT_CALIBRATION_HISTORY` | 1 | 4,562 | 18 |
| 2018 | available | 2 | 7,871 | 36 |
| 2019 | available | 3 | 18,462 | 57 |
| 2020 | available | 4 | 29,371 | 78 |
| 2021 | available | 5 | 36,086 | 94 |

This is intentional. B11 does not manufacture an interval when the forward calibration history is too short.

## Interval construction

B11 reports two predeclared constructions using finite-sample absolute-residual quantiles.

### Global forward calibration

`GLOBAL_FORWARD` uses all eligible residuals from earlier forward years.

### Support-adaptive calibration

`SUPPORT_ADAPTIVE` may calibrate within an outcome-free T1 environmental-support stratum when that stratum has at least five historical environments and 200 residual cells. Otherwise it falls back to the global chronological quantile.

The support boundary uses the nearest-environment distance percentile relative to the current training set. It does not use yield. `AT_OR_BEYOND_TRAINING_NN_ENVELOPE` is reserved for a test environment at or beyond the maximum internal nearest-neighbour spacing of the current training environments.

In the four interval-eligible forward years, all 77 evaluated environments remained within that envelope. Therefore the support-adaptive intervals reduce exactly to the global chronological intervals in this dataset. This is evidence against inventing a support-conditioned calibration benefit where none was observed.

## Forward coverage

The interval-eligible evaluation contains **36,445 prediction cells**, **77 environments**, and **four forward test years (2018–2021)**.

| Method | Nominal | Empirical coverage | Environment-balanced coverage | Environment-cluster 95% interval | Mean interval width |
|---|---:|---:|---:|---:|---:|
| Global forward | 80% | 77.54% | 76.35% | [72.59%, 81.89%] | 6.704 |
| Support-adaptive | 80% | 77.54% | 76.35% | [72.62%, 81.79%] | 6.704 |
| Global forward | 90% | 88.58% | 87.47% | [85.05%, 91.45%] | 8.503 |
| **Support-adaptive** | **90%** | **88.58%** | **87.47%** | **[85.09%, 91.54%]** | **8.503** |
| Global forward | 95% | 94.47% | 93.92% | [92.38%, 96.25%] | 10.108 |
| Support-adaptive | 95% | 94.47% | 93.92% | [92.42%, 96.23%] | 10.108 |

The predeclared B11 admission check is satisfied for the 90% interval: empirical coverage is within three percentage points of nominal and the environment-cluster interval contains 90%. The machine decision is:

`ADMIT_FORWARD_INTERVALS_KEEP_SUPPORT_ABSTENTION_DIAGNOSTIC`

This admits the **forward residual-calibration layer**, not a universal conformal guarantee and not a hard environmental abstention rule.

## Year-to-year calibration behavior

Coverage is not constant through time.

| Test year | 80% coverage | 90% coverage | 95% coverage |
|---|---:|---:|---:|
| 2018 | 76.65% | 89.85% | 96.41% |
| 2019 | 72.44% | **83.47%** | 90.37% |
| 2020 | 77.68% | 89.22% | 95.44% |
| 2021 | 85.35% | **93.20%** | 96.62% |

The 2019 undercoverage is important. Pooled calibration close to nominal does not erase temporal heterogeneity. B11 therefore remains a forward-time retrospective backtest, not a claim that interval coverage is invariant under future distribution shift.

## Environmental support and abstention

The outcome-free nearest-neighbour support rule abstains on **zero** of the 77 interval-eligible environments. Every evaluated environment is inside the current training nearest-neighbour envelope.

Accordingly:

- all evaluated predictions are `RETAIN_SUPPORTED`;
- no `ABSTAIN_LOW_ENVIRONMENT_SUPPORT` performance estimate can be made;
- support-based abstention is **not admitted**;
- the reliability rule remains diagnostic until an independent forward block contains genuinely low-support environments.

This is preferable to choosing a threshold after looking at errors.

## Selective-risk diagnostic

B11 also asks whether retaining only the environments with the smallest outcome-free support distance improves prediction. It does not.

| Target environment retention | Realized cell retention | RMSE | 90% coverage |
|---:|---:|---:|---:|
| 100% | 100.00% | **2.6865** | **88.58%** |
| 95% | 98.31% | 2.6988 | 88.43% |
| 90% | 91.28% | 2.7143 | 88.22% |
| 80% | 76.87% | 2.7843 | 87.15% |
| 70% | 67.87% | 2.7957 | 86.68% |

Removing nominally lower-support environments actually worsens RMSE and coverage in this retrospective diagnostic. Therefore environmental distance is not promoted as an abstention score.

## Support/error associations

At the environment-year level (77 observations), no tested issuance-time support signal has a strong descriptive relationship with T1 RMSE:

| Signal | Spearman \(\rho\) with environment RMSE |
|---|---:|
| T1 full nearest-distance percentile | 0.0897 |
| Maximum training-kernel similarity | -0.0844 |
| Weather nearest-distance percentile | -0.0536 |
| Nearest training location distance | -0.0340 |
| 90% interval half-width | -0.0041 |

These are descriptive associations, not causal tests. The main finding is negative but useful: **the currently available support geometry is not a reliable difficulty-ranking variable for the supported T1 predictor.**

## Scientific interpretation

B11 separates two questions that should not be conflated:

1. **Can forecast uncertainty be calibrated from prior forward residuals?**  Yes, sufficiently well for the predeclared 90% admission check on the 2018–2021 backtest.
2. **Can the current environmental-support geometry identify when to abstain?**  No. The hard boundary was never reached, and progressively filtering by the softer distance ranking worsened rather than improved risk.

The practical architecture is therefore

\[
G+E_{T1}\rightarrow \hat Y\rightarrow \text{forward residual interval}\rightarrow \text{support diagnostic},
\]

with the interval layer admitted and the support-based abstention layer still diagnostic.

## Boundaries

B11 does **not** establish:

- live prospective field coverage;
- exchangeability across future years or environments;
- a causal connection between environmental distance and prediction error;
- a validated low-support abstention threshold;
- that support-adaptive calibration is better than global calibration in this dataset;
- that 2016 or 2017 had valid forward intervals;
- that the T2 branch may be reopened;
- that post-result tuning is permitted.

The T2 adaptive branch remains closed. The B11 result changes only the reliability layer around the frozen T1 reference.

## Reproducibility

Implementation:

- `src/plant_intelligence/uncertainty/maize_forward_uncertainty.py`
- `tests/test_case_study_b11_forward_uncertainty.py`
- `.github/workflows/case-study-b11-forward-uncertainty.yml`

Published evidence:

- `reports/results/case_study_b11_calibration_audit.csv`
- `reports/results/case_study_b11_coverage_by_year.csv`
- `reports/results/case_study_b11_coverage_summary.csv`
- `reports/results/case_study_b11_support_conditioned_coverage.csv`
- `reports/results/case_study_b11_reliability_summary.csv`
- `reports/results/case_study_b11_selective_risk.csv`
- `reports/results/case_study_b11_support_error_association.csv`
- `reports/results/case_study_b11_branch_decision.csv`
- `reports/results/case_study_b11_b10_t1_reproduction_audit.csv`
- `reports/figures/case_study_b11_forward_coverage.png`
- `reports/figures/case_study_b11_selective_risk.png`
