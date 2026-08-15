from pathlib import Path

readme = Path('README.md')
text = readme.read_text(encoding='utf-8')
marker = 'Detailed Case Study B evidence:'
if '## B10-T — Temporal geometry stability audit' not in text:
    section = '''## B10-T — Temporal geometry stability audit

B10-T asks whether the 12 B10-R environmental geometries are rank-persistent enough across the six locked forward years to justify any adaptive T2 controller. No new predictor is fitted.

| Transition | Spearman rank $\\rho$ | Top-3 overlap | Previous winner next-year rank | Lagged-winner regret |
|---|---:|---:|---:|---:|
| 2016→2017 | 0.014 | 0/3 | 7 | 0.4439 |
| 2017→2018 | **-0.587** | 0/3 | **12** | 0.3402 |
| 2018→2019 | 0.503 | 2/3 | 4 | 0.0715 |
| 2019→2020 | **0.895** | **3/3** | **1** | **0.0000** |
| 2020→2021 | **-0.874** | **0/3** | **12** | 0.4436 |

Across the five adjacent transitions, mean Spearman rank correlation is **-0.0098**, mean Top-3 overlap is **33.3%**, and the annual winner persists only **20%** of the time. Carrying the previous year's winner forward has mean regret **0.2598 RMSE** and beats frozen T1 in only **2 of 5** transitions.

The 2019→2020 period is a useful counterexample to simplistic narratives: geometry ranking appears highly stable in that transition, but the next transition nearly reverses the full ranking. The 2020 winner falls to rank **12 of 12** in 2021.

Outcome-free support/kernel shifts are also audited, but only five transitions exist. Their correlations are therefore descriptive and do not justify a threshold or controller. The B10-T conclusion is that **rank persistence is not a defensible basis for T2 deployment under the current evidence**.

![Case Study B10-T temporal geometry stability](reports/figures/case_study_b10t_temporal_stability.png)

'''
    text = text.replace(marker, section + marker, 1)

b10s = '- [`docs/case_study_b_training_only_geometry_selection.md`](docs/case_study_b_training_only_geometry_selection.md) — B10-S training-only selection and negative deployment result'
b10t = '- [`docs/case_study_b_temporal_geometry_stability.md`](docs/case_study_b_temporal_geometry_stability.md) — B10-T year-to-year geometry ranking persistence and lagged-winner regret'
if b10s in text and b10t not in text:
    text = text.replace(b10s, b10s + '\n' + b10t, 1)

validation = 'B10-S finally converts that diagnostic grid into a strictly training-only expanding-window selection test and preserves its negative result when historical performance fails to transfer.'
if validation in text and 'B10-T then audits whether the geometry ranking itself is temporally persistent' not in text:
    text = text.replace(validation, validation + ' B10-T then audits whether the geometry ranking itself is temporally persistent and rejects rank persistence as a sufficient basis for a T2 controller.', 1)

wf = '- `case-study-b10s-training-only-geometry.yml` — training-only chronological T2 geometry-selection reproduction.'
if wf in text and 'case-study-b10t-temporal-stability.yml' not in text:
    text = text.replace(wf, wf + '\n- `case-study-b10t-temporal-stability.yml` — temporal geometry ranking, Top-k persistence, lagged-winner regret, and outcome-free shift audit.', 1)

cmd = 'python -m plant_intelligence.models.maize_training_only_geometry_selection --output-root .'
if cmd in text and 'maize_geometry_temporal_stability' not in text:
    text = text.replace(cmd, cmd + '\npython -m plant_intelligence.models.maize_geometry_temporal_stability --output-root .', 1)

limit = '- that the B10-S oracle-regret table is a prospective benchmark: oracle configurations explicitly use outer-year outcomes and are never admitted for deployment;'
if limit in text and 'B10-T establishes a deployable rank-persistence controller' not in text:
    text = text.replace(limit, limit + '\n- that B10-T establishes a deployable rank-persistence controller: mean adjacent-year rank correlation is near zero, annual winners rarely persist, and the outcome-free shift correlations have only five transitions;\n- that the strongest B10-T outcome-free shift correlation defines a biological mechanism or threshold: those associations are descriptive small-n diagnostics only;', 1)

see = '[`docs/case_study_b_training_only_geometry_selection.md`](docs/case_study_b_training_only_geometry_selection.md) for the detailed boundaries.'
if see in text:
    text = text.replace(see, '[`docs/case_study_b_training_only_geometry_selection.md`](docs/case_study_b_training_only_geometry_selection.md), and [`docs/case_study_b_temporal_geometry_stability.md`](docs/case_study_b_temporal_geometry_stability.md) for the detailed boundaries.', 1)

# Documentation list near the bottom may contain the B10-S document independently.
doc_line = '- [`docs/case_study_b_training_only_geometry_selection.md`](docs/case_study_b_training_only_geometry_selection.md) — B10-S training-only chronological geometry selection'
if doc_line in text and '— B10-T temporal geometry ranking stability' not in text:
    text = text.replace(doc_line, doc_line + '\n- [`docs/case_study_b_temporal_geometry_stability.md`](docs/case_study_b_temporal_geometry_stability.md) — B10-T temporal geometry ranking stability and lagged-winner regret', 1)

readme.write_text(text, encoding='utf-8')

limitations = Path('docs/limitations.md')
limits = limitations.read_text(encoding='utf-8')
marker = '## Uncertainty calibration'
if '## B10-T temporal ranking stability boundary' not in limits:
    section = '''## B10-T temporal ranking stability boundary

B10-T does not fit or select a new predictor. It audits the published B10-R 12-geometry RMSE ranking across the six locked forward years. The mean adjacent-year Spearman rank correlation is approximately zero, Top-3 overlap averages one third, and the annual winner persists in only one of five transitions. Reusing the previous year's winner therefore does not provide a defensible deployment rule.

A particularly important counterexample is 2019→2020 versus 2020→2021. Ranking persistence is very high in the first transition, but the next transition is strongly negative and the previous winner falls to last place. One recent stable transition cannot therefore be interpreted as evidence of future persistence.

B10-T also reports descriptive correlations between ranking inversion and outcome-free support/kernel changes. There are only five transitions. These correlations are hypothesis-generating only, are not significance claims, and must not be converted into thresholds, causal biological mechanisms, or controller admission rules.

The B10-T machine summary records `NOT_JUSTIFIED_BY_RANK_PERSISTENCE_AUDIT`. This means the current evidence rejects a rank-persistence controller; it does not prove that all adaptive environmental representations are impossible. A future method should reduce sensitivity to selecting one brittle geometry and must still be evaluated without outer-year outcome leakage.

'''
    limits = limits.replace(marker, section + marker, 1)
limitations.write_text(limits, encoding='utf-8')
