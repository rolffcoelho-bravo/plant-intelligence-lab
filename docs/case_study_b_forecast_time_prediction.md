# Case Study B10 — Forecast-Time-Safe Prediction and Value of Waiting

## Question

B10 asks whether the retrospective information transition observed in B8 survives after environmental inputs are restricted to information that exists at explicit forecast issuance times and evaluated under a forward-year deployment backtest.

The frozen comparison is

\[
G
\rightarrow
G+E_{T0}
\rightarrow
G+E_{T1}
\rightarrow
G+E_{T2}.
\]

The three environmental states come directly from the B9 data lock:

- **T0 — pre-season:** prior-year weather climatology plus static soil and context known at issuance; no current-year realized weather.
- **T1 — 30 DAP:** observed current-year weather from planting through 30 days after planting; no later realized weather.
- **T2 — 60 DAP fixed-time proxy:** observed current-year weather from planting through 60 days after planting; no later realized weather and no observed flowering/silking information.

Observed yield, harvest date, anthesis, silking, ASI, and other future-phenology/outcome variables remain excluded.

## Frozen model design

B10 performs no hyperparameter search. Before seeing B10 performance, the model is frozen at the modal B6-R selected representation:

- genomic rank: **20**
- environmental rank: **16**
- environmental RBF gamma multiplier: **2.0**
- ridge alpha: **10.0**

The environment representation has **70 features** at each issuance state: seven weather summaries, static SSURGO map-unit indicators, latitude/longitude, planting day-of-year encoding, and the available plant-population proxy with an explicit missingness indicator. All environmental transformations learn their scale/kernel geometry from the relevant training partition.

The primary validation is the B9 forward-year lock:

\[
\max(year_{train}) < year_{test},
\]

with test years 2016–2021. The original B5 CV-E and CV-GE folds are retained only as secondary continuity checks.

## Pooled results

| Regime | Model | RMSE | MAE | R² | Correlation |
|---|---|---:|---:|---:|---:|
| CV-E continuity | G | 2.6876 | 2.1524 | 0.0696 | 0.2722 |
| CV-E continuity | G+E_T0 | 2.6030 | 2.0891 | 0.1272 | 0.3826 |
| CV-E continuity | **G+E_T1** | **2.5519** | **2.0413** | **0.1611** | **0.4088** |
| CV-E continuity | G+E_T2 | 2.5625 | 2.0449 | 0.1542 | 0.4049 |
| CV-GE continuity | G | 2.6917 | 2.1559 | 0.0668 | 0.2681 |
| CV-GE continuity | G+E_T0 | 2.6065 | 2.0922 | 0.1249 | 0.3803 |
| CV-GE continuity | **G+E_T1** | **2.5555** | **2.0443** | **0.1588** | **0.4063** |
| CV-GE continuity | G+E_T2 | 2.5661 | 2.0479 | 0.1518 | 0.4026 |
| **Forward year** | G | 2.7642 | 2.2283 | -0.0145 | 0.2847 |
| **Forward year** | **G+E_T0** | **2.6635** | 2.1605 | 0.0581 | **0.3631** |
| **Forward year** | G+E_T1 | 2.6614 | **2.1510** | **0.0595** | 0.3405 |
| **Forward year** | G+E_T2 | **3.2843** | **2.4859** | **-0.4322** | **0.1977** |

The forward-year result is the primary scientific result. T0 reduces pooled RMSE relative to G by about **3.64%**, but the paired cluster intervals cross zero. Waiting from T0 to T1 changes pooled RMSE by only **0.08%**, again with intervals crossing zero. The large B8 late-stage gain does **not** reproduce as a general forward-time gain under the B9 issuance-safe state definition.

Most importantly, T2 is not merely unhelpful in the pooled forward-year benchmark: it is substantially worse. Relative to T1, pooled RMSE increases by **0.6229** (about **23.4%**). The environment-cluster 95% interval for `T2 − T1` is **[0.2082, 1.0774]**, with zero bootstrap improvement frequency. A year-cluster bootstrap is much wider and crosses zero because only six forward test years exist and the effect is strongly heterogeneous across years.

## Forward-year heterogeneity

The T2 failure is concentrated in the earliest forward years, especially 2016:

