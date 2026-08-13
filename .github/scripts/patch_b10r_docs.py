from pathlib import Path

readme = Path('README.md')
text = readme.read_text(encoding='utf-8')

text = text.replace(
    'decision-horizon forecasting, prospective environmental-state reconstruction, Value-of-Waiting analysis, and a grounded scientific interface',
    'decision-horizon forecasting, prospective environmental-state reconstruction, Value-of-Waiting analysis, support-aware forward diagnostics, and a grounded scientific interface',
    1,
)
text = text.replace(
    'maps when that information becomes predictive, and reconstructs forecast-time-safe environmental states.',
    'maps when that information becomes predictive, reconstructs forecast-time-safe environmental states, and diagnoses when support geometry makes later environmental information unsafe to use.',
    1,
)

marker = 'Detailed Case Study B evidence:'
if '## B10-R — Support-aware forward-time environmental geometry' not in text:
    if marker not in text:
        raise SystemExit('README B10-R insertion marker not found')
    section = '''## B10-R — Support-aware forward-time environmental geometry

B10-R keeps the B9 horizons and B10 forward-year splits fixed and asks **why** T2 failed. Support diagnostics are constructed from training environments only; a small rank/bandwidth grid is used strictly as a retrospective explanation tool, not as a new model-selection procedure.

The strongest pooled support-error associations are directionally coherent with transfer risk: lower maximum training-kernel similarity is associated with larger T2 deterioration (Spearman **-0.392**), greater weather-state distance with larger deterioration (**+0.356**), and fewer prior environments with larger deterioration (**-0.342**). These signs survive every leave-one-year-out analysis, although within-year relationships are weaker and do not support a hard abstention threshold.

The main result is more specific than simple support scarcity. The frozen 2016 T2 geometry (rank 16, gamma multiplier 2) has RMSE **6.6486**, while diagnostic alternatives reach **2.2283** at rank 8/gamma 4 and **2.2508** at rank 32/gamma 4. The 2016 frozen T2 training kernel has effective rank about **13.0** while retaining 16 dimensions. This strongly implicates a **support × spectral-geometry interaction** in the catastrophic 2016 failure.

But geometry is not the whole story. In **2017**, none of the twelve diagnostic T2 geometries beats the frozen T1 benchmark. Later years are substantially less fragile. The defensible diagnosis is therefore:

$$
\\boxed{\\text{T2 transfer risk}=\\text{support/spectral geometry interaction}+\\text{year-dependent information mismatch}.}
$$

The lowest pooled diagnostic-grid RMSE is **2.5392**, about 4.6% below frozen T1, but this is an **oracle diagnostic** inspected on held-out outcomes and is not promoted as a deployable champion. The next admissible step is to ask whether environmental geometry can be selected using **training-only historical forward validation**.

![Case Study B10-R support-aware forward diagnostics](reports/figures/case_study_b10r_support_diagnostic.png)

'''
    text = text.replace(marker, section + marker, 1)

b10 = '- [`docs/case_study_b_forecast_time_prediction.md`](docs/case_study_b_forecast_time_prediction.md) — B10 forward-year prediction, Value of Waiting, and support-failure evidence'
b10r = '- [`docs/case_study_b_forward_support_diagnostics.md`](docs/case_study_b_forward_support_diagnostics.md) — B10-R support geometry, spectral sensitivity, and forward-failure diagnosis'
if b10 in text and b10r not in text:
    text = text.replace(b10, b10 + '\n' + b10r, 1)

validation = 'B10 then consumes those frozen states with no new hyperparameter search and makes the chronological forward-year benchmark primary.'
if validation in text and 'B10-R keeps those forward splits fixed' not in text:
    text = text.replace(
        validation,
        validation + ' B10-R keeps those forward splits fixed, constructs support diagnostics from training environments only, and treats its rank/bandwidth grid as diagnostic rather than selected performance.',
        1,
    )

workflow = '- `case-study-b10-forecast-time-prediction.yml` — frozen-horizon forward-year prediction and Value-of-Waiting benchmark.'
workflow_r = '- `case-study-b10r-support-diagnostics.yml` — support geometry, forward-failure diagnosis, and diagnostic-only rank/bandwidth sensitivity.'
if workflow in text and workflow_r not in text:
    text = text.replace(workflow, workflow + '\n' + workflow_r, 1)

command = 'python -m plant_intelligence.models.maize_forecast_time_prediction --output-root .'
command_r = 'python -m plant_intelligence.models.maize_forward_support_diagnostics --output-root .'
if command in text and command_r not in text:
    text = text.replace(command, command + '\n' + command_r, 1)

limit_anchor = '- that the six-year forward bootstrap provides a precise year-level uncertainty distribution;'
new_limits = '''- that the B10-R diagnostic rank-32/gamma-4 pooled result is a deployable champion: it is an oracle sensitivity result inspected on held-out outcomes;
- that B10-R has validated a support threshold or fallback policy: pooled support associations are informative but within-year relationships are not uniformly monotonic;
- that sparse historical support alone explains T2 failure: 2016 is strongly geometry-sensitive, while 2017 remains worse than T1 across the tested diagnostic geometry grid;'''
if limit_anchor in text and 'diagnostic rank-32/gamma-4' not in text:
    text = text.replace(limit_anchor, limit_anchor + '\n' + new_limits, 1)

see_old = '[`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md) for the detailed boundaries.'
see_new = '[`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md), [`docs/case_study_b_forecast_time_prediction.md`](docs/case_study_b_forecast_time_prediction.md), and [`docs/case_study_b_forward_support_diagnostics.md`](docs/case_study_b_forward_support_diagnostics.md) for the detailed boundaries.'
if see_old in text:
    text = text.replace(see_old, see_new, 1)

doc_b10 = '- [`docs/case_study_b_forecast_time_prediction.md`](docs/case_study_b_forecast_time_prediction.md) — B10 forecast-time prediction, Value of Waiting, and forward-support diagnostics'
doc_b10r = '- [`docs/case_study_b_forward_support_diagnostics.md`](docs/case_study_b_forward_support_diagnostics.md) — B10-R support geometry, spectral sensitivity, and forward-time failure diagnosis'
if doc_b10 in text and doc_b10r not in text:
    text = text.replace(doc_b10, doc_b10 + '\n' + doc_b10r, 1)

readme.write_text(text, encoding='utf-8')

limitations = Path('docs/limitations.md')
limits = limitations.read_text(encoding='utf-8')
marker = '## Uncertainty calibration'
if '## B10-R support geometry and diagnostic sensitivity' not in limits:
    if marker not in limits:
        raise SystemExit('limitations B10-R insertion marker not found')
    section = '''## B10-R support geometry and diagnostic sensitivity

B10-R does not select a replacement T2 model. Outcome-free support variables are constructed from the corresponding training environments, but the association analysis and rank/bandwidth grid are evaluated against already-observed B10 held-out errors. The grid therefore diagnoses mechanism and sensitivity; its lowest RMSE must not be presented as prospective or selected performance.

The strongest pooled associations indicate that weaker kernel similarity, greater weather-state distance, and fewer prior environments tend to accompany larger T2-versus-T1 error. These relationships retain their direction under leave-one-year-out analysis, but within-year associations are weaker and novelty quartiles are not monotonic. No single support measure is therefore admitted as a hard abstention or fallback threshold.

The severe 2016 T2 collapse is highly geometry-sensitive. Several diagnostic rank/bandwidth choices remove most of the failure, while the frozen rank-16 representation is especially poor. The 2016 training kernel has effective rank around 13 while 16 dimensions are retained, which is consistent with a support/spectral-geometry interaction. This is not proof that effective rank is the causal numerical mechanism, nor that rank 16 is generally unsafe.

2017 provides an essential counterexample: none of the twelve diagnostic T2 geometries beats its frozen T1 benchmark. The forward failure therefore cannot be reduced to tuning or sample size alone. Year-specific distribution shift or information mismatch remains part of the diagnosis.

Any next-stage geometry controller must choose its representation using training-only information, ideally nested historical forward splits. Only after that succeeds can a support-aware T1/T2 fallback or abstention rule be evaluated without outcome leakage.

'''
    limits = limits.replace(marker, section + marker, 1)
limitations.write_text(limits, encoding='utf-8')
