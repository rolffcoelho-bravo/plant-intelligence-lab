# Case Study B13A — Blind 2023 Source and Compatibility Audit

## Purpose

B13A is a source-compatibility gate between the already-merged B13 statistical lock and any 2023 prediction seal.

It does **not** generate 2023 predictions and it does **not** read 2023 phenotypic outcomes.

The question is narrower:

> Can the public G2F 2023 field-season release support a later sealed T1 prediction stage while preserving the frozen B10/B11/B12 predictor, the merged B13 calibration rule, and a mechanically enforceable pre-outcome boundary?

## Why 2023 requires a different source protocol

The public G2F resources list a dedicated 2022 GxE prediction-competition package and a dedicated 2024 GxE prediction-competition package, but the 2023 resource is the field-season release itself (DOI `10.25739/rzzy-3n27`). Therefore B13A does not pretend that 2023 has the same submission-template/answer-file structure as B12.

The 2023 CyVerse release physically separates:

- `a._2023_phenotypic_data/`;
- `b._2023_weather_data/`;
- `c._2023_soil_data/`;
- `z._2023_supplemental_info/`.

B13A treats the entire phenotype directory as forbidden before the eventual prediction seal.

## Allowed pre-seal files

Exactly four public CSV resources are allow-listed:

- `z._2023_supplemental_info/g2f_2023_field_metadata.csv`;
- `z._2023_supplemental_info/g2f_2023_agronomic_information.csv`;
- `b._2023_weather_data/g2f_2023_weather_cleaned.csv`;
- `c._2023_soil_data/g2f_2023_soil_data.csv`.

The audit records a SHA-256 digest for each resolved safe source.

The following are forbidden during B13A:

- any path containing `a._2023_phenotypic_data`;
- `g2f_2023_phenotypic_data.csv`;
- any unregistered file not present in the explicit safe allow-list.

A forbidden path fails before an HTTP request is issued.

## Frozen B13 state

B13A verifies the merged machine-readable B13 lock before source acquisition. The required state remains:

- target year: 2023;
- point predictor: unchanged frozen `G+E_T1`;
- control interval: `FROZEN_B11_90`;
- adaptive interval: `ONE_SIDED_CLUSTER_DRIFT_GUARD_90`;
- 2023 adaptive quantile level: `0.9512813317177465`;
- primary estimand: `OFFICIALLY_OBSERVABLE_SEALED_KEYS`;
- T2 branch: closed;
- post-result tuning: prohibited.

B13A has no authority to modify these values.

## Frozen genotype universe

B13A does not rebuild genomic markers from the newer 2014–2023 genotype release.

Instead it verifies the immutable B12 prediction SHA-256 and inherits the exact unique hybrids already supported by the frozen B5 genomic representation. The expected set contains 43 hybrids.

This keeps B13A a portability audit of the existing predictor rather than a new genomic preprocessing stage.

## 2023 environment universe

The candidate environment set is built only from the safe 2023 field metadata.

An environment is T1-metadata-feasible only when the safe metadata provide:

- an environment identifier;
- planting date;
- latitude;
- longitude.

The later prediction stage will still be required to reconstruct the actual T1 state through 30 DAP and to reject environments whose complete frozen T1 context cannot be obtained.

B13A therefore tests source feasibility; it does not quietly substitute full-season realized weather into the T1 predictor.

## Candidate prediction universe

Before any 2023 phenotype key is read, B13A constructs

`frozen B12-supported genotypes × T1-metadata-feasible 2023 environments`.

That Cartesian product is sorted deterministically and hashed.

This is deliberate. B12 showed that defining a sealed cohort from a later answer-key structure can create an avoidable completeness problem. In B13, the prediction universe is frozen independently of the 2023 phenotype file. At the later reveal, the already-predeclared estimand `OFFICIALLY_OBSERVABLE_SEALED_KEYS` will intersect the sealed prediction keys with exact official phenotype-key presence. Numerical yield can never determine inclusion.

## Historical encoder reproduction

B13A reuses the B12 historical T1 encoding audit. Before any 2023 prediction stage is admitted, the candidate encoder must reproduce the frozen B10 historical T1 matrix exactly:

- identical environment order;
- identical feature columns;
- identical numeric values.

Any mismatch produces `B13A_HISTORICAL_ENCODER_MISMATCH` and blocks progression.

## Machine states

The successful state is:

`B13A_2023_SOURCE_COMPATIBLE_READY_FOR_SEAL`

Failure states include:

- `B13A_2023_SOURCE_UNRESOLVED`;
- `B13A_2023_T1_CONTEXT_INSUFFICIENT`;
- `B13A_HISTORICAL_ENCODER_MISMATCH`;
- `B13A_OUTCOME_BOUNDARY_VIOLATION`.

A compatibility failure is retained; it is not repaired by opening the phenotype file.

## What success permits

A successful B13A audit permits a later B13B Stage-A implementation to reconstruct full issuance-safe 2023 T1 states, create both locked interval competitors, generate the candidate predictions, and freeze the resulting dual-interval artifact before outcome access.

It does not itself permit outcome access.

## Implementation

- `src/plant_intelligence/uncertainty/maize_b13_2023_source_audit.py`
- `tests/test_case_study_b13a_2023_source_audit.py`
- `.github/workflows/case-study-b13a-2023-source-audit.yml`
