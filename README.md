# Plant Intelligence Lab

**Applied data science for genomics, phenotype forecasting, environmental transfer, and uncertainty-aware biological decision support.**

Plant Intelligence Lab is a public research-software project showing how an end-to-end data-science workflow can be applied to biological problems. Genomics and plant phenotyping are the principal application domain; the reusable focus is the process: data provenance, high-dimensional representation, leakage-aware validation, temporal information control, uncertainty quantification, external evaluation, failure analysis, reproducibility, and evidence-grounded scientific interaction.

The repository is organized around two completed empirical case studies built from public research data:

- **Case Study A ‚Äî Arabidopsis longitudinal forecasting:** genomic prediction, protocol-response analysis, early phenotype forecasting, uncertainty, selective prediction, and retrospective experiment prioritization.
- **Case Study B ‚Äî Genotype √ó environment prediction and environmental transfer:** a wheat G√óE benchmark followed by a larger Genomes-to-Fields maize program with continuous environmental information, forward-time testing, uncertainty calibration, and sealed external evaluation.

The project treats a prediction score as only one part of a scientific data-science system. The workflow also asks whether the right information was available at the intended decision time, whether train/test structure matches the deployment problem, whether uncertainty transports, whether unsupported cases are identifiable, and whether negative or incomplete results remain visible after evaluation.

> **Status:** the current empirical program is closed and preserved as a reproducible public research-software release. The frozen Case Study B evidence is not reopened by this release cleanup.

## What the repository demonstrates

The common workflow across the case studies is:

**problem definition ‚Üí public-data audit ‚Üí feature/information boundary ‚Üí validation lock ‚Üí baseline and challenger models ‚Üí uncertainty ‚Üí stress testing ‚Üí external evaluation ‚Üí failure diagnosis ‚Üí reproducible evidence**.

In practice, the repository demonstrates:

- high-dimensional genomic data processing and prediction;
- genotype-aware, environment-aware, double-cold-start, and forward-year validation;
- continuous environmental representation from weather, soil, and management context;
- explicit control of information available at prediction time;
- uncertainty calibration and selective-prediction diagnostics;
- immutable prediction seals for external evaluation;
- transparent treatment of missing outcome keys and unevaluable deployment states;
- postoutcome diagnostics kept separate from model updating;
- machine-readable results, tests, and GitHub Actions;
- a provider-independent scientific AI layer constrained by verified project evidence.

---

## Case Study A ‚Äî Arabidopsis longitudinal forecasting

Case Study A examines how genomic information and early phenotype information contribute to later phenotype prediction and experimental prioritization in *Arabidopsis thaliana*.

| Result | Value |
|---|---:|
| Raw SNP markers processed | **10,709,949** |
| SNP markers after QC | **1,257,793** |
| Genomic accessions used | **152** |
| Best supported forecast | **Day 15 ‚Üí Day 21 phenotype** |
| Out-of-fold RMSE | **0.7397** |
| Out-of-fold $R^2$ | **0.8631** |
| Predictive correlation | **0.9306** |
| 90% interval empirical coverage | **91.23%** |
| Predictions retained after abstention | **98.60%** |
| Retained-case RMSE | **0.6766** |

The high-dimensional genomic-only benchmark is weak relative to the early-phenotype forecast, and adding genomic information to the Day-15 phenotype state does not improve the Day-21 prediction in this dataset. That negative result is retained: model complexity is evaluated by measurable predictive or decision value rather than by complexity alone.

The experiment-prioritization component is a retrospective post-Day-15 benchmark. It is not presented as a prospective laboratory intervention or as realized laboratory savings.

Key code is under `src/plant_intelligence/genetics/`, `forecasting/`, `optimization/`, and `uncertainty/`. Machine-readable evidence is under `reports/results/`.

---

## Case Study B ‚Äî Genotype √ó environment prediction and environmental transfer

Case Study B develops the environmental side of the data-science workflow. It begins with a compact wheat benchmark in which environment identity is categorical, then moves to a larger maize setting where environments can be represented by measurable covariates.

### Wheat benchmark

The executable benchmark uses the BGLR/CIMMYT multi-environment wheat resource.

| Component | Value |
|---|---:|
| Wheat lines | **599** |
| DArT markers | **1,279** |
| Mega-environments | **4** |
| Line √ó environment phenotype cells | **2,396** |
| CV-G G+E+G√óE RMSE | **0.8949** |
| CV2 G+E+G√óE RMSE | **0.8469** |

