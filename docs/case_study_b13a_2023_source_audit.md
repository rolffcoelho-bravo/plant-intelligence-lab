# Case Study B13A — Blind 2023 Source and Compatibility Audit

## Purpose

B13A is the source-compatibility gate between the merged B13 statistical lock and any 2023 prediction seal.

It does **not** generate 2023 predictions and it does **not** read 2023 phenotypic outcomes.

The question is narrow:

> Can the public G2F 2023 field-season release support a sealed `T1_30DAP` prediction stage while preserving the frozen B10/B11/B12 predictor, the merged B13 calibration rule, and a mechanically enforceable pre-outcome boundary?

## Why 2023 requires a different source protocol

The public G2F resources provide a dedicated 2022 GxE prediction-competition package and a dedicated 2024 GxE prediction-competition package, whereas the 2023 resource is the field-season release itself (DOI `10.25739/rzzy-3n27`). B13A therefore does not impose B12's submission-template/answer-file structure on 2023.

The 2023 CyVerse release separates phenotypic, weather, soil, and supplemental resources. B13A treats the entire `a._2023_phenotypic_data/` directory as forbidden before any future prediction seal.

## Frozen B13 state

Before source acquisition, B13A verifies the merged machine-readable B13 lock:

- target year: 2023;
- point predictor: unchanged frozen `G+E_T1`;
- control interval: `FROZEN_B11_90`;
- adaptive interval: `ONE_SIDED_CLUSTER_DRIFT_GUARD_90`;
- 2023 adaptive quantile level: `0.9512813317177465`;
- primary estimand: `OFFICIALLY_OBSERVABLE_SEALED_KEYS`;
- T2 branch: closed;
- post-result tuning: prohibited.

B13A has no authority to change these values.

## Blind source boundary

Exactly four public 2023 resources are allowed before a prediction seal:

- `z._2023_supplemental_info/g2f_2023_field_metadata.csv`;
- `z._2023_supplemental_info/g2f_2023_agronomic_information.csv`;
- `b._2023_weather_data/g2f_2023_weather_cleaned.csv`;
- `c._2023_soil_data/g2f_2023_soil_data.csv`.

The canonical workflow stages those four objects through anonymous CyVerse iRODS/GoCommands and records a SHA-256 digest for each source.

The following remain forbidden:

- any path containing `a._2023_phenotypic_data`;
- `g2f_2023_phenotypic_data.csv`;
- any unregistered object outside the explicit allow-list.

No 2023 phenotype directory or file was accessed during B13A.

## Frozen genotype compatibility

B13A does not rebuild the genomic representation from the newer 2014–2023 genotype release.

It verifies the immutable B12 prediction SHA-256

`fb8347da2a5ba9fff0d106fa9b7a13037818c8e0e0d1387527dbf090c3085220`

and inherits exactly the 43 unique hybrids already supported by the frozen B5 genomic representation.

The genomic side of the portability audit therefore remains compatible without changing marker construction.

## Historical T1 encoder reproduction

B13A reuses the B12 historical T1 encoding audit. The frozen historical matrix was reproduced exactly:

- identical environment order;
- identical feature columns;
- identical numeric values.

Therefore the B13A stop is not caused by an encoder rewrite or a change in the frozen predictor.

## 2023 safe environment audit

The allow-listed 2023 field metadata identify 27 experiment environments. Environment identity is available through `Experiment_Code`, and safe field metadata provide location information for most environments.

However, the field metadata do **not** expose an explicit planting-date field under the predeclared planting/sowing names required to anchor `T1_30DAP`.

The supplemental agronomic table is also not a planting-calendar table. Its observed schema contains treatment/application information, including `Date_of_application`. B13A explicitly refuses to reinterpret treatment/application dates as planting dates.

Likewise, `Date_weather_station_placed` is not treated as a planting-date proxy.

These are deliberate non-substitutions. The frozen T1 horizon is defined relative to planting; changing that clock would change the scientific meaning of the predictor after the external year had already been chosen.

## Canonical result

The completed blind audit records:

- frozen supported genotypes: **43**;
- safe 2023 metadata environments: **27**;
- T1-metadata-feasible environments: **0**;
- candidate prediction cells: **0**;
- historical T1 encoder exactly reproduced: **true**;
- phenotype directory accessed: **false**;
- phenotype file accessed: **false**;
- 2023 observed keys used to define the candidate universe: **false**;
- point predictor changed: **false**;
- T2 branch reopened: **false**;
- post-result tuning permitted: **false**.

The machine decision is:

`B13A_2023_T1_CONTEXT_INSUFFICIENT`

with reason:

`NO_EXPLICIT_PLANTING_DATE_IN_ALLOWLISTED_2023_PREOUTCOME_SOURCES`

## Interpretation

This is a **source-interface incompatibility**, not a model-performance failure and not a calibration result.

The 2023 field-season release supplies useful environment identity, weather, soil, and management material, but under the locked B13 issuance semantics it does not currently supply the exact planting-date information needed to define the first 30 days after planting without introducing an unregistered proxy.

Consequently, B13A blocks B13B rather than silently changing the forecast clock.

No 2023 prediction artifact may be generated under the current source protocol.

## What B13A does not permit

The negative result does not permit:

- opening the phenotype file to recover planting dates;
- using phenotype-key availability to choose the prediction cohort;
- treating weather-station placement as planting;
- treating treatment/application dates as planting;
- changing the T1 horizon;
- rebuilding the genomic representation;
- reopening T2;
- tuning a new uncertainty rule on 2023.

## Next admissible research action

A separate pre-outcome source-recovery stage may search for exact 2023 planting dates only from independent, outcome-free sources with explicit provenance and exact environment mapping. That stage must be locked before any phenotype access.

If exact planting dates cannot be recovered without violating the source boundary, the 2023 external branch should close cleanly and a later external block should be considered under a newly predeclared protocol.

## Implementation and evidence

- `src/plant_intelligence/uncertainty/maize_b13_2023_source_audit.py`
- `src/plant_intelligence/uncertainty/maize_b13a_2023_source_audit_runner.py`
- `src/plant_intelligence/uncertainty/maize_b13a_2023_final_audit.py`
- `tests/test_case_study_b13a_2023_source_audit.py`
- `.github/workflows/case-study-b13a-2023-source-audit.yml`
- `reports/results/case_study_b13a_2023_source_manifest.csv`
- `reports/results/case_study_b13a_2023_environment_audit.csv`
- `reports/results/case_study_b13a_2023_genotype_audit.csv`
- `reports/results/case_study_b13a_2023_candidate_universe.csv`
- `reports/results/case_study_b13a_2023_lock_decision.csv`
