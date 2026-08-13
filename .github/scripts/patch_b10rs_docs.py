from pathlib import Path

readme=Path('README.md')
text=readme.read_text(encoding='utf-8')
marker='Detailed Case Study B evidence:'
if '## B10-R — Support-aware forward-time geometry diagnosis' not in text:
    section='''## B10-R — Support-aware forward-time geometry diagnosis

B10-R diagnoses the B10 T2 failure without changing the B9 horizons or promoting a post-hoc champion. Across 113 held-out environments, lower maximum training-kernel similarity and greater weather-space distance are associated with larger T2-minus-T1 error. The severe 2016 collapse is highly sensitive to environmental rank/bandwidth: the frozen rank-16/gamma-2 T2 model has RMSE 6.6486, while diagnostic-only alternatives reach roughly 2.23. However, 2017 remains worse than T1 across the tested geometry neighborhood, so the result is not reducible to one bad hyperparameter choice.

The defensible conclusion is that later environmental information is **conditionally usable**: deployment risk depends jointly on historical support, spectral representation, and year-specific environmental state. The B10-R grid is diagnostic only and is not admitted for deployment selection.

![Case Study B10-R support diagnostic](reports/figures/case_study_b10r_support_diagnostic.png)

## B10-S — Training-only forward geometry selection

B10-S asks whether the B10-R oracle insight can be converted into a valid selection rule using only earlier years. The candidate grid is frozen to the same 12 B10-R geometries. For outer year `t`, each candidate is scored only on chronological inner years `y < t`, and each inner year itself uses training years `< y`. The outer-year outcome is never used. Because 2016 has only one usable inner validation year, it is explicitly classified as `INSUFFICIENT_HISTORY_FALLBACK` and retains the frozen B10 geometry.

| Forward model | RMSE | $R^2$ | Correlation |
|---|---:|---:|---:|
| Frozen T1 | **2.6614** | **0.0595** | **0.3405** |
| Frozen T2 | 3.2843 | -0.4322 | 0.1977 |
| **Training-only selected T2** | **3.4095** | **-0.5435** | **0.1457** |

The result is deliberately preserved as a **negative finding**. Training-only expanding-window selection makes T2 worse than frozen T2 by **0.1252 RMSE**; the environment-cluster 95% interval is **[0.0303, 0.2323]**, and the six-year cluster interval is **[0.0231, 0.2865]**. It is also materially worse than frozen T1. Historical average predictive performance therefore does not reliably identify the next deployment year's best environmental spectral geometry.

This blocks a naive adaptive T2 controller. The next methodological question is temporal stability: whether geometry rankings themselves are persistent enough to support any prospective selector.

![Case Study B10-S training-only geometry selection](reports/figures/case_study_b10s_training_only_geometry.png)

'''
    text=text.replace(marker,section+marker,1)

b10='- [`docs/case_study_b_forecast_time_prediction.md`](docs/case_study_b_forecast_time_prediction.md) — B10 forward-year prediction, Value of Waiting, and support-failure evidence'
b10r='- [`docs/case_study_b_forward_support_diagnostics.md`](docs/case_study_b_forward_support_diagnostics.md) — B10-R support/spectral-geometry diagnosis'
b10s='- [`docs/case_study_b_training_only_geometry_selection.md`](docs/case_study_b_training_only_geometry_selection.md) — B10-S training-only selection and negative deployment result'
if b10 in text and b10r not in text:
    text=text.replace(b10,b10+'\n'+b10r+'\n'+b10s,1)

validation='B10 then consumes those frozen states with no new hyperparameter search and makes the chronological forward-year benchmark primary.'
if validation in text and 'B10-R then diagnoses' not in text:
    text=text.replace(validation,validation+' B10-R then diagnoses the T2 support/geometry failure without selecting a replacement model. B10-S finally converts that diagnostic grid into a strictly training-only expanding-window selection test and preserves its negative result when historical performance fails to transfer.',1)

wf='- `case-study-b10-forecast-time-prediction.yml` — frozen-horizon forward-year prediction and Value-of-Waiting benchmark.'
if wf in text and 'case-study-b10s-training-only-geometry.yml' not in text:
    text=text.replace(wf,wf+'\n- `case-study-b10r-support-diagnostics.yml` — support-aware forward-time environmental geometry diagnosis.\n- `case-study-b10s-training-only-geometry.yml` — training-only chronological T2 geometry-selection reproduction.',1)

cmd='python -m plant_intelligence.models.maize_forecast_time_prediction --output-root .'
if cmd in text and 'maize_training_only_geometry_selection' not in text:
    text=text.replace(cmd,cmd+'\npython -m plant_intelligence.models.maize_forward_support_diagnostics --output-root .\npython -m plant_intelligence.models.maize_training_only_geometry_selection --output-root .',1)

limit='- that the six-year forward bootstrap provides a precise year-level uncertainty distribution;'
if limit in text and 'B10-S proves adaptive geometry selection is impossible' not in text:
    text=text.replace(limit,limit+'\n- that B10-R establishes a deployable spectral geometry or validated support threshold: its rank/bandwidth grid is diagnostic and uses held-out outcomes only for explanation;\n- that B10-S proves adaptive geometry selection is impossible: it rejects the tested expanding-window outcome-based selector, not every possible training-only stability criterion;\n- that the B10-S oracle-regret table is a prospective benchmark: oracle configurations explicitly use outer-year outcomes and are never admitted for deployment;',1)

see='[`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md) for the detailed boundaries.'
if see in text:
    text=text.replace(see,'[`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md), [`docs/case_study_b_forward_support_diagnostics.md`](docs/case_study_b_forward_support_diagnostics.md), and [`docs/case_study_b_training_only_geometry_selection.md`](docs/case_study_b_training_only_geometry_selection.md) for the detailed boundaries.',1)
readme.write_text(text,encoding='utf-8')

p=Path('docs/limitations.md')
limits=p.read_text(encoding='utf-8')
marker='## Uncertainty calibration'
if '## B10-R and B10-S spectral-geometry boundary' not in limits:
    section='''## B10-R and B10-S spectral-geometry boundary

B10-R is a diagnostic analysis, not a post-hoc model promotion step. Its support measures are computed without yield, but its rank/bandwidth sensitivity grid is interpreted after observing held-out errors. The best diagnostic geometry therefore cannot be reported as a prospectively selected champion. The 2016 collapse is strongly geometry-sensitive, while the 2017 disadvantage persists across the tested grid; neither a single support variable nor kernel effective rank alone is established as the failure mechanism.

B10-S converts the same fixed grid into a genuinely training-only expanding-window selector. The outer-year outcome is excluded from selection, and 2016 is explicitly assigned an insufficient-history fallback. The selected T2 model nevertheless performs worse than both frozen T2 and frozen T1 in pooled forward-year prediction, with the selected-versus-frozen-T2 cluster intervals above zero. This rejects the tested historical-performance selector under the frozen design.

The B10-S result must not be generalized into a claim that adaptive geometry is impossible. It shows that expanding-window historical yield performance is not sufficiently deployment-stable here. Any future adaptive controller must be justified by a criterion that can be calculated before the outer outcome and whose temporal stability is demonstrated separately.

The oracle-regret audit remains explanatory only: its oracle configurations use the corresponding outer-year outcomes and are explicitly marked as not admitted for deployment.

'''
    limits=limits.replace(marker,section+marker,1)
p.write_text(limits,encoding='utf-8')