Explicit G√óE structure improves prediction when environment categories are represented in training. Complete environmental cold start is much weaker because a categorical environment identifier does not encode similarity to a genuinely new environment. That limitation motivates the maize extension.

### Maize environmental-transfer program

The Genomes-to-Fields extension uses a substantially larger data object.

| Component | Value |
|---|---:|
| Phenotype records | **78,686** |
| Genotyped/phenotyped hybrids | **4,372** |
| SNP markers | **98,026** |
| Year-location environments | **136** |
| Environmental covariates in the curated matrix | **202** |
| Study years | **2014‚Äì2021** |

The program tests continuous environmental transfer, representation robustness, biological information blocks, forecast-time information availability, chronological forward-year prediction, and forward residual calibration. The 30-days-after-planting state is retained as the supported reference for the external sequence. A more adaptive 60-day branch is closed after the locked evidence does not establish a reliable advantage over that reference.

### External evaluation sequence

The external sequence is preserved season by season rather than collapsed into one pooled success metric.

| Season | Evaluation state | Evidence |
|---|---|---|
| **2022** | Incomplete primary cohort | **420** predictions were sealed; **387** exact official keys were observable and **33** were absent. The observable-case analysis is diagnostic. |
| **2023** | Information interface unevaluable | The frozen 30-day state could not be reconstructed from an admissible exact planting date, so no prediction cohort was issued. |
| **2024** | Completed sealed external evaluation | **798** predictions were sealed; **779** official keys were evaluable across **92** hybrids and **19** environments. |

For the completed 2024 cohort:

| Metric | Value |
|---|---:|
| RMSE | **2.6197** |
| MAE | **2.1235** |
| $R^2$ | **0.1484** |
| Pearson correlation | **0.3909** |
| Frozen 90% interval environment-balanced coverage | **0.8998** |
| Frozen 90% interval mean score | **10.5301** |
| One-sided widening-rule environment-balanced coverage | **0.9521** |
| One-sided widening-rule mean score | **11.1063** |

The frozen 90% uncertainty rule satisfies its predefined 2024 calibration criterion. The predeclared one-sided widening rule over-covers and has a worse interval score, so it is not promoted over the frozen control.

Postoutcome diagnosis shows a mixed error structure: approximately **42.96%** of squared error is associated with environment-level mean bias and **57.04%** remains within environments after centering. The median predicted-to-observed within-environment standard-deviation ratio is **0.2883**, indicating substantial compression of genotype-response spread. These diagnostics explain the frozen system; they are not used to retrofit it.

The complete stage-by-stage evidence remains available for inspection through the documentation and machine-readable results.

---

## Grounded scientific AI

The repository includes a provider-independent grounded scientific interface downstream of the quantitative evidence. It retrieves verified project outputs, traces numerical claims to sources, and blocks unsupported extrapolation rather than allowing a language model to redefine the scientific record.

The deterministic grounding benchmark contains **11 cases** and checks supported responses, safe handling of unsupported questions, source traceability, and numerical-claim verification. It evaluates the software contract of the grounding layer, not the general scientific accuracy of an arbitrary external language model.

---

## Reproducibility

### Install

```bash
python -m pip install -e .
```

Optional Case Study B dependency:

```bash
python -m pip install -e '.[case-study-b]'
```

### Representative executions

```bash
python -m plant_intelligence.data.wheat_gxe --output-root .
python -m plant_intelligence.models.wheat_gxe_baseline --output-root .

python -m plant_intelligence.data.maize_environment_transfer --output-root .
python -m plant_intelligence.data.maize_prospective_environment --output-root .
python -m plant_intelligence.models.maize_forecast_time_prediction --output-root .
python -m plant_intelligence.uncertainty.maize_forward_uncertainty --output-root .

python -m plant_intelligence.ai.evaluation --output-dir reports/results
```

GitHub Actions separates lightweight unit checks from real-data workflows. The stage-specific workflows remain in `.github/workflows/` because they are part of the reproducible computational record.

### Repository structure

