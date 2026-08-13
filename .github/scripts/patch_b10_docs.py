from pathlib import Path

p=Path('README.md')
t=p.read_text(encoding='utf-8')
t=t.replace('decision-horizon forecasting, prospective environmental-state reconstruction, and a grounded scientific interface','decision-horizon forecasting, prospective environmental-state reconstruction, Value-of-Waiting analysis, and a grounded scientific interface',1)
marker='Detailed Case Study B evidence:'
if '## B10 — Forecast-time-safe prediction and Value of Waiting' not in t:
    section='''## B10 — Forecast-time-safe prediction and Value of Waiting

B10 consumes the frozen B9 issuance-safe states with no new hyperparameter search:

$$
G \\rightarrow G+E_{T0} \\rightarrow G+E_{T1} \\rightarrow G+E_{T2}.
$$

The primary benchmark is the B9 forward-year lock, so every training year precedes its test year. B5 CV-E/CV-GE remain secondary continuity checks.

| Primary forward-year model | RMSE | $R^2$ | Correlation |
|---|---:|---:|---:|
| G | 2.7642 | -0.0145 | 0.2847 |
| **G+E_T0** | **2.6635** | 0.0581 | **0.3631** |
| G+E_T1 | 2.6614 | **0.0595** | 0.3405 |
| G+E_T2 | **3.2843** | **-0.4322** | **0.1977** |

T0 improves pooled RMSE over G by about **3.64%**, but its cluster intervals cross zero. Waiting from T0 to 30 DAP changes pooled RMSE by only **0.08%**. The key result is non-monotonic: waiting from 30 to 60 DAP makes pooled forward-year RMSE **23.4% worse** under the frozen representation.

The failure is concentrated in early forward backtests. In 2016, with only **23 prior training environments**, T2 RMSE reaches **6.6486**. The catastrophic behavior disappears as historical environmental support expands. B10 therefore identifies a **support-dependent transfer failure**, not evidence that 60-DAP weather is biologically harmful.

For `T2 - T1`, the environment-cluster 95% RMSE-difference interval is **[0.2082, 1.0774]** with zero bootstrap improvement frequency. The year-cluster interval is much wider and crosses zero because only six forward test years are available and the effect is strongly heterogeneous.

![Case Study B10 forecast-time-safe Value of Waiting](reports/figures/case_study_b10_value_of_waiting.png)

'''
    t=t.replace(marker,section+marker,1)
b9='- [`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md) — B9 forecast-time-safe input and forward-year validation lock'
b10='- [`docs/case_study_b_forecast_time_prediction.md`](docs/case_study_b_forecast_time_prediction.md) — B10 forward-year prediction, Value of Waiting, and support-failure evidence'
if b9 in t and b10 not in t: t=t.replace(b9,b9+'\n'+b10,1)
w9='- `case-study-b9-prospective-environment.yml` — forecast-time-safe weather/soil/management data and forward-year validation lock.'
w10='- `case-study-b10-forecast-time-prediction.yml` — frozen-horizon forward-year prediction and Value-of-Waiting benchmark.'
if w9 in t and w10 not in t: t=t.replace(w9,w9+'\n'+w10,1)
c9='python -m plant_intelligence.data.maize_prospective_environment --output-root .'
c10='python -m plant_intelligence.models.maize_forecast_time_prediction --output-root .'
if c9 in t and c10 not in t: t=t.replace(c9,c9+'\n'+c10,1)
v='B9 freezes three issuance-time states and a separate forward-year manifest before any prospective-input model is fitted.'
if v in t and 'B10 then consumes those frozen states' not in t: t=t.replace(v,v+' B10 then consumes those frozen states with no new hyperparameter search and makes the chronological forward-year benchmark primary.',1)
la='- that B9 is prospective field validation: its inputs are reconstructed retrospectively with strict issuance cutoffs, T1/T2 use observed-to-date weather rather than archived forecasts, and T2 is a fixed 60-DAP proxy rather than observed reproductive phenology;'
if la in t and 'B10 proves waiting to 60 DAP' not in t:
    t=t.replace(la,la+'\n- that B10 proves waiting to 60 DAP is generally harmful: the pooled forward-year failure is strongly year-dependent and concentrated when historical environmental support is thin;\n- that B10 establishes a final deployment horizon or an optimal environmental kernel: the 2016 T2 failure requires a support/geometry diagnostic before model complexity is changed;\n- that the six-year forward bootstrap provides a precise year-level uncertainty distribution;',1)
d9='- [`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md) — B9 issuance-safe environmental inputs and forward-year validation lock'
d10='- [`docs/case_study_b_forecast_time_prediction.md`](docs/case_study_b_forecast_time_prediction.md) — B10 forecast-time prediction, Value of Waiting, and forward-support diagnostics'
if d9 in t and d10 not in t: t=t.replace(d9,d9+'\n'+d10,1)
p.write_text(t,encoding='utf-8')

p=Path('docs/limitations.md')
l=p.read_text(encoding='utf-8')
marker='## Uncertainty calibration'
if '## B10 forecast-time prediction and support dependence' not in l:
    section='''## B10 forecast-time prediction and support dependence

B10 makes the B9 chronological forward-year backtest the primary performance benchmark and freezes `G`, `G+E_T0`, `G+E_T1`, and `G+E_T2` without a new hyperparameter search.

The pooled forward-year result is non-monotonic. T0 improves over G in the point estimate, T1 is essentially tied with T0, and T2 is substantially worse. This must not be translated into a biological claim that 60-DAP weather is harmful or that later information is intrinsically detrimental.

The T2 failure is strongly heterogeneous and concentrated in the earliest forward backtests, especially 2016, when only 23 prior training environments are available. Later years have more historical environmental support and do not show the same catastrophic behavior. B10 therefore points to a support/representation problem but does not yet identify whether environmental distance, kernel bandwidth, rank, nonstationarity, location composition, or another geometry component is responsible.

The environment-cluster bootstrap supports the pooled T2 deterioration relative to T1. The year-cluster bootstrap has only six test-year clusters and is wide; it must not be presented as a precise year-level uncertainty distribution. Secondary B5 CV-E/CV-GE continuity checks cannot override a failure in the primary chronological design.

B10 remains a retrospective backtest with issuance-safe historical inputs, not a live prospective field trial. T1/T2 use observed-to-date historical weather, not archived operational forecasts.

'''
    l=l.replace(marker,section+marker,1)
p.write_text(l,encoding='utf-8')
