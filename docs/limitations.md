# Limitations

Plant Intelligence Lab is a public computational biotechnology demonstration built on real public data. Its conclusions must remain bounded by the datasets, targets, validation design, and retrospective analyses used in each case study.

## Public-data boundary

Public datasets are valuable for reproducibility and methodological demonstration, but they do not reproduce the full complexity of proprietary commercial biotechnology systems. Results from the current *Arabidopsis thaliana* case study should not be interpreted as validated performance for another species, laboratory, propagation system, production environment, or commercial process.

## Sample size and high dimensionality

Case Study A operates with a small biological sample relative to the number of genomic markers. This creates a genuine $p \gg n$ estimation problem and increases the risk of overfitting, unstable variance-component estimation, and optimistic interpretation if validation is weak.

The repository therefore treats genotype-aware out-of-fold performance as the primary evidence and does not infer strong genomic predictability merely from the availability of millions of SNP markers.

## Population structure and relatedness

Genetically related accessions can make prediction easier if close relatives appear on both sides of a train/test split. Case Study A uses genotype-aware folds to reduce this risk. Even so, performance on these folds is not equivalent to prospective deployment on a different genetic population.

## Genomic-model interpretation

The weak genomic-only forecasting results in Case Study A do **not** imply that genomics is generally unimportant in plant biotechnology. They show only that, for the evaluated regeneration targets, sample, representations, and validation design, genomic information did not generate strong out-of-fold prediction and did not improve the strongest Day-15 early-phenotype forecast.

GBLUP variance-component estimates frequently reached numerical boundaries in the small sample. Near-boundary heritability estimates should therefore not be interpreted as precise biological heritability estimates.

## Phenotype quality and measurement process

No model can recover information absent from the measured phenotypes. Measurement error, batch effects, protocol execution, missing covariates, laboratory conditions, and biological heterogeneity can materially limit both prediction and interpretation.

## Protocol-response analysis

The current case study evaluates two regeneration protocol variants. Protocol-response heterogeneity is an observed association structure, not evidence of a causal genotype-specific mechanism. The analysis should not be generalized to other protocols without new data.

## Early forecasting

The strongest current forecast uses Day-15 biological response to predict Day-21 response. This relationship is biologically plausible because the two measurements belong to the same developing process.

The result should therefore be interpreted as **early trajectory forecasting**, not as evidence that the model discovered an independent hidden biological mechanism. Features recorded after the intended prediction time must never be used in model fitting or evaluation.

## Information ablation

The information-ablation result shows that $X_{15}$ alone outperformed the more complex genomic combinations in the current dataset. This is a data-value result for the evaluated task. It does not establish that genomic information would be unnecessary before Day 15, for different phenotypes, or in a different operational setting.

## Uncertainty calibration

Conformal intervals are calibrated empirically on the available out-of-fold residual structure. Coverage close to nominal levels in this case study does not guarantee identical coverage after distribution shift, under new protocols, in another species, or in a prospective laboratory deployment.

## Abstention

The current abstention rule identified only four of 285 retrospective predictions as unreliable. Those four observations had substantially larger error than the retained set, but the abstained sample is too small to treat the observed error ratio as a stable general property.

The abstention result should therefore be reported as a case-study finding rather than a universal performance claim.

## Retrospective experiment selection

The experiment-selection module is a **retrospective acquisition benchmark**. It ranks observations whose eventual outcomes are already known to the evaluation dataset and compares the resulting enrichment with repeated random selection.

It can legitimately show that model-guided ranking concentrated high-response observations in this dataset. It does **not** demonstrate prospective laboratory savings, reduced assay counts, faster discovery, or improved real-world experimental campaigns.

Prospective validation would require recommendations to be generated before the corresponding biological outcomes are observed and then tested in an actual experimental cycle.

## Exploration versus exploitation

The EXPLOIT, EXPLORE, and BALANCED modes represent different quantitative objectives. A high uncertainty score does not mean an experiment is expected to perform well; it means the observation may be informative. A high predicted-response score prioritizes expected outcome, not information gain.

These objectives should remain explicit rather than being interpreted as one universal recommendation score.

## Causality and biological mechanism

Predictive importance, association, regression coefficients, model rankings, genomic similarity, or acquisition scores do not by themselves establish causal biological mechanisms.

The repository is a prediction and decision-support project, not a causal genomics study.

## Cross-species and cross-laboratory transfer

A fitted model should not be transferred unchanged across species, laboratories, protocols, production systems, or biological objectives. Transfer requires a new data audit, target definition, calibration assessment, and prospective validation.

## Decision support

The integrated decision engine combines forecast, uncertainty, reliability, and experimental objective. It is intended to support scientific prioritization, not replace biological expertise, safety controls, laboratory judgement, or operational constraints.

## GenAI

Any future generative-AI interface must operate over verified data and model outputs. It should not fabricate experimental history, invent biological results, override uncertainty information, or convert retrospective evidence into unsupported claims.

## Industrial applicability

The repository demonstrates transferable computational capability. Industrial deployment would require a new assessment of the biological objective, available data, measurement process, operational constraints, economics, calibration, failure modes, and prospective performance.
