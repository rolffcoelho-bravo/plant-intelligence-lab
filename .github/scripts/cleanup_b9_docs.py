from pathlib import Path

path = Path("README.md")
text = path.read_text(encoding="utf-8")

# Remove duplicate B8 evidence/documentation entries created by consolidating an
# already B8-aware README.
text = text.replace(
    "- [`docs/case_study_b_decision_horizons.md`](docs/case_study_b_decision_horizons.md) — B8 availability audit and decision-horizon information frontier\n",
    "",
)
text = text.replace(
    "- [`docs/case_study_b_decision_horizons.md`](docs/case_study_b_decision_horizons.md) — B8 decision-time availability and temporal information frontier\n",
    "",
)

# Preserve the logical sequence B7 -> B8 -> B9 exactly once.
text = text.replace(
    "B9 freezes three issuance-time states and a separate forward-year manifest before any prospective-input model is fitted. B8 keeps those representation choices frozen again and changes only the information horizon; post-horizon environmental columns are prohibited from earlier horizons.",
    "B9 freezes three issuance-time states and a separate forward-year manifest before any prospective-input model is fitted.",
    1,
)

b8_workflow = "- `case-study-b8-decision-horizons.yml` — decision-time availability audit and temporal information-frontier benchmark."
b9_workflow = "- `case-study-b9-prospective-environment.yml` — forecast-time-safe weather/soil/management data and forward-year validation lock."
if b8_workflow in text and b9_workflow not in text:
    text = text.replace(b8_workflow, b8_workflow + "\n" + b9_workflow, 1)

text = text.replace(
    "python -m plant_intelligence.models.maize_environment_decision_horizons --output-root .\npython -m plant_intelligence.data.maize_prospective_environment --output-root .\npython -m plant_intelligence.models.maize_environment_decision_horizons --output-root .",
    "python -m plant_intelligence.models.maize_environment_decision_horizons --output-root .\npython -m plant_intelligence.data.maize_prospective_environment --output-root .",
    1,
)

limit_anchor = "- that historical-location environmental summaries improve pre-season RMSE in the current representation;"
b9_limit = "- that B9 is prospective field validation: its inputs are reconstructed retrospectively with strict issuance cutoffs, T1/T2 use observed-to-date weather rather than archived forecasts, and T2 is a fixed 60-DAP proxy rather than observed reproductive phenology;"
if limit_anchor in text and b9_limit not in text:
    text = text.replace(limit_anchor, limit_anchor + "\n" + b9_limit, 1)

old_see = "and [`docs/case_study_b_decision_horizons.md`](docs/case_study_b_decision_horizons.md) for the detailed boundaries."
new_see = "[`docs/case_study_b_decision_horizons.md`](docs/case_study_b_decision_horizons.md), and [`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md) for the detailed boundaries."
if old_see in text and "case_study_b_prospective_environment.md) for the detailed boundaries" not in text:
    text = text.replace(old_see, new_see, 1)

path.write_text(text, encoding="utf-8")
