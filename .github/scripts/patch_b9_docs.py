from pathlib import Path

readme_path = Path("README.md")
readme = readme_path.read_text(encoding="utf-8")

readme = readme.replace(
    "continuous-environment transfer, biological environmental representation, decision-horizon forecasting, and a grounded scientific interface",
    "continuous-environment transfer, biological environmental representation, decision-horizon forecasting, prospective environmental-state reconstruction, and a grounded scientific interface",
    1,
)
readme = readme.replace(
    "a larger Genomes-to-Fields maize extension tests transfer to physically characterized unseen environments, asks which environmental information is useful, and maps when that information becomes predictive.",
    "a larger Genomes-to-Fields maize extension tests transfer to physically characterized unseen environments, asks which environmental information is useful, maps when that information becomes predictive, and reconstructs forecast-time-safe environmental states.",
    1,
)

marker = "Detailed Case Study B evidence:"
if "## B9 — Forecast-time-safe environmental states" not in readme:
    if marker not in readme:
        raise SystemExit("README insertion marker not found.")
    section = """## B9 — Forecast-time-safe environmental states

B9 does **not** fit a new predictor. It converts the deployment limitation exposed by B8 into a reproducible data and validation lock. The retrospective APSIM stage summaries are replaced, for this new experiment, by environmental states whose information is explicitly bounded by forecast issuance time.

Three states are frozen:

| Forecast state | Current-year realized weather admitted | Future weather | Observed anthesis/silking/yield |
|---|---|---|---|
| **T0 pre-season** | none | **No** | **No** |
| **T1 — 30 DAP** | planting → 30 days after planting | **No** | **No** |
| **T2 — 60 DAP fixed-time proxy** | planting → 60 days after planting | **No** | **No** |

The executed audit covers **136 environments** from 2014–2021, resolves planting dates and coordinates for **100%** of environments, acquires NASA POWER weather at **113 unique coordinates** with zero missingness in the locked weather audit, obtains SSURGO point soil information at every queried coordinate, and produces **408** issuance-safe environment-state rows. The machine audit records **0 future-weather violations** and **0 observed-phenology violations**.

B9 also preserves the original B5 CV-E/CV-GE manifests unchanged and registers a separate chronological validation before modeling:

$$
\\max(year_{train}) < year_{test}.
$$

The locked forward-year tests cover **113 environments** across six test years, 2016–2021. B9 intentionally reports **no prediction-performance result**: the next model must consume these states and manifests without redefining the horizons after seeing performance.

![Case Study B9 forecast-time input coverage](reports/figures/case_study_b9_input_coverage.png)

A critical boundary remains: B9 reconstructs historical observations as if they were cut off at the issuance date. It is therefore a **retrospective forecast-time-safe backtest substrate**, not a live prospective trial and not an archived weather-forecast benchmark.

"""
    readme = readme.replace(marker, section + marker, 1)

old_evidence = "- [`docs/case_study_b_biological_environment.md`](docs/case_study_b_biological_environment.md) — B7 target-proximal audit, process/stage ablations, and multiple-kernel evidence"
if old_evidence in readme and "B9 forecast-time-safe input and forward-year validation lock" not in readme:
    readme = readme.replace(
        old_evidence,
        old_evidence
        + "\n- [`docs/case_study_b_decision_horizons.md`](docs/case_study_b_decision_horizons.md) — B8 decision-horizon information ablation"
        + "\n- [`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md) — B9 forecast-time-safe input and forward-year validation lock",
        1,
    )

workflow_marker = "- `case-study-b7-process-kernels.yml` — target-proximal audit and biological process/phenology environmental representation."
if workflow_marker in readme and "case-study-b9-prospective-environment.yml" not in readme:
    readme = readme.replace(
        workflow_marker,
        workflow_marker
        + "\n- `case-study-b8-decision-horizons.yml` — retrospective decision-horizon information ablation;"
        + "\n- `case-study-b9-prospective-environment.yml` — forecast-time-safe weather/soil/management data and forward-year validation lock.",
        1,
    )