| Test year | Training environments | G RMSE | T0 RMSE | T1 RMSE | T2 RMSE |
|---:|---:|---:|---:|---:|---:|
| 2016 | 23 | 2.4042 | 2.5167 | 2.7275 | **6.6486** |
| 2017 | 41 | 2.9261 | 3.1291 | **2.2621** | 2.9975 |
| 2018 | 59 | **2.5016** | 2.5906 | 2.5527 | 2.5926 |
| 2019 | 80 | 3.1995 | 2.9281 | 2.9195 | **2.7464** |
| 2020 | 101 | 2.8074 | 2.5450 | 2.7452 | **2.5389** |
| 2021 | 117 | 2.5385 | **2.3381** | 2.4752 | 2.4619 |

This pattern is evidence of **support-dependent environmental transfer**, not evidence that 60-DAP biology is harmful. With only two prior years and 23 training environments in the 2016 backtest, the fixed environmental kernel can extrapolate poorly at T2. As historical environmental support expands, the catastrophic behavior disappears and T2 becomes competitive or beneficial in some later years.

That interpretation is deliberately diagnostic. B10 does not yet establish which component of support failure is responsible: environmental distance, kernel bandwidth, rank, weather-state nonstationarity, location composition, or interactions among them.

## Value of Waiting

For a reference state \(T_i\) and later state \(T_j\), B10 defines

\[
VoW(T_i\rightarrow T_j)=RMSE(T_i)-RMSE(T_j).
\]

Positive values mean that waiting reduced prediction error. Negative values mean that the later information state made prediction worse under the frozen model.

Primary forward-year point estimates:

| Comparison | Value of Waiting (RMSE units) | RMSE change |
|---|---:|---:|
| G → T0 | +0.1007 | +3.64% improvement |
| T0 → T1 | +0.0021 | +0.08% improvement |
| T1 → T2 | **-0.6229** | **23.41% deterioration** |
| T0 → T2 | **-0.6208** | **23.31% deterioration** |

The result rejects a simplistic rule that more realized environmental information must monotonically improve prediction. Information has value only when the representation can transfer it reliably under the available support.

## Secondary continuity checks

The frozen B5 CV-E and CV-GE regimes produce a different, less hostile picture. In both, T0 improves over G by about 3.1%, and T1 adds another ~2.0% pooled RMSE improvement over T0. T2 then gives back about 0.4% relative to T1.

For CV-E, the environment-cluster interval for `T1 − T0` is narrowly below zero, while the year-cluster interval crosses zero. For CV-GE, both uncertainty views remain compatible with a small or absent incremental gain. These continuity results show that the B10 state construction is predictive in ordinary cold-environment folds, but they cannot override the forward-year failure diagnostic.

## Scientific interpretation

B10 materially changes the project conclusion about decision timing.

B8 showed that retrospective stage-derived environmental information appeared to become useful near the reproductive window. B10 shows that, after enforcing issuance-time-safe inputs and forward-year validation, that late information jump is **not deployment-stable**. The earliest forward deployment year is especially fragile.

The strongest defensible conclusion is therefore:

> Forecast-time-safe environmental information can improve cold-environment prediction, but its value is support-dependent and non-monotonic. Under forward-year validation, additional 60-DAP information can be actively harmful when environmental support is thin.

This is a more valuable industrial result than forcing a monotonic accuracy story. A decision system needs to know not only what information is available, but whether the current training support is sufficient to use that information safely.

## Boundaries

B10 does **not** establish:

- that 60-DAP weather is biologically harmful;
- that waiting to 60 DAP generally worsens prediction;
- that the T0 point improvement is universally robust;
- that six forward test years provide a precise year-level uncertainty distribution;
- that the B10 kernel is the optimal forecast-time representation;
- that the backtest is a live prospective field trial;
- that observed-to-date weather is equivalent to an archived operational weather forecast;
- causal mechanisms from the predictive differences.

The 2016 failure must be diagnosed before changing model complexity or declaring a final deployment horizon.

## Reproducibility

Run the required data locks and B10 with:

```bash
python -m plant_intelligence.data.maize_environment_transfer --output-root .
python -m plant_intelligence.data.maize_prospective_environment --output-root .
python -m plant_intelligence.models.maize_forecast_time_prediction --output-root .
```

Primary machine-readable evidence:

- `reports/results/case_study_b10_forecast_time_summary.csv`
- `reports/results/case_study_b10_forward_year_metrics.csv`
- `reports/results/case_study_b10_value_of_waiting.csv`
- `reports/results/case_study_b10_value_of_waiting_bootstrap.csv`
- `reports/results/case_study_b10_design_audit.csv`
- `reports/results/case_study_b10_feature_audit.csv`
- `reports/figures/case_study_b10_value_of_waiting.png`
