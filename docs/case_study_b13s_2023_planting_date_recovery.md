# Case Study B13-S — 2023 Planting-Date Recovery Audit

## Purpose

B13-S is a strictly pre-outcome provenance audit opened only because B13A established a narrow source-interface incompatibility: the official 2023 field-season release identifies 27 environments but does not expose an explicit planting date in the four allow-listed pre-outcome source tables.

B13-S does not alter the frozen `G+E_T1` point predictor, the `T1_30DAP` clock, the merged B13 uncertainty rules, the B12 genomic representation, or the closed T2 branch. It may only recover exact planting/sowing dates from independent authoritative sources that can be mapped unambiguously to the already-audited 2023 experiment codes.

## Recovery admissibility rule

A recovered date is admissible only if all conditions hold:

1. the source field explicitly means planting date or sowing date;
2. the source is authoritative and independent of B13A's 2023 phenotype file;
3. the date maps exactly and uniquely to one of the 27 B13A `Experiment_Code` values;
4. the source provides an exact calendar date;
5. the date is not inferred from anthesis, silking, harvest, yield, phenology, weather-station placement, treatment/application timing, or another proxy;
6. no numerical phenotype or yield file is opened to construct the recovery table;
7. source path, SHA-256, field name, raw environment key, mapped B13A key, and recovery decision are recorded before any 2023 phenotype access.

## Primary recovery source

The first and preferred independent source is the official Genomes to Fields 2024 GxE Prediction Competition metadata release, DOI `10.25739/78mn-4394`.

The accompanying official data note identifies `2_Training_Meta_Data_2014_2023.csv` as the metadata file for the 2014–2023 training history. B13-S permits access to this metadata file only. Training trait/phenotype files, observed-value files, and all 2023 phenotype files remain forbidden.

This source was published after the 2023 season. Its use is therefore provenance recovery for a retrospective sealed test, not a claim that the public file was available at 2023 issuance time. A date can still be admissible because planting date itself is an issuance-time fact, provided its semantics are explicit and it is not reconstructed from outcomes.

## Mechanical source boundary

Allowed external object:

- `Training_data/2_Training_Meta_Data_2014_2023.csv`

Forbidden external objects include any path containing or basename matching:

- `Trait`;
- `Phenotyp`;
- `Observed`;
- `ANSWER`;
- `1_Training_Trait_Data_2014_2023.csv`;
- `7_Testing_Observed_Values.csv`;
- `g2f_2023_phenotypic_data.csv`.

The workflow stages the single allow-listed metadata object through anonymous CyVerse iRODS and fails if any forbidden outcome object is present in the B13-S staging directory.

## Frozen B13A universe

B13-S must read the already-merged B13A environment audit and recover dates only for its 27 environment codes. It may not expand the target environment set based on the later metadata file.

## Machine states

A complete audit must terminate in exactly one of these states:

- `B13S_2023_EXACT_PLANTING_DATES_RECOVERED`
- `B13S_2023_PARTIAL_PLANTING_DATE_RECOVERY`
- `B13S_2023_NO_ADMISSIBLE_PLANTING_DATE_RECOVERY`
- `B13S_2023_SOURCE_MAPPING_AMBIGUOUS`
- `B13S_OUTCOME_BOUNDARY_VIOLATION`

`PARTIAL_PLANTING_DATE_RECOVERY` is not permission to impute missing dates. It permits a later sealed prediction stage only for the exactly mapped recovered subset, after that subset is frozen and hashed independently of phenotype outcomes.

## Non-negotiable exclusions

B13-S does not:

- open 2023 phenotype outcomes;
- tune any prediction or calibration parameter;
- redefine `T1_30DAP`;
- use treatment/application dates as planting proxies;
- use weather-station placement as a planting proxy;
- infer planting from flowering or harvest;
- reopen T2;
- use recovered dates to select environments based on yield availability.

A failure to recover exact dates closes the current 2023 continuation path rather than changing the model clock.
