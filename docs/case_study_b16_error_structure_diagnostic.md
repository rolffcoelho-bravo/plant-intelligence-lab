# Case Study B16 — Error-Structure Diagnostic

## Status

B16 is a diagnostic gate opened after B15 was terminated by prior-art equivalence. It does **not** introduce a new predictor, interval, support rule, genomic representation, forecast clock, or adaptive method. It uses only outcomes already revealed through B14C and the already-published B12 available-case diagnostic.

The question is:

> Is the remaining external prediction error primarily an environment-wide level error, or does substantial error remain after removing each environment's retrospective mean residual, indicating a within-environment genotype-ordering/interaction problem?

This distinction determines which unresolved mechanism is worth a later methodology search. It is not itself claimed as novel.

## Literature boundary

Environment-specific prediction ability, within-environment correlation, environmental similarity, and G×E prediction are established in multi-environment genomic prediction. Relevant examples include:

- Jarquín et al.-lineage G×E/environmental-covariate genomic prediction work and subsequent Genomes-to-Fields analyses;
- Rogers et al. (2022), *Environment-specific genomic prediction ability in maize using environmental covariates depends on environmental similarity to training data*, G3;
- Tolley et al. (2023), *Genomic prediction and association mapping of maize grain yield in multi-environment trials based on reaction norm models*, Frontiers in Genetics;
- the Genomes-to-Fields prediction competition analysis showing that model rankings depend materially on the chosen predictive metric.

Therefore B16 does not claim novelty for computing within-environment correlation, residual centering, or environment-specific RMSE.

## Frozen primary cohort

Primary input:

`reports/results/case_study_b14c_2024_primary_cohort.csv`

Only rows already admitted to B14C's officially observable sealed cohort are used. No new source is acquired.

Historical reference:

`reports/results/case_study_b12_2022_available_case_by_environment.csv`

B12 remains explicitly diagnostic/non-confirmatory; B16 does not upgrade its status.

## Exact error decomposition

For cell `i` in environment `e`, define the residual

\[
r_{ei}=y_{ei}-\hat y_{ei}.
\]

Let

\[
\bar r_e=\frac{1}{n_e}\sum_i r_{ei}.
\]

Then the raw sum of squared error decomposes exactly as

\[
\sum_e\sum_i r_{ei}^2
=
\underbrace{\sum_e n_e\bar r_e^2}_{\text{environment mean-bias SSE}}
+
\underbrace{\sum_e\sum_i(r_{ei}-\bar r_e)^2}_{\text{within-environment centered SSE}}.
\]

The environment-bias fraction is

\[
B_{env}
=
\frac{\sum_e n_e\bar r_e^2}{\sum_e\sum_i r_{ei}^2}.
\]

No threshold for declaring `dominant` is predeclared. B16 reports the continuous quantity.

## Oracle environment-intercept diagnostic

A retrospective diagnostic prediction is

\[
\hat y^{oracle}_{ei}=\hat y_{ei}+\bar r_e.
\]

This uses target outcomes and is **not deployable**. Its RMSE is reported only to quantify how much raw error is mathematically attributable to an environment-wide additive offset.

B16 forbids promoting this oracle correction as a model improvement.

## Within-environment structure

For every environment with sufficient nonconstant data, B16 reports:

- Pearson correlation between `predicted` and `observed`;
- Spearman rank correlation;
- observed standard deviation;
- predicted standard deviation;
- predicted/observed standard-deviation ratio;
- raw RMSE and MAE;
- environment mean residual;
- centered RMSE after removing only the retrospective environment mean residual.

Season-level summaries report cell-weighted error decomposition and unweighted distributions of environment-level correlation and dispersion diagnostics.

## B12 corroboration

The existing B12 by-environment artifact supplies 2022 environment-specific Pearson correlations, RMSE and R². B16 reports only descriptive aggregate reference quantities:

- median within-environment correlation;
- fraction of environments with negative R²;
- median environment RMSE.

The 2022 available-case diagnostic remains post-reveal and non-confirmatory.

## Locked prohibitions

B16 permits none of the following:

- access to a new outcome season;
- new external outcome acquisition;
- generation of new predictions;
- refitting or changing the frozen point predictor;
- promoting the oracle environment intercept;
- changing interval calibration;
- tuning an adaptive rule or support threshold;
- changing B5 genomics;
- changing `T1_30DAP`;
- reopening T2;
- resealing an external prediction artifact;
- claiming that this decomposition is a new methodology.

## Interpretation rule

B16's result chooses a **research question**, not a model.

If a large continuous share of SSE is attributable to environment-wide bias, a later stage may investigate the still-unresolved problem of forecast-time environment-level yield potential, but only after a hostile prior-art audit.

If substantial centered error and weak within-environment ordering remain, a later stage should instead focus on unmodeled genotype-by-environment interaction/rank instability.

If both are substantial, the next research problem must explicitly address their separation rather than hiding one inside a global RMSE.