```text
plant-intelligence-lab/
‚îú‚îÄ‚îÄ .github/workflows/       # CI and real-data execution workflows
‚îú‚îÄ‚îÄ data/                    # source notes; raw public data excluded from Git
‚îú‚îÄ‚îÄ docs/                    # methods, case-study evidence, limits, documentation guide
‚îú‚îÄ‚îÄ notebooks/               # exploratory/reproducible notebooks
‚îú‚îÄ‚îÄ reports/
‚îÇ   ‚îú‚îÄ‚îÄ figures/             # empirical figures
‚îÇ   ‚îî‚îÄ‚îÄ results/             # machine-readable evidence, seals, and audit records
‚îú‚îÄ‚îÄ src/plant_intelligence/
‚îÇ   ‚îú‚îÄ‚îÄ ai/
‚îÇ   ‚îú‚îÄ‚îÄ data/
‚îÇ   ‚îú‚îÄ‚îÄ diagnostics/
‚îÇ   ‚îú‚îÄ‚îÄ forecasting/
‚îÇ   ‚îú‚îÄ‚îÄÅùïπï—•çÃº+äRÄÄÉäRsäRäR ÅµΩëï±Ãº+äRÄÄÉäRsäRäR ÅΩ¡—•µ•ÈÖ—•Ω∏º+äRÄÄÉäRSäRäR Å’πçï…—Ö•π—‰º+äRsäRäRFW7G2Æ)IŒ)H)H4ïDDîÙ‚Ê6f`Æ)IŒ)H)HP—Sî—B∏•'8• 8• \õ⁄ôX›ù€[∏•%8• 8•  README.md
```

---

## Public data foundation

The repository uses public research resources only:

- 1001 Genomes and AraPheno for *Arabidopsis thaliana*;
- BGLR/CIMMYT multi-environment wheat data;
- Genomes-to-Fields maize genotype, phenotype, environment, and external-evaluation resources;
- NASA POWER weather;
- USDA-NRCS SSURGO soil information.

Raw source files are excluded from Git where reproducible retrieval, hashes, schema audits, and reconstruction code are sufficient to rebuild the evidence.

---

## Scientific boundaries

Performance claims apply to the evaluated public datasets, targets, and locked validation designs. Important boundaries are:

- predictive association is not a causal biological mechanism;
- retrospective experiment prioritization is not a prospective laboratory trial;
- historical forecast-time reconstruction is not equivalent to an archived operational weather forecast;
- the 2024 maize evaluation was sealed before repository outcome access, but it was not calendar-time prospective;
- the 2022 387-case result is diagnostic because the 420-case primary cohort was incomplete;
- 2023 provides no prediction-performance result;
- Case Study B does not establish a validated environmental-support abstention threshold;
- postoutcome diagnostics are explanatory, not deployable corrections;
- fitted models should not be assumed to transfer automatically across breeding programs, species, or production environments.

Detailed boundaries are maintained in [`docs/limitations.md`](docs/limitations.md).

---

## Documentation

Use [`docs/README.md`](docs/README.md) as the documentation map. Recommended entry points are:

- [`docs/methodology.md`](docs/methodology.md) ‚Äî quantitative methodology and software architecture;
- [`docs/biological_context.md`](docs/biological_context.md) ‚Äî biological context;
- [`docs/case_study_b_data_lock.md`](docs/case_study_b_data_lock.md) ‚Äî wheat data and validation design;
- [`docs/case_study_b_environment_transfer.md`](docs/case_study_b_environment_transfer.md) ‚Äî maize continuous-environment transfer;
- [`docs/case_study_b_prospective_environment.md`](docs/case_study_b_prospective_environment.md) ‚Äî the forecast-time-safe environmental states;
- [`docs/case_study_b_external_temporal_validation.md`](docs/case_study_b_external_temporal_validation.md) ‚Äî sealed 2022 external evaluation and diagnostic boundary;
- [`docs/case_study_b14c_2024_results.md`](docs/case_study_b14c_2024_results.md) ‚Äî completed 2024 external results;
- [`docs/case_study_b_closure_and_contribution_audit.md`](docs/case_study_b_closure_and_contribution_audit.md) ‚Äî scientific closure and contribution boundary.

Machine-readable evidence is under [`reports/results/`](reports/results/), and empirical figures are under [`reports/figures/`](reports/figures/).

---

## License

Licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE).

## Citation

Pereira, Rodolfo. (2026). *Plant Intelligence Lab: Applied Data Science for Genomic Prediction, Phenotype Forecasting and Biological Decision Support*. ShockBridge Pulse Research Lab. Python research software.

Machine-readable metadata are available in [`CITATION.cff`](CITATION.cff).

---

**Plant Intelligence Lab**  
Rodolfo Pereira ¬∑ ShockBridge Pulse Research Lab
