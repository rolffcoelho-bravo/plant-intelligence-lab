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

B7 identifies five `yield_*` columns in the environmental matrix and treats them conservatively as target-proximal crop-model outputs. They are excluded from every new B7 and B8 environmental candidate representation.

The frozen B6-R all-environment model is retained only as a sensitivity reference. Removing the five variables changes pooled RMSE by only about 0.008 in either cold-start regime, with environment-cluster intervals crossing zero.

This sensitivity result supports the narrower statement that B6-R performance is not materially dependent on those five variables. It does **not** prove that the five variables constitute direct target leakage, nor does it guarantee that every one of the remaining 197 environmental covariates is available prospectively at every intended decision time.

## Biological environmental blocks

The B7 process and phenology labels are deterministic modeling groups created from the environmental-covariate names. They improve interpretability but do not establish causal pathways.

The reproductive-transition block nearly matches the all-environment point performance, while the vegetative-only block is clearly worse under both cold-start regimes. This is evidence about predictive information timing under the evaluated representation, not evidence that one developmental stage biologically causes the observed yield response.

The equal-weight process multiple kernel has the best B7 pooled point estimate, but its paired environment-cluster interval crosses zero. It must therefore not be presented as a robust accuracy breakthrough.

## B8 decision-horizon information frontier

B8 freezes the B5 cold-start folds and B6-R outer-fold representation settings, then changes only the amount of environmental information admitted through the source phenological intervals.

The pre-season training-location history representation does not improve RMSE over genomics alone. The pre-flowering and through-`EnJFlo` current-year representations also have weaker pooled RMSE under the frozen model. The largest change occurs only when cumulative reproductive-stage information is admitted: RMSE falls by approximately **8.19%** in CV-E and **8.16%** in CV-GE relative to the immediately preceding horizon.

That reproductive-stage transition is supported by the paired environment-cluster bootstrap, with the 95% RMSE-difference interval entirely below zero in both regimes. This does **not** mean that early environmental conditions are biologically unimportant. It means the evaluated early environmental similarity representation does not translate them into lower cold-start RMSE under the frozen architecture.

The reproductive-stage point estimate is also better than the genomic-only baseline, but that broader comparison is not 95%-robust across environment clusters. The additional full-season gain beyond the reproductive-stage representation is likewise small and not robust.

## Decision-time availability and prospective interpretation

The Genomes-to-Fields ECOV table is a retrospective research object. Its APSIM environmental covariates were summarized over phenological intervals, and the source workflow calibrated year-location thermal time so simulated flowering aligned with average observed silking. Consequently, a current-year ECOV block can be restricted to columns from an early interval while still depending on retrospectively constructed source phenology.

B8 therefore labels the current-year pre-flowering, through-floral-initiation, reproductive-stage, and full-season results as **retrospective decision-horizon proxies**, not prospective deployment validation.

The B8 pre-season location-history representation is stricter with respect to the held-out year-location: it uses no held-out current-year ECOV row, and a training environment's own row is excluded from its own history proxy. However, the B5 environment folds are environment cold-start folds rather than calendar forward-chaining folds. The history result is therefore an input-availability experiment under the frozen CV design, not evidence from a real-time future forecasting trial.

A genuinely prospective extension must reconstruct environmental state using only information that exists at the forecast issuance date, such as prior climate history, soil/management variables known before planting, weather forecasts available on that date, and observed-to-date weather. It must not use future realized weather or future observed phenology to define earlier environmental states.

## Forecast-time-safe environmental reconstruction

B9 reconstructs environmental state using fixed issuance dates rather than observed future phenology. T0 excludes all current-year realized weather, while T1 and T2 use only weather observed through 30 and 60 days after planting respectively. Observed yield, harvest date, anthesis, silking, ASI, and related future-phenology fields are explicitly forbidden. The executed audit records zero future-weather and zero observed-phenology violations.

This makes B9 **forecast-time safe with respect to the information cutoff**, but it does not make the study prospective. NASA POWER observations are retrieved retrospectively and truncated at the historical issuance date. T1 and T2 are observed-to-date weather reconstructions, not archived operational weather forecasts. A true live deployment would require predictions to be issued before future outcomes occur and, if future weather forecasts are used, their historically issued forecast vintages must be preserved.

The T2 60-DAP state is a fixed calendar-time proxy and must not be described as observed reproductive stage, flowering, anthesis, or silking. Its purpose is to remove the observed-silking calibration problem exposed in B8.

The SSURGO layer is a public static soil-map representation at the resolved coordinate. It is not a plot-level soil assay and cannot represent all within-field soil heterogeneity. Management metadata are admitted only when their provenance supports availability at issuance.

B9 also registers a forward-year stress test in which every training year precedes the test year. This is stronger temporal backtesting than shuffled environment folds, but it remains retrospective historical evaluation rather than prospective field validation.

## B10 forecast-time prediction and support dependence

