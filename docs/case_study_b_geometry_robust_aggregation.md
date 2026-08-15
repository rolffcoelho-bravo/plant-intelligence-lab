# Case Study B10-U — Geometry-Agnostic Robust T2 Aggregation

## Purpose

B10-U is the stopping experiment for the T2 adaptive-geometry branch.

B10-R showed that the 60-DAP forecast-time-safe state can contain useful signal but is highly sensitive to environmental spectral geometry. B10-S showed that expanding-window historical performance does not reliably select the next year's geometry. B10-T then showed that geometry rankings themselves are not sufficiently persistent across forward years.

B10-U therefore stops trying to identify a single winning geometry. Instead, it asks whether uncertainty over the already frozen B10-R geometry family can be diversified away through two fully symmetric, predeclared aggregation rules.

No geometry is selected or weighted from held-out yield.

## Frozen aggregation design

The candidate family is exactly the 12 B10-R T2 geometries:

\[
r_E \in \{8,16,32\}, \qquad \gamma \in \{0.5,1,2,4\}.
\]

Genomic rank remains 20, ridge alpha remains 10, the B9 T2 issuance state remains fixed at 60 DAP, and the forward-year test years remain 2016–2021.

For each held-out genotype-environment cell, B10-U computes all 12 T2 predictions and then applies only:

\[
\hat y^{mean}_{T2}=\frac{1}{12}\sum_{g=1}^{12}\hat y_g,
\]

and

\[
\hat y^{median}_{T2}=\operatorname{median}(\hat y_1,\ldots,\hat y_{12}).
\]

There are no learned ensemble weights, no geometry ranking, no outcome-based admission rule, and no post-result tuning.

Frozen B10 T1 and T2 are reproduced in the same outer partitions for exact paired comparison.

## Predeclared stopping rule

Before execution, the T2 branch was allowed to remain open only if at least one aggregate simultaneously:

1. had lower pooled RMSE than frozen T1;
2. had both environment-cluster and year-cluster paired 95% RMSE-difference intervals entirely below zero versus frozen T1; and
3. reduced both worst-year RMSE and across-year RMSE range relative to frozen T2.

If no aggregate satisfied all three conditions, the T2 adaptive branch would close for this dataset. No additional geometry search or optimized weighting is permitted after the result.

## Pooled forward-year results

| Model | RMSE | MAE | R² | Correlation |
|---|---:|---:|---:|---:|
| Frozen T1 | 2.6614 | 2.1510 | 0.0595 | 0.3405 |
| Frozen T2 | 3.2843 | 2.4859 | -0.4322 | 0.1977 |
| T2 equal mean of 12 | 2.5892 | 2.0899 | 0.1099 | 0.3838 |
| **T2 median of 12** | **2.5765** | **2.0839** | **0.1186** | **0.3978** |

Both aggregation rules repair most of the frozen-T2 failure. Relative to frozen T2, pooled RMSE falls by about 0.695 for the equal mean and 0.708 for the median.

The median aggregate also has the best pooled point estimate among the four predeclared models, about 0.0849 RMSE lower than frozen T1, roughly a 3.2% point improvement.

However, point performance is not the admission criterion.

## Paired uncertainty

### Aggregates versus frozen T1

| Comparison | Cluster | ΔRMSE aggregate − T1 | 95% interval | Improvement frequency |
|---|---|---:|---:|---:|
| Mean12 − T1 | environment | -0.0723 | [-0.1772, 0.0225] | 0.9315 |
| Mean12 − T1 | test year | -0.0723 | [-0.1825, 0.0784] | 0.8410 |
| Median12 − T1 | environment | **-0.0849** | **[-0.1712, 0.0042]** | **0.9670** |
| Median12 − T1 | test year | **-0.0849** | **[-0.1875, 0.0585]** | **0.8790** |

Both aggregates favor T2 aggregation in the point estimate, especially the median, but every 95% interval versus T1 still crosses zero.

Therefore neither aggregate establishes the predeclared robust improvement over T1.

### Aggregates versus frozen T2

| Comparison | Cluster | ΔRMSE aggregate − frozen T2 | 95% interval | Improvement frequency |
|---|---|---:|---:|---:|
| Mean12 − frozen T2 | environment | -0.6952 | [-1.1355, -0.3312] | 1.0000 |
| Mean12 − frozen T2 | test year | -0.6952 | [-1.9990, -0.0320] | 0.9960 |
| Median12 − frozen T2 | environment | **-0.7078** | **[-1.1786, -0.2951]** | **1.0000** |
| Median12 − frozen T2 | test year | **-0.7078** | **[-2.0353, -0.0108]** | **0.9880** |

Geometry aggregation therefore robustly repairs the specific frozen-T2 geometry failure. What it does not do is robustly establish superiority to the safer T1 reference.

## Forward-year behavior

