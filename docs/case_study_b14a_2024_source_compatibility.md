# Case Study B14A — 2024 Pre-Outcome Source Compatibility Audit

## Purpose

B14A is a strictly pre-outcome gate for the official Genomes to Fields 2024 Maize GxE Prediction Competition release (DOI `10.25739/78mn-4394`). It asks one question only: can the frozen B10/B11/B12 `G+E_T1` information state be reconstructed for a non-empty subset of the official 2024 submission universe without reading 2024 yield, changing the genomic representation, changing the `T1_30DAP` clock, tuning the point predictor, or reopening T2?

B14A generates **no yield predictions** and evaluates **no 2024 outcome**.

## External source boundary

Only two 2024 testing objects are allow-listed during B14A:

- `Testing_data/1_Submission_Template_2024.csv`
- `Testing_data/2_Testing_Meta_Data_2024.csv`

The following object is mechanically forbidden:

- `Testing_data/7_Testing_Observed_Values.csv`

Any staged file whose name contains `observed`, `answer`, `trait`, or `phenotyp` also violates the Stage-A boundary.

The official G2F data note identifies the test set as 1,063 hybrids across 23 test locations and lists the submission template, testing metadata, soil, weather, environmental-covariate and observed-value files separately. B14A intentionally stages only the submission template and testing metadata because the frozen B12 `T1_30DAP` reconstruction obtains weather only from planting through 30 DAP and uses the same SSURGO soil identity construction as the frozen historical encoder.

The submission template is used only for its `Env` and `Hybrid` keys. Its `Yield_Mg_ha` prediction column is not used in candidate-universe construction. A separate boundary audit confirmed that the 10,057-row official template contains zero non-empty `Yield_Mg_ha` values. The later `7_Testing_Observed_Values.csv` file was never staged or opened.

## Frozen genomic compatibility rule

B14A does **not** import the competition release's 2,425-SNP representation.

A 2024 hybrid is genomically supported only if its exact identifier is already present in the frozen B5 genotype matrix materialized in this repository. This is the same support rule used by B12 Stage A.

No genotype projection, marker intersection, VCF re-encoding, parent reconstruction, imputation, alias search, or post-source representation change is permitted in B14A.

## Frozen T1 rule

For a 2024 environment to be T1-feasible, the allow-listed testing metadata must provide:

1. an explicit planting/sowing-date column;
2. exactly one distinct parseable planting date for the environment;
3. usable latitude and longitude.

Weather is then reconstructed only over

`[planting date, planting date + 30 days]`

using the same NASA POWER variables and aggregation used by B12. SSURGO identity must also be available. No later weather, observed phenology, flowering, harvest, yield, weather-station placement, treatment date, or inferred planting proxy is permitted.

The historical T1 encoder must reproduce the frozen B10 representation exactly before any 2024 compatibility state can be admitted.

## Candidate universe

The official `1_Submission_Template_2024.csv` defines the only permissible genotype-environment cells.

A candidate cell is retained only when:

- its genotype is present in the frozen B5 genotype matrix; and
- its environment has a complete frozen T1 context.

The candidate universe is outcome-independent. If non-empty, its canonical sorted CSV representation is SHA-256 hashed for the next stage. B14A still does not produce predictions.

## Machine states

B14A terminates in one of:

- `B14A_2024_READY_FOR_PREOUTCOME_SEAL`
- `B14A_2024_T1_CONTEXT_INSUFFICIENT`
- `B14A_2024_NO_FROZEN_GENOMIC_OVERLAP`
- `B14A_2024_NO_JOINTLY_SUPPORTED_CELLS`
- `B14A_HISTORICAL_ENCODER_MISMATCH`
- `B14A_OUTCOME_BOUNDARY_VIOLATION`
- `B14A_2024_SOURCE_UNRESOLVED`

`READY_FOR_PREOUTCOME_SEAL` means only that a later prediction-sealing stage is technically admissible. It is not a performance result.

## Completed blind audit

The official 2024 submission template contains **10,057 genotype-environment cells**, **1,063 hybrids**, and **23 environments**.

The frozen B5 genotype matrix contains 4,372 exact hybrid vectors. Exact identifier intersection with the official 2024 submission universe retains **92 hybrids**. The competition release's newer 2,425-SNP representation was not imported.

The testing metadata expose the explicit planting field `Date_Planted` for all 23 requested environments. Twenty environments also provide the coordinates needed to define the frozen T1 weather state directly. Three environments are excluded at the metadata gate because issuance coordinates are unavailable:

- `MNH1_2024`
- `NEH3_2024`
- `SCH1_2024`

No approximate location or field-corner substitute is introduced after seeing this limitation.

Of the 20 metadata-feasible environments, 19 complete the frozen T1 reconstruction. `ONH3_2024` is excluded because the frozen SSURGO soil identity required by the historical environment encoder is unavailable there. No alternative Canadian soil representation is introduced.

The historical T1 encoder reproduces the frozen B10 values exactly, and the combined historical-plus-2024 T1 matrix is constructible without changing the feature representation.

The resulting pre-outcome candidate universe contains:

- **798 cells**
- **92 frozen-B5-supported hybrids**
- **19 T1-compatible environments**

Its canonical SHA-256 is:

`32e4f308522ee849e498d2bf0614f3ec349574a27bb327fefeb80e0f4e05bf7f`

The machine decision is:

`B14A_2024_READY_FOR_PREOUTCOME_SEAL`

This is a compatibility result only. No 2024 prediction has been generated and no 2024 observed yield has been accessed.

## Source seals

The two staged pre-outcome objects are frozen at:

- submission template SHA-256: `80969670ef0f61c16d3dcaa1c410b1f1c628a2d0ca3ad21d444236e7ce8c4178`
- testing metadata SHA-256: `10bdecd20bc15bfe7354a6b1ee39eb0b9d206f0dfe4d220386c17dea86fffdab`

## Immutable exclusions

B14A records all of the following as false:

- `observed_values_accessed`
- `prediction_generated`
- `point_predictor_changed`
- `b5_genotype_representation_changed`
- `new_2425_snp_representation_imported`
- `t1_clock_changed`
- `t2_branch_reopened`
- `post_result_tuning_permitted`

The 2024 continuation may proceed only from the frozen 798-cell universe above. B14A does not authorize expansion to unsupported genotypes or environments and does not authorize access to the observed-values file.