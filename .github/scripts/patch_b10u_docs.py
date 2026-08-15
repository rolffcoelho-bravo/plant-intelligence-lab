from pathlib import Path

readme = Path('README.md')
text = readme.read_text(encoding='utf-8')
marker = 'Detailed Case Study B evidence:'
if '## B10-U — Geometry-agnostic robust T2 aggregation' not in text:
    section = '''## B10-U — Geometry-agnostic robust T2 aggregation

B10-U is the locked stopping experiment for the T2 adaptive-geometry branch. Instead of trying to identify one temporally unstable geometry, it symmetrically aggregates the exact 12 frozen B10-R T2 predictions using only two predeclared rules: an equal arithmetic mean and a coordinate-wise median. There are **no learned ensemble weights, no geometry selection, and no post-result tuning**.

| Forward model | RMSE | $R^2$ | Correlation |
|---|---:|---:|---:|
| Frozen T1 | 2.6614 | 0.0595 | 0.3405 |
| Frozen T2 | 3.2843 | -0.4322 | 0.1977 |
| T2 Mean12 | 2.5892 | 0.1099 | 0.3838 |
| **T2 Median12** | **2.5765** | **0.1186** | **0.3978** |

Aggregation repairs the frozen-T2 collapse. Median12 lowers pooled RMSE by **0.7078** versus frozen T2 and reduces the worst forward-year RMSE from **6.6486** to **2.6953**. Mean12 shows the same qualitative stabilization.

However, the predeclared admission rule requires robust superiority to frozen T1, not only repair of frozen T2. Median12 has a favorable point difference of **-0.0849 RMSE** versus T1, but its environment-cluster 95% interval is **[-0.1712, 0.0042]** and its six-year cluster interval is **[-0.1875, 0.0585]**. Mean12 likewise crosses zero in both views.

Therefore neither aggregate is admitted. The machine decision is:

`CLOSE_T2_ADAPTIVE_BRANCH_USE_SUPPORTED_T1`

This closure is deliberately narrow. It does **not** mean that T2 contains no useful signal: geometry aggregation clearly recovers signal and removes catastrophic representation failure. It means that, on these same locked forward years, the repaired T2 representation still does not establish a reliable advantage over the safer T1 reference. No further post-hoc T2 geometry tuning is permitted on this dataset.

![Case Study B10-U robust T2 aggregation](reports/figures/case_study_b10u_robust_aggregation.png)

'''
    text = text.replace(marker, section + marker, 1)

b10t = '- [`docs/case_study_b_temporal_geometry_stability.md`](docs/case_study_b_temporal_geometry_stability.md) — B10-T year-to-year geometry ranking persistence and lagged-winner regret'
b10u = '- [`docs/case_study_b_geometry_robust_aggregation.md`](docs/case_study_b_geometry_robust_aggregation.md) — B10-U symmetric T2 aggregation and locked branch-closing decision'
if b10t in text and b10u not in text:
    text = text.replace(b10t, b10t + '\n' + b10u, 1)

validation = 'B10-T then audits whether the geometry ranking itself is temporally persistent and rejects rank persistence as a sufficient basis for a T2 controller.'
if validation in text and 'B10-U finally tests whether representation uncertainty can be diversified' not in text:
    text = text.replace(validation, validation + ' B10-U finally tests whether representation uncertainty can be diversified without selecting a geometry; aggregation repairs frozen T2 but does not robustly beat T1, so the adaptive T2 branch closes under its locked stopping rule.', 1)

wf = '- `case-study-b10t-temporal-stability.yml` — temporal geometry ranking, Top-k persistence, lagged-winner regret, and outcome-free shift audit.'
if wf in text and 'case-study-b10u-robust-aggregation.yml' not in text:
    text = text.replace(wf, wf + '\n- `case-study-b10u-robust-aggregation.yml` — equal-mean/median T2 geometry aggregation and predeclared stopping decision.', 1)

cmd = 'python -m plant_intelligence.models.maize_geometry_temporal_stability --output-root .'
if cmd in text and 'maize_geometry_robust_aggregation' not in text:
    text = text.replace(cmd, cmd + '\npython -m plant_intelligence.models.maize_geometry_robust_aggregation --output-root .', 1)

