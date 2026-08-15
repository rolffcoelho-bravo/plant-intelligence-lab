# Case Study B10-T — Temporal Stability of Environmental Spectral Geometry

## Purpose

B10-T asks whether the 12 environmental geometries already evaluated in B10-R have enough year-to-year ranking persistence to justify any adaptive T2 controller.

No new predictor is fitted and no geometry is promoted. The analysis consumes only the published B10-R evidence for the six locked forward test years 2016–2021.

For each year, the 12 geometries are ranked by held-out RMSE. B10-T then measures:

- adjacent-year Spearman rank correlation;
- Top-1, Top-3 and Top-5 overlap;
- persistence of the previous year's winner;
- next-year regret from reusing the previous year's winner;
- per-configuration rank dispersion;
- descriptive alignment between rank inversion and outcome-free support/kernel changes already measured in B10-R.

The last analysis has only five adjacent-year transitions. Its correlations are therefore descriptive diagnostics only and are not used to define a deployment rule.

## Main temporal-stability result

| Transition | Spearman rank rho | Top-3 overlap | Previous winner next-year rank | Lagged-winner regret | Lagged winner beats frozen T1? |
|---|---:|---:|---:|---:|---|
| 2016 → 2017 | 0.0140 | 0 / 3 | 7 | 0.4439 | No |
| 2017 → 2018 | **-0.5874** | 0 / 3 | **12** | 0.3402 | No |
| 2018 → 2019 | 0.5035 | 2 / 3 | 4 | 0.0715 | Yes |
| 2019 → 2020 | **0.8951** | **3 / 3** | **1** | **0.0000** | Yes |
| 2020 → 2021 | **-0.8741** | **0 / 3** | **12** | 0.4436 | No |

Across all five transitions:

- mean adjacent-year Spearman rho: **-0.0098**;
- median adjacent-year Spearman rho: **0.0140**;
- mean Top-3 overlap fraction: **0.3333**;
- winner persistence: **1/5 = 20%**;
- mean lagged-winner regret: **0.2598 RMSE**;
- median lagged-winner regret: **0.3402 RMSE**;
- previous-year winner beats frozen T1 in only **2/5 = 40%** of transitions.

The geometry ranking is therefore not temporally persistent in a way that supports a simple lagged-winner or rank-persistence controller.

## The central counterexample

The 2019 → 2020 transition looks highly encouraging:

- Spearman rho = **0.8951**;
- Top-3 overlap = **100%**;
- the 2019 winner `rank32/gamma0.5` remains the 2020 winner;
- lagged-winner regret = **0**.

If the analysis ended there, a persistence-based controller could appear plausible.

But the very next transition, 2020 → 2021, nearly reverses the complete ranking:

- Spearman rho = **-0.8741**;
- Top-1 overlap = **0%**;
- Top-3 overlap = **0%**;
- Top-5 overlap = **0%**;
- the 2020 winner becomes **rank 12 of 12** in 2021;
- lagged-winner regret rises to **0.4436 RMSE**, about **18.4%** above the 2021 oracle diagnostic minimum.

This pair of transitions is strong evidence that a short period of apparent geometry stability cannot be assumed to persist into the next deployment year.

## Per-configuration stability

No configuration behaves as a stable universal champion.

The best average RMSE rank across the six years is `rank32/gamma4`, with:

- mean rank **4.5**;
- rank standard deviation **2.74**;
- one annual win;
- Top-3 placement in only **2 of 6** years;
- worst annual rank **8**.

The configuration with the most annual wins is not stable either. `rank16/gamma4` wins two years but has mean rank **7.33**, rank standard deviation **5.01**, and moves as far as rank 12 in other years.

Similarly, `rank32/gamma0.5` wins two years but ranges from rank 1 to rank 12.

This means that neither average rank nor winner count supplies a defensible static T2 geometry.

## Lagged-winner regret

B10-T explicitly tests a simple prospective idea: use year `t`'s best geometry in year `t+1`.

