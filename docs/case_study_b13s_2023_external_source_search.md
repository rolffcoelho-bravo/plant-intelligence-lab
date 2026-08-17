# Case Study B13-S — External Authoritative Source Search

## Scope

This note records the independent public-source search performed after the primary B13-S recovery object failed to expose an explicit planting/sowing field.

The search remained strictly pre-outcome. It did not inspect the 2023 phenotype file, numerical yield values, observed-value files, or any outcome-derived phenology. The target universe remained the 27 `Experiment_Code` values frozen by B13A.

The admissibility standard remained unchanged: an external source had to provide an exact calendar planting/sowing date that could be mapped unambiguously to a frozen 2023 G2F experiment code. Month-only statements, generic location planting reports, station-placement dates, treatment/application dates, flowering dates, harvest dates, and inferred season windows were not admissible.

## Sources checked

The audit checked the following authoritative source families:

- the official Genomes to Fields resource index and 2023 release;
- the official G2F 2024 Maize GxE Prediction Competition resource and its 2014–2023 training metadata;
- CyVerse Data Commons records for the G2F 2023 and 2024 competition datasets;
- USDA Agricultural Research Service project and annual-report pages for Columbia, Missouri;
- public institutional pages and repositories associated with participating G2F collaborators at Colorado State, Delaware, Georgia, Iowa State, Illinois, Purdue, Michigan State, Minnesota, Missouri/USDA-ARS, North Carolina State, Nebraska, Cornell, Ohio State, Clemson, Texas A&M, and Wisconsin;
- exact-code public searches for representative frozen identifiers including `COH1_2023`, `IAH1_2023`, `NEH1_2023`, and `WIH1_2023`, followed by analogous searches across the frozen code list.

The official 2024 competition data note confirms that `2_Training_Meta_Data_2014_2023.csv` is the environment metadata file for the 2014–2023 training history. B13-S acquired only that metadata object. The published B13-S schema evidence shows that it contains `Year`, `Env`, `Experiment_Code`, field/location information, weather-station placement/removal fields, tillage and planter information, irrigation and comments, but no explicit planting/sowing date field.

## Located contextual evidence that remains inadmissible

A USDA-ARS Columbia, Missouri 2023 annual report states that two 2023 Genomes to Fields locations in Columbia were planted **in May**. This supports the existence and timing of the Missouri trials, but it does not give an exact calendar day and it does not uniquely map an exact day to `MOH1_2023` and `MOH2_2023`. It is therefore retained only as contextual evidence and is not used to construct T1.

No searched authoritative public source supplied an exact planting/sowing calendar date that could be mapped unambiguously to any of the 27 frozen B13A experiment codes under the locked recovery rule.

This statement is intentionally limited: the search did not locate an admissible public source. It is not a claim that no such record exists in private collaborator records, laboratory notebooks, restricted systems, or unpublished field-management logs.

## Search disposition

The external search does not change the machine result produced from the primary authoritative metadata object:

`B13S_2023_NO_ADMISSIBLE_PLANTING_DATE_RECOVERY`

No proxy date is introduced and no environment is rescued by inference.

## Consequence

Under the frozen B13/B13A/B13-S protocol, the current 2023 continuation path cannot construct the original `T1_30DAP` information state. B13B therefore remains blocked. Any later reopening would require genuinely new authoritative provenance containing exact planting dates, followed by a new pre-outcome lock before those dates were used. It may not be reopened by changing the T1 clock or by reading 2023 outcomes.