command_marker = "python -m plant_intelligence.models.maize_environment_process_kernels --output-root ."
if command_marker in readme and "plant_intelligence.data.maize_prospective_environment" not in readme:
    readme = readme.replace(
        command_marker,
        command_marker
        + "\npython -m plant_intelligence.models.maize_environment_decision_horizons --output-root ."
        + "\npython -m plant_intelligence.data.maize_prospective_environment --output-root .",
        1,
    )

validation_marker = "B7 freezes those B6-R choices and changes only the environmental information block, with the five target-proximal `yield_*` outputs excluded from every new candidate."
if validation_marker in readme and "B9 freezes three issuance-time states" not in readme:
    readme = readme.replace(
        validation_marker,
        validation_marker
        + " B8 then measures retrospective information accumulation across source stages. B9 freezes three issuance-time states and a separate forward-year manifest before any prospective-input model is fitted.",
        1,
    )

limits_marker = "- that retrospective full-season or reproductive-stage environmental descriptors are necessarily available for a pre-season forecast;"
if limits_marker in readme and "B9 forecast-time-safe states constitute prospective field validation" not in readme:
    readme = readme.replace(
        limits_marker,
        limits_marker
        + "\n- that B9 forecast-time-safe states constitute prospective field validation: B9 is a retrospective reconstruction with strict issuance cutoffs, and T1/T2 use observed-to-date weather rather than archived forecasts;",
        1,
    )

docs_marker = "- [`docs/case_study_b_biological_environment.md`](docs/case_study_b_biological_environment.md) — B7 process/phenology environmental ablation and target-proximal sensitivity"
if docs_marker in readme and "docs/case_study_b_prospective_environment.md" not in readme.split("# Documentation", 1)[-1]:
    readme = readme.replace(
        docs_marker,
        docs_marker
        + "\n- [`docs/case_study_b_decision_horizons.md`](docs/case_study_b_decision_horizons.md) — B8 decision-time information accumulation and source-level availability boundary"
        + "\n- [`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md) — B9 issuance-safe environmental inputs and forward-year validation lock",
        1,
    )

readme_path.write_text(readme, encoding="utf-8")

limitations_path = Path("docs/limitations.md")
limitations = limitations_path.read_text(encoding="utf-8")
insert_before = "## Uncertainty calibration"
if "## Forecast-time-safe environmental reconstruction" not in limitations:
    if insert_before not in limitations:
        raise SystemExit("Limitations insertion marker not found.")
    section = """## Forecast-time-safe environmental reconstruction

B9 reconstructs environmental state using fixed issuance dates rather than observed future phenology. T0 excludes all current-year realized weather, while T1 and T2 use only weather observed through 30 and 60 days after planting respectively. Observed yield, harvest date, anthesis, silking, ASI, and related future-phenology fields are explicitly forbidden. The executed audit records zero future-weather and zero observed-phenology violations.

This makes B9 **forecast-time safe with respect to the information cutoff**, but it does not make the study prospective. NASA POWER observations are retrieved retrospectively and truncated at the historical issuance date. T1 and T2 are observed-to-date weather reconstructions, not archived operational weather forecasts. A true live deployment would require predictions to be issued before future outcomes occur and, if future weather forecasts are used, their historically issued forecast vintages must be preserved.

The T2 60-DAP state is a fixed calendar-time proxy and must not be described as observed reproductive stage, flowering, anthesis, or silking. Its purpose is to remove the observed-silking calibration problem exposed in B8.

The SSURGO layer is a public static soil-map representation at the resolved coordinate. It is not a plot-level soil assay and cannot represent all within-field soil heterogeneity. Management metadata are admitted only when their provenance supports availability at issuance.

B9 also registers a forward-year stress test in which every training year precedes the test year. This is stronger temporal backtesting than shuffled environment folds, but it remains retrospective historical evaluation rather than prospective field validation.

"""
    limitations = limitations.replace(insert_before, section + insert_before, 1)
limitations_path.write_text(limitations, encoding="utf-8")
