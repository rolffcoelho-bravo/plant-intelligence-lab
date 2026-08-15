from pathlib import Path

path = Path("README.md")
text = path.read_text(encoding="utf-8")

duplicate_workflow = (
    "- `case-study-b10u-robust-aggregation.yml` — geometry-agnostic T2 aggregation and branch stopping experiment.\n"
    "- `case-study-b11-forward-uncertainty.yml` — frozen-T1 forward residual calibration, coverage, reliability, and selective-risk audit.\n"
    "- `case-study-b10u-robust-aggregation.yml` — equal-mean/median T2 geometry aggregation and predeclared stopping decision.\n"
)
canonical_workflow = (
    "- `case-study-b10u-robust-aggregation.yml` — equal-mean/median T2 geometry aggregation and predeclared stopping decision.\n"
    "- `case-study-b11-forward-uncertainty.yml` — frozen-T1 forward residual calibration, coverage, reliability, and selective-risk audit.\n"
)
if duplicate_workflow in text:
    text = text.replace(duplicate_workflow, canonical_workflow, 1)

command_dup = (
    "python -m plant_intelligence.models.maize_geometry_robust_aggregation --output-root .\n"
    "python -m plant_intelligence.uncertainty.maize_forward_uncertainty --output-root .\n"
    "python -m plant_intelligence.models.maize_geometry_robust_aggregation --output-root .\n"
)
command_clean = (
    "python -m plant_intelligence.models.maize_geometry_robust_aggregation --output-root .\n"
    "python -m plant_intelligence.uncertainty.maize_forward_uncertainty --output-root .\n"
)
if command_dup in text:
    text = text.replace(command_dup, command_clean, 1)

old_validation = (
    "B10-T then audits whether the geometry ranking itself is temporally persistent and rejects rank persistence as a sufficient basis for a T2 controller. "
    "B10-U finally tests whether representation uncertainty can be diversified without selecting a geometry; aggregation repairs frozen T2 but does not robustly beat T1, so the adaptive T2 branch closes under its locked stopping rule."
)
new_validation = old_validation + (
    " B11 then freezes T1 and evaluates strictly chronological residual calibration, admitting the interval layer while keeping environmental-support abstention diagnostic."
)
if old_validation in text and "B11 then freezes T1" not in text:
    text = text.replace(old_validation, new_validation, 1)

path.write_text(text, encoding="utf-8")
