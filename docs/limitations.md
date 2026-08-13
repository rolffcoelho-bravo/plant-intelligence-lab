# Limitations

Plant Intelligence Lab is a public computational biotechnology demonstration built on real public data. Its conclusions must remain bounded by the datasets, targets, validation design, and retrospective analyses used in each case study.

## Public-data boundary

Public datasets are valuable for reproducibility and methodological demonstration, but they do not reproduce the full complexity of proprietary commercial biotechnology systems. Results from the current case studies should not be interpreted as validated performance for another species, laboratory, propagation system, breeding program, production environment, or commercial process.

## Sample size and high dimensionality

Case Study A operates with a small biological sample relative to the number of genomic markers. This creates a genuine $p \gg n$ estimation problem and increases the risk of overfitting, unstable variance-component estimation, and optimistic interpretation if validation is weak.

The repository therefore treats genotype-aware out-of-fold performance as the primary evidence and does not infer strong genomic predictability merely from the availability of millions of SNP markers.

Case Study B also uses compressed genomic representations to make the large marker spaces computationally tractable. Those low-rank representations approximate genomic relationships; they are not complete biological summaries of the genome.

## Population structure and relatedness

Genetically related accessions or hybrids can make prediction easier if close relatives appear on both sides of a train/test split. Case Study A uses genotype-aware folds. Case Study B additionally includes explicit genotype cold-start and genotype-plus-environment double-cold-start scenarios.

Even these designs do not establish prospective transfer to a different breeding population.

## Genomic-model interpretation

The weak genomic-only forecasting results in Case Study A do **not** imply that genomics is generally unimportant in plant biotechnology. They show only that, for the evaluated regeneration targets, sample, representations, and validation design, genomic information did not generate strong out-of-fold prediction and did not improve the strongest Day-15 early-phenotype forecast.

GBLUP variance-component estimates frequently reached numerical boundaries in the small sample. Near-boundary heritability estimates should therefore not be interpreted as precise biological heritability estimates.

## Phenotype quality and measurement process

No model can recover information absent from the measured phenotypes. Measurement error, batch effects, protocol execution, missing covariates, laboratory or field conditions, and biological heterogeneity can materially limit both prediction and interpretation.

## Protocol-response analysis

The current Case Study A evaluates two regeneration protocol variants. Protocol-response heterogeneity is an observed association structure, not evidence of a causal genotype-specific mechanism. The analysis should not be generalized to other protocols without new data.

## Early forecasting

The strongest Case Study A forecast uses Day-15 biological response to predict Day-21 response. This relationship is biologically plausible because the two measurements belong to the same developing process.

The result should therefore be interpreted as **early trajectory forecasting**, not as evidence that the model discovered an independent hidden biological mechanism. Features recorded after the intended prediction time must never be used in model fitting or evaluation.

## Information ablation

The Case Study A information-ablation result shows that $X_{15}$ alone outperformed the more complex genomic combinations in the current dataset. This is a data-value result for the evaluated task. It does not establish that genomic information would be unnecessary before Day 15, for different phenotypes, or in a different operational setting.

## Wheat G×E boundary

The wheat component of Case Study B shows that an explicit genomic G×E structure improves prediction under represented-environment CV-G and CV2. It does not establish that four categorical mega-environment identifiers can support transfer to a physically new environment.

The strict categorical CV-GE failure is therefore treated as a representation boundary rather than hidden as an unfavorable model result.

## Continuous-environment transfer

The Genomes-to-Fields extension gives each year-location a measurable environmental vector and therefore makes true environment cold-start prediction mathematically possible.

The first continuous-environment benchmark and the B6-R robustness stage produce favorable pooled point estimates from adding environmental information to genomics. Their paired environment-cluster intervals still cross zero. The project therefore does not claim a universal or 95%-robust unseen-environment gain.

The product $K_G\odot K_E$ interaction kernel also fails to establish a robust RMSE advantage over additive environmental transfer. It should not be interpreted as a causal G×E variance decomposition.

## Environmental novelty

B6-R finds a weak positive relationship between environmental novelty and environment-level prediction error. The highest-novelty quartile is harder on average, but the relationship is not strong enough to define a prospective abstention threshold without further validation.

Environmental distance is therefore a candidate reliability feature, not a validated operational rejection rule.