That rule succeeds only in the 2019 → 2020 transition and remains better than frozen T1 in 2018 → 2019. It fails in the other three transitions.

The mean next-year regret from carrying forward the previous winner is **0.2598 RMSE**, and the median regret is **0.3402 RMSE**.

The result therefore rejects the idea that the previous year's best T2 geometry is a reliable deployment choice.

## Outcome-free environmental shift audit

B10-T also compares rank inversion with outcome-free quantities already available before yield is observed, including:

- growth in the number of historical training environments;
- T2 nearest-support distance;
- maximum training-kernel similarity;
- local kernel density;
- projection residual;
- weather-space nearest distance;
- full and weather-kernel effective rank;
- full and weather RBF bandwidth changes;
- a composite standardized outcome-free shift index.

There are only **five transitions**, so no inferential claim is justified.

The descriptive correlations are mixed. The composite outcome-free shift index has Spearman rho **-0.30** with rank inversion and **0.30** with lagged-winner regret. The absolute change in weather-kernel RBF gamma has rho **0.60** with rank inversion and **0.90** with lagged-winner regret, while other support metrics have different signs. With `n=5`, these values are hypothesis-generating only.

Therefore B10-T does **not** identify a validated outcome-free state variable that predicts when the geometry ranking will invert.

## Scientific interpretation

B10-T sharpens the negative B10-S result.

B10-S showed that expanding-window historical prediction performance cannot reliably select the next year's T2 geometry. B10-T now explains why that failure is plausible: the geometry ranking itself is highly temporally nonstationary.

The strongest defensible conclusion is:

> Environmental-representation quality is not sufficiently rank-persistent across forward years for a single lagged winner, historical rank, or short-run persistence rule to justify T2 deployment.

This separates four concepts that must not be conflated:

1. **Information availability:** B9 determines what information exists at each forecast time.
2. **Information value:** B10 shows that more information does not automatically improve prediction.
3. **Representation sensitivity:** B10-R shows that T2 performance depends strongly on geometry.
4. **Representation stability:** B10-S/B10-T show that the geometry that performs well in one historical regime may not remain good in the next.

The resulting decision-system principle is:

> A richer environmental information state should not be admitted merely because it is available, because a geometry worked historically, or because its ranking was stable over one recent transition.

## Controller consequence

B10-T does not justify a T2 controller based on geometry-rank persistence.

The machine-readable summary therefore records:

`NOT_JUSTIFIED_BY_RANK_PERSISTENCE_AUDIT`

This is not a statement that adaptive environmental modeling is impossible. It means that the current evidence rejects three increasingly permissive shortcuts:

- fixed frozen T2 geometry;
- expanding-window historical geometry selection;
- previous-year or short-run geometry-rank persistence.

Any next adaptive method should reduce dependence on selecting one brittle geometry rather than enlarge the hyperparameter search.

## What B10-T does not establish

B10-T does not establish:

- that environmental geometry is random;
- that spectral representations have no value;
- that no outcome-free stability signal exists;
- that the weather-kernel bandwidth association is causal or reproducible;
- that a five-transition correlation supports a threshold;
- that the best average-rank geometry should be deployed;
- that the oracle annual winner is prospectively attainable;
- that a new neural or nonlinear model would solve the instability;
- a production T1/T2 admission controller.

## Reproducibility

```bash
python -m plant_intelligence.models.maize_geometry_temporal_stability --output-root .
```

Primary evidence:

- `reports/results/case_study_b10t_geometry_rank_table.csv`
- `reports/results/case_study_b10t_rank_stability.csv`
- `reports/results/case_study_b10t_config_stability.csv`
- `reports/results/case_study_b10t_shift_alignment.csv`
- `reports/results/case_study_b10t_shift_associations.csv`
- `reports/results/case_study_b10t_summary.csv`
- `reports/figures/case_study_b10t_temporal_stability.png`
