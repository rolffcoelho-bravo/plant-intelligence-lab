# Case Study B — Step B4 Uncertainty, Reliability & Deployment Boundaries

## Purpose

Step B4 converts the frozen Case Study B predictors from point forecasts into an uncertainty-aware deployment assessment. It does **not** refit the predictive models or change the locked CV-G/CV2 validation design.

The frozen prediction sources are:

- **CV-G:** the normalized G×E mixture from Step B2-R, RMSE 0.890109;
- **CV2:** the pre-registered classical G+E+G×E model from Step B2, RMSE 0.846926.

The analysis asks four questions:

1. Are residual prediction intervals calibrated at 80%, 90%, and 95% coverage?
2. Does calibration remain stable across the four represented mega-environments?
3. Does genomic support distance identify harder unseen genotypes?
4. Which deployment regimes are scientifically supportable with categorical environments alone?

## Cross-fitted prediction intervals

Intervals are calibrated from absolute out-of-sample residuals. For a target coverage level \(c\), the finite-sample residual quantile is

\[
q_c = r_{(\lceil(n+1)c\rceil)},
\]

and the interval is

\[
[\hat y-q_c,\;\hat y+q_c].
\]

Calibration is environment-specific where sample size permits. Every evaluated observation excludes its own calibration fold from the residual pool. CV-G uses the locked genotype outer folds. CV2 uses deterministic genotype-only residual-calibration folds; these folds do not alter model fitting or hyperparameter selection.

### Pooled calibration

| Validation | Nominal | Empirical | Mean interval width | N |
|---|---:|---:|---:|---:|
| CV-G | 80% | **80.18%** | 2.210 | 2,396 |
| CV-G | 90% | **89.77%** | 2.919 | 2,396 |
| CV-G | 95% | **94.95%** | 3.660 | 2,396 |
| CV2 | 80% | **80.13%** | 2.124 | 599 |
| CV2 | 90% | **89.98%** | 2.854 | 599 |
| CV2 | 95% | **94.99%** | 3.462 | 599 |

The pooled empirical coverage tracks the nominal targets closely in both supported deployment regimes.

### Environment-specific 90% coverage

| Environment | CV-G | CV2 |
|---|---:|---:|
| ME1 | 89.82% | 90.67% |
| ME2 | 89.82% | 89.33% |
| ME3 | 89.82% | 90.00% |
| ME4 | 89.65% | 89.93% |

This is evidence of stable residual calibration across the represented categorical environments. It is not evidence that the same intervals remain calibrated in a genuinely new physical environment.

## Genomic-support diagnostic

For CV-G, every test genotype is unseen during model fitting. A support distance is therefore calculated in a training-only genomic PCA space. Standardization and PCA are fitted using only the outer-training genotypes, and each held-out genotype is assigned its nearest training-genotype distance.

The association with absolute forecast error is:

\[
\rho_{Spearman}=0.1008,
\qquad
p=7.63\times10^{-7}.
\]

The association is statistically detectable but **small in magnitude**. Genomic distance therefore contains some information about difficult unseen genotypes, but it is not strong enough to justify a hard standalone abstention threshold.

The 90% interval width itself has essentially no rank association with absolute error:

- CV-G: \(\rho=0.0019\), \(p=0.927\);
- CV2: \(\rho=0.0178\), \(p=0.663\).

This is an important negative result. The calibrated interval widths are useful for uncertainty coverage, but they are not individually reliable error-ranking scores in this dataset.

## Selective-risk diagnostic

Because the error-ranking signals are weak, Step B4 deliberately avoids declaring an operational in-support abstention rule. Instead, it reports retrospective selective-risk curves.

For CV-G, the exploratory risk score combines interval-width rank and genomic-distance rank. For CV2, only interval-width rank is available because the genotype itself is represented in training through its other environments.

| Validation | Retained fraction | RMSE | MAE |
|---|---:|---:|---:|
| CV-G | 100.0% | 0.8901 | 0.6886 |
| CV-G | 95.0% | 0.8846 | 0.6840 |
| CV-G | 90.0% | 0.8770 | 0.6794 |
| CV-G | 79.9% | 0.8607 | 0.6699 |
| CV2 | 100.0% | 0.8469 | 0.6536 |
| CV2 | 95.0% | 0.8463 | 0.6520 |
| CV2 | 90.0% | 0.8451 | 0.6475 |
| CV2 | 80.0% | 0.8227 | 0.6476 |

Removing approximately the highest-risk 20% retrospectively reduces RMSE by about 3.31% in CV-G and 2.86% in CV2. These curves are diagnostics, not a prospective abstention guarantee. Given the weak direct signal-error associations, the repository does not promote a fixed in-support abstention cutoff from this result alone.

## Deployment boundary

The strongest operational conclusion of Step B4 is representational rather than numerical.

| Regime | State | Interpretation |
|---|---|---|
| CV-G | **FORECAST_SUPPORTED** | Unseen genotype, but environment category was represented during training. |
| CV2 | **FORECAST_SUPPORTED** | Missing genotype×environment response with genotype observed in other represented environments. |
| CV-E | **UNSUPPORTED_ENVIRONMENT** | Held-out categorical environment lacks continuous descriptors that would allow similarity-based transfer. |
| CV-GE | **UNSUPPORTED_ENVIRONMENT** | Both genotype and categorical environment are unseen; environmental transfer cannot be inferred. |

The current model should therefore not silently convert CV-E or CV-GE stress-test outputs into operational forecasts. The appropriate state is

\[
\boxed{\text{UNSUPPORTED ENVIRONMENT}}
\]

until real transferable environmental covariates are available.

## Scientific interpretation

Step B4 establishes three distinct conclusions.

First, cross-fitted residual intervals are well calibrated for the two supported represented-environment deployment regimes.

Second, genomic support distance is associated with error for unseen genotypes, but only weakly. Interval width is not an effective error-ranking variable here. The evidence therefore supports uncertainty reporting but does not yet support an aggressive abstention policy within represented environments.

Third, the strict environmental cold-start problem is a representation problem. Four categorical labels contain no physical geometry that can connect an unseen environment to ME1–ME4. CV-E and CV-GE are therefore formalized as unsupported deployment states rather than weakly supported forecasts.

This preserves the central project principle: uncertainty should expose where the model is supported, and abstention should be evidence-driven rather than introduced as decoration.

## Reproducibility

Implementation:

`src/plant_intelligence/uncertainty/wheat_gxe_uncertainty.py`

Tests:

`tests/test_case_study_b_uncertainty.py`

Workflow:

`.github/workflows/case-study-b-uncertainty.yml`

Validated outputs:

- `reports/results/case_study_b_uncertainty_predictions.csv`
- `reports/results/case_study_b_uncertainty_coverage.csv`
- `reports/results/case_study_b_support_diagnostics.csv`
- `reports/results/case_study_b_selective_risk.csv`
- `reports/results/case_study_b_deployment_boundary.csv`
- `reports/figures/case_study_b_uncertainty_reliability.png`

The dedicated workflow completed successfully, including targeted tests, public-data rematerialization for training-only genomic-support diagnostics, result verification, and publication of the compact evidence.