limit = '- that the strongest B10-T outcome-free shift correlation defines a biological mechanism or threshold: those associations are descriptive small-n diagnostics only;'
if limit in text and 'B10-U proves the median T2 aggregate is a deployment champion' not in text:
    text = text.replace(limit, limit + '\n- that B10-U proves the median T2 aggregate is a deployment champion: its pooled point estimate is favorable but both paired 95% cluster intervals versus T1 cross zero;\n- that B10-U shows T2 information is useless: symmetric aggregation robustly repairs the frozen-T2 failure, but the predeclared stopping rule still closes the adaptive T2 branch because superiority to T1 is not established;\n- that further optimized T2 ensemble weights should be fitted on these same forward years: B10-U explicitly forbids post-result tuning after the stopping decision;', 1)

see = '[`docs/case_study_b_temporal_geometry_stability.md`](docs/case_study_b_temporal_geometry_stability.md) for the detailed boundaries.'
if see in text:
    text = text.replace(see, '[`docs/case_study_b_temporal_geometry_stability.md`](docs/case_study_b_temporal_geometry_stability.md), and [`docs/case_study_b_geometry_robust_aggregation.md`](docs/case_study_b_geometry_robust_aggregation.md) for the detailed boundaries.', 1)

docline = '- [`docs/case_study_b_forecast_time_prediction.md`](docs/case_study_b_forecast_time_prediction.md) — B10 forecast-time prediction, Value of Waiting, and forward-support diagnostics'
if docline in text and '— B10-U robust geometry aggregation' not in text:
    extra = '''- [`docs/case_study_b_forward_support_diagnostics.md`](docs/case_study_b_forward_support_diagnostics.md) — B10-R support and spectral-geometry diagnosis
- [`docs/case_study_b_training_only_geometry_selection.md`](docs/case_study_b_training_only_geometry_selection.md) — B10-S training-only geometry-selection test
- [`docs/case_study_b_temporal_geometry_stability.md`](docs/case_study_b_temporal_geometry_stability.md) — B10-T temporal ranking-stability audit
- [`docs/case_study_b_geometry_robust_aggregation.md`](docs/case_study_b_geometry_robust_aggregation.md) — B10-U robust geometry aggregation and branch closure'''
    text = text.replace(docline, docline + '\n' + extra, 1)

readme.write_text(text, encoding='utf-8')

limitations = Path('docs/limitations.md')
limits = limitations.read_text(encoding='utf-8')
marker = '## Uncertainty calibration'
if '## B10-U geometry aggregation and stopping boundary' not in limits:
    section = '''## B10-U geometry aggregation and stopping boundary

B10-U is a finite stopping experiment, not an invitation to optimize an ensemble after observing the six forward years. It aggregates exactly the 12 previously frozen B10-R T2 geometries by equal mean and coordinate-wise median. No member receives an outcome-trained weight and no geometry is selected for an outer year.

Both aggregates materially repair the frozen-T2 representation failure and dramatically reduce its worst-year instability. The median aggregate also has the best pooled point RMSE among the predeclared B10-U models. However, the paired environment-cluster and test-year-cluster 95% intervals for both aggregates versus frozen T1 cross zero. Under the predeclared rule, neither aggregate is admitted and the machine decision is `CLOSE_T2_ADAPTIVE_BRANCH_USE_SUPPORTED_T1`.

This decision must not be rephrased as evidence that T2 contains no useful environmental information. B10-U shows that representation uncertainty can be diversified and that the frozen-T2 collapse is not intrinsic to the 60-DAP information state. The narrower conclusion is that the repaired T2 signal does not establish sufficiently reliable superiority to the T1 reference on these forward years.

The branch closure also means that learned stacking weights, another geometry grid, additional post-hoc thresholds, or a neural ensemble should not now be fitted to these same six years to rescue T2. An independent future block or dataset could test the already frozen Median12 rule, but that would be a new validation stage rather than continued tuning of this evidence.

T1 should be understood here as the supported reference horizon for the T2 branch, not as proof of universal superiority over T0. In B10, T0 and T1 were nearly tied in pooled forward-year performance.

'''
    limits = limits.replace(marker, section + marker, 1)
limitations.write_text(limits, encoding='utf-8')