B10 makes the B9 chronological forward-year backtest the primary performance benchmark and freezes `G`, `G+E_T0`, `G+E_T1`, and `G+E_T2` without a new hyperparameter search.

The pooled forward-year result is non-monotonic. T0 improves over G in the point estimate, T1 is essentially tied with T0, and T2 is substantially worse. This must not be translated into a biological claim that 60-DAP weather is harmful or that later information is intrinsically detrimental.

The T2 failure is strongly heterogeneous and concentrated in the earliest forward backtests, especially 2016, when only 23 prior training environments are available. Later years have more historical environmental support and do not show the same catastrophic behavior. B10 therefore points to a support/representation problem but does not yet identify whether environmental distance, kernel bandwidth, rank, nonstationarity, location composition, or another geometry component is responsible.

The environment-cluster bootstrap supports the pooled T2 deterioration relative to T1. The year-cluster bootstrap has only six test-year clusters and is wide; it must not be presented as a precise year-level uncertainty distribution. Secondary B5 CV-E/CV-GE continuity checks cannot override a failure in the primary chronological design.

B10 remains a retrospective backtest with issuance-safe historical inputs, not a live prospective field trial. T1/T2 use observed-to-date historical weather, not archived operational forecasts.

## B10-R and B10-S spectral-geometry boundary

B10-R is a diagnostic analysis, not a post-hoc model promotion step. Its support measures are computed without yield, but its rank/bandwidth sensitivity grid is interpreted after observing held-out errors. The best diagnostic geometry therefore cannot be reported as a prospectively selected champion. The 2016 collapse is strongly geometry-sensitive, while the 2017 disadvantage persists across the tested grid; neither a single support variable nor kernel effective rank alone is established as the failure mechanism.

B10-S converts the same fixed grid into a genuinely training-only expanding-window selector. The outer-year outcome is excluded from selection, and 2016 is explicitly assigned an insufficient-history fallback. The selected T2 model nevertheless performs worse than both frozen T2 and frozen T1 in pooled forward-year prediction, with the selected-versus-frozen-T2 cluster intervals above zero. This rejects the tested historical-performance selector under the frozen design.

The B10-S result must not be generalized into a claim that adaptive geometry is impossible. It shows that expanding-window historical yield performance is not sufficiently deployment-stable here. Any future adaptive controller must be justified by a criterion that can be calculated before the outer outcome and whose temporal stability is demonstrated separately.

The oracle-regret audit remains explanatory only: its oracle configurations use the corresponding outer-year outcomes and are explicitly marked as not admitted for deployment.

## B10-T temporal ranking stability boundary

B10-T does not fit or select a new predictor. It audits the published B10-R 12-geometry RMSE ranking across the six locked forward years. The mean adjacent-year Spearman rank correlation is approximately zero, Top-3 overlap averages one third, and the annual winner persists in only one of five transitions. Reusing the previous year's winner therefore does not provide a defensible deployment rule.

A particularly important counterexample is 2019→2020 versus 2020→2021. Ranking persistence is very high in the first transition, but the next transition is strongly negative and the previous winner falls to last place. One recent stable transition cannot therefore be interpreted as evidence of future persistence.

B10-T also reports descriptive correlations between ranking inversion and outcome-free support/kernel changes. There are only five transitions. These correlations are hypothesis-generating only, are not significance claims, and must not be converted into thresholds, causal biological mechanisms, or controller admission rules.

The B10-T machine summary records `NOT_JUSTIFIED_BY_RANK_PERSISTENCE_AUDIT`. This means the current evidence rejects a rank-persistence controller; it does not prove that all adaptive environmental representations are impossible. A future method should reduce sensitivity to selecting one brittle geometry and must still be evaluated without outer-year outcome leakage.

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

Predictive importance, association, regression coefficients, model rankings, genomic similarity, environmental similarity, stage ablations, decision-horizon differences, kernel weights, or acquisition scores do not by themselves establish causal biological mechanisms.

The repository is a prediction and decision-support project, not a causal genomics or causal environmental-mechanism study.

## Cross-species and cross-laboratory transfer

A fitted model should not be transferred unchanged across species, laboratories, protocols, breeding programs, production systems, or biological objectives. Transfer requires a new data audit, target definition, calibration assessment, and prospective validation.

## Decision support

The integrated decision architecture combines forecast, uncertainty, reliability, environmental support, information horizon, and experimental objective. It is intended to support scientific prioritization, not replace biological expertise, safety controls, laboratory or breeding judgement, or operational constraints.

## GenAI

Any generative-AI interface must operate over verified data and model outputs. It should not fabricate experimental history, invent biological results, override uncertainty information, or convert retrospective evidence into unsupported claims.

## Industrial applicability

The repository demonstrates transferable computational capability. Industrial deployment would require a new assessment of the biological objective, available-at-decision-time data, measurement process, operational constraints, economics, calibration, failure modes, and prospective performance.