| Test year | Frozen T1 | Frozen T2 | T2 Mean12 | T2 Median12 |
|---:|---:|---:|---:|---:|
| 2016 | 2.7275 | **6.6486** | 2.9200 | **2.4746** |
| 2017 | **2.2621** | 2.9975 | 2.4451 | 2.6953 |
| 2018 | 2.5527 | 2.5926 | **2.4962** | 2.5432 |
| 2019 | 2.9195 | 2.7464 | **2.6700** | 2.6953 |
| 2020 | 2.7452 | 2.5389 | 2.5272 | **2.5189** |
| 2021 | **2.4752** | 2.4619 | 2.5077 | 2.5102 |

The most important stability result is the disappearance of the catastrophic 2016 frozen-T2 failure. Median aggregation lowers 2016 RMSE from 6.6486 to 2.4746 without selecting a geometry from 2016 yield.

Across the six years, frozen T2 has a worst-year RMSE of 6.6486 and a year-RMSE range of 4.1867. Mean aggregation reduces these to 2.9200 and 0.4748. Median aggregation reduces them further to 2.6953 and 0.2208.

Thus geometry-agnostic aggregation clearly improves T2 stability.

The remaining problem is relative to T1: Mean12 beats T1 in three of six years, and Median12 beats T1 in four of six. Median12 is still 0.4332 RMSE worse than T1 in its largest unfavorable year, 2017. This heterogeneity is why the pooled point advantage does not pass the locked bootstrap criterion.

## Stopping decision

The machine-readable decision is:

`CLOSE_T2_ADAPTIVE_BRANCH_USE_SUPPORTED_T1`

for both aggregates.

The reason is precise:

- **catastrophic-instability repair:** passed for both aggregates;
- **pooled point improvement over T1:** present for both aggregates;
- **robust 95% paired improvement over T1 under both cluster views:** not established;
- **aggregate admitted:** no;
- **post-result tuning permitted:** no.

This closes the adaptive T2 geometry branch for this dataset under the predeclared rule.

The conclusion should not be paraphrased as "T2 contains no useful information." B10-U demonstrates the opposite: aggregating across representation uncertainty recovers substantial signal and removes the catastrophic frozen-geometry failure. The narrower conclusion is that the available evidence does not justify replacing the T1 reference with a T2 aggregate in deployment.

## Scientific interpretation

B10-U provides a useful resolution to the B10-R/B10-S/B10-T sequence.

The main failure was not simply insufficient T2 information. It was excessive dependence on a single unstable representation. Symmetric aggregation over the fixed geometry family produces a much more stable predictor and strongly outperforms the failed frozen T2 geometry.

This supports a general methodological principle:

> Representation uncertainty can sometimes be diversified even when representation selection is temporally unstable.

But the project also preserves the stricter deployment principle:

> A repaired model is not automatically an admitted model. The repaired T2 representation must still demonstrate reliable advantage over the simpler supported decision horizon.

For this dataset, it does not yet meet that standard.

## Biological interpretation

The 60-DAP environmental trajectory should not be described as biologically harmful. B10-U shows that it can carry useful predictive information when spectral-geometry risk is diversified.

At the same time, the gain is not sufficiently consistent across forward years to justify waiting for or relying on T2 instead of T1 under the locked evidence standard. In particular, 2017 remains a clear counterexample where T1 is materially better than either aggregate.

The decision-system lesson is therefore about reliability rather than information quantity:

\[
\text{more biological/environmental information}
\not\Rightarrow
\text{better deployable decision}.
\]

Representation uncertainty and temporal heterogeneity must be accounted for explicitly.

## Boundary of the branch closure

The B10-U stopping result applies to this dataset, these forecast-time states, this fixed 12-geometry family, and this forward-year design.

It does not establish that:

- T2 information has no scientific value;
- model averaging can never improve over T1 in another dataset;
- all ensemble or distributional approaches are invalid;
- a future independent dataset could not validate the Median12 point advantage;
- the median aggregate is a prospectively validated champion;
- optimized or learned ensemble weights should now be tried on these same six years;
- a neural network should be introduced to rescue the branch;
- T1 is universally superior to T0, since B10 found those earlier horizons nearly tied in pooled performance.

The key governance consequence is methodological rather than administrative: **no additional post-hoc T2 geometry tuning should be performed on these same forward years.**

## Reproducibility

```bash
python -m plant_intelligence.data.maize_environment_transfer --output-root .
python -m plant_intelligence.models.maize_geometry_robust_aggregation --output-root .
```

Primary compact evidence:

- `reports/results/case_study_b10u_summary.csv`
- `reports/results/case_study_b10u_forward_year_metrics.csv`
- `reports/results/case_study_b10u_environment_metrics.csv`
- `reports/results/case_study_b10u_paired_bootstrap.csv`
- `reports/results/case_study_b10u_instability_audit.csv`
- `reports/results/case_study_b10u_b10_reproduction_audit.csv`
- `reports/results/case_study_b10u_branch_decision.csv`
- `reports/figures/case_study_b10u_robust_aggregation.png`