## Target-proximal environmental variables

B7 identifies five `yield_*` columns in the environmental matrix and treats them conservatively as target-proximal crop-model outputs. They are excluded from every new B7 candidate representation.

The frozen B6-R all-environment model is retained only as a sensitivity reference. Removing the five variables changes pooled RMSE by only about 0.008 in either cold-start regime, with environment-cluster intervals crossing zero.

This sensitivity result supports the narrower statement that B6-R performance is not materially dependent on those five variables. It does **not** prove that the five variables constitute direct target leakage, nor does it guarantee that every one of the remaining 197 environmental covariates is available prospectively at every intended decision time.

## Biological environmental blocks

The B7 process and phenology labels are deterministic modeling groups created from the environmental-covariate names. They improve interpretability but do not establish causal pathways.

The reproductive-transition block nearly matches the all-environment point performance, while the vegetative-only block is clearly worse under both cold-start regimes. This is evidence about predictive information timing under the evaluated representation, not evidence that one developmental stage biologically causes the observed yield response.

The equal-weight process multiple kernel has the best B7 pooled point estimate, but its paired environment-cluster interval crosses zero. It must therefore not be presented as a robust accuracy breakthrough.

## Decision-time availability of environmental information

A retrospective year-location environmental descriptor can be informative while still being unavailable when a real decision must be made. Several environmental variables summarize conditions accumulated over phenological intervals.

Consequently, a model using reproductive-stage or full-season environmental information must not be presented as a pre-season forecast unless a separate availability audit shows that all inputs are knowable at that prediction horizon. The next deployment-oriented validation should explicitly separate pre-season, early-season, and later in-season information sets.

## Uncertainty calibration

Conformal intervals are calibrated empirically on the available out-of-fold residual structure. Coverage close to nominal levels in Case Study A and the supported wheat regimes does not guarantee identical coverage after distribution shift, under new protocols, in another species, or in a prospective deployment.

## Abstention

The Case Study A abstention rule identified only four of 285 retrospective predictions as unreliable. Those four observations had substantially larger error than the retained set, but the abstained sample is too small to treat the observed error ratio as a stable general property.

The wheat uncertainty study likewise does not manufacture a hard threshold where the available reliability signals are weak. Abstention claims remain case-study-specific.

## Retrospective experiment selection

The experiment-selection module is a **retrospective acquisition benchmark**. It ranks observations whose eventual outcomes are already known to the evaluation dataset and compares the resulting enrichment with repeated random selection.

It can legitimately show that model-guided ranking concentrated high-response observations in this dataset. It does **not** demonstrate prospective laboratory savings, reduced assay counts, faster discovery, or improved real-world experimental campaigns.

Prospective validation would require recommendations to be generated before the corresponding biological outcomes are observed and then tested in an actual experimental cycle.

## Exploration versus exploitation

The EXPLOIT, EXPLORE, and BALANCED modes represent different quantitative objectives. A high uncertainty score does not mean an experiment is expected to perform well; it means the observation may be informative. A high predicted-response score prioritizes expected outcome, not information gain.

These objectives should remain explicit rather than being interpreted as one universal recommendation score.

## Causality and biological mechanism

Predictive importance, association, regression coefficients, model rankings, genomic similarity, environmental similarity, stage ablations, kernel weights, or acquisition scores do not by themselves establish causal biological mechanisms.

The repository is a prediction and decision-support project, not a causal genomics or causal environmental-mechanism study.

## Cross-species and cross-laboratory transfer

A fitted model should not be transferred unchanged across species, laboratories, protocols, breeding programs, production systems, or biological objectives. Transfer requires a new data audit, target definition, calibration assessment, and prospective validation.

## Decision support

The integrated decision architecture combines forecast, uncertainty, reliability, environmental support, and experimental objective. It is intended to support scientific prioritization, not replace biological expertise, safety controls, laboratory or breeding judgement, or operational constraints.

## GenAI

Any generative-AI interface must operate over verified data and model outputs. It should not fabricate experimental history, invent biological results, override uncertainty information, or convert retrospective evidence into unsupported claims.

## Industrial applicability

The repository demonstrates transferable computational capability. Industrial deployment would require a new assessment of the biological objective, available-at-decision-time data, measurement process, operational constraints, economics, calibration, failure modes, and prospective performance.
