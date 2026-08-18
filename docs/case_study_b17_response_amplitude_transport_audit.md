# Case Study B17 — Forecast-Time Response-Amplitude Transport Audit

## Status

B17 continues directly from B16. It is an **outcome-closed mechanism/novelty audit**, not a predictor-development stage.

B16 established a mixed external failure mechanism for the frozen `G+E_T1` system on the sealed 2024 cohort: substantial environment-level offset error, substantial residual within-environment error, weak-to-moderate genotype ordering, and strong compression of predicted within-environment genotype-response amplitude. B17 asks whether that amplitude phenomenon itself offers a defensible new methodological direction.

The answer after hostile prior-art comparison is **no at the broad level**.

Machine decision:

`B17_BROAD_RESPONSE_AMPLITUDE_NOVELTY_REJECTED_OPEN_ARCHITECTURE_CONTRACTION_TEST`

No response rescaling is promoted.

## Frozen inputs

B17 uses only already-merged evidence:

- `reports/results/case_study_b14c_2024_primary_cohort.csv` — the 779 officially observable sealed 2024 cells;
- `reports/results/case_study_b16_2024_error_structure_summary.csv` — the already-published B16 decomposition.

No new season and no new external outcome source are accessed.

## Response-amplitude quantities

Within environment `e`, let

\[
y_e^c = y_e - \bar y_e\mathbf 1,
\qquad
\hat y_e^c = \hat y_e - \overline{\hat y}_e\mathbf 1.
\]

The already-used B16 amplitude ratio is

\[
a_e = \frac{s(\hat y_e)}{s(y_e)}.
\]

Values below one indicate compressed predicted spread relative to the realized target spread.

B17 also records the ordinary within-environment calibration/dispersion slope

\[
\beta_e
=
\frac{\langle \hat y_e^c,y_e^c\rangle}
{\langle \hat y_e^c,\hat y_e^c\rangle}.
\]

Whenever both standard deviations are nonzero,

\[
\beta_e
=
\rho_e\frac{s(y_e)}{s(\hat y_e)},
\]

so the slope separates two distinct ingredients: ordering/alignment through `rho_e`, and amplitude through the standard-deviation ratio. This identity is descriptive, not new theory.

## Pairwise-difference error

For residuals `f_i = y_i - z_i` inside one environment with `n` genotypes, define the ordered-pair mean squared error of differences

\[
\operatorname{MSED}
=
\frac{1}{n(n-1)}
\sum_i\sum_{j\ne i}
[(y_i-y_j)-(z_i-z_j)]^2.
\]

The exact identity is

\[
\operatorname{MSED}
=
\frac{2}{n-1}\sum_i(f_i-\bar f)^2.
\]

B17 implements this identity only to place the B16 result in the established language of within-environment genotype-difference prediction.

## Forecast-time non-identification boundary

Before target outcomes are observed, a fixed pre-outcome information state and a fixed prediction vector are compatible with multiple possible target-response amplitudes.

A finite witness is enough. Hold the prediction vector fixed and consider two admissible outcome worlds whose centered target vectors are respectively `0.5` and `2.0` times the same centered prediction vector. The pre-outcome state and prediction are identical in both worlds, but the target amplitude differs by a factor of four.

Therefore, without additional structural assumptions, the future target-response amplitude is **not distribution-free point identified** from the deployed prediction/pre-outcome state alone.

This is a boundary lemma, not a novelty claim.

## Hostile prior-art audit

The broad candidate fails because the relevant pieces are already occupied.

### 1. Within-environment difference shrinkage is explicit prior art

Eckhoff et al. (2026), *Tailoring AI and ML models for genotype-by-environment prediction leveraging environmental covariates: A European rye example*, Theoretical and Applied Genetics, DOI `10.1007/s00122-026-05280-z`, directly decomposes prediction error using within-environment pairwise genotype differences, uses MSED, and explicitly interprets the ratio of predicted and observed pairwise-difference standard deviations as shrinkage. It also reports stronger shrinkage under harder prediction schemes.

That is a direct collision with any claim that B16/B17 newly discovered or newly defined response-amplitude shrinkage in G×E prediction.

### 2. Genotype-specific response slopes in unseen environments are established

Hrachov et al. (2026), *Regression approaches for modeling genotype-environment interaction and making predictions into unseen environments*, Theoretical and Applied Genetics, DOI `10.1007/s00122-025-05103-7`, places factorial regression, random coefficient regression, environmental kernels, reduced-rank regression and extended Finlay-Wilkinson constructions in a common prediction framework for unseen environments and discusses prediction uncertainty.

Avagyan et al. (2025), *Penalized factorial regression as a flexible and computationally attractive reaction norm model for prediction in the presence of GxE*, Theoretical and Applied Genetics, DOI `10.1007/s00122-025-04865-4`, predicts genotype-specific reaction-norm slopes from environmental covariates with explicit penalization/shrinkage.

Thus “transport genotype-response amplitude/slopes to a new environment” is not a free novelty space.

### 3. Latent G×E response transport from environmental covariates is established

Hu, Rincent and Runcie (2025), *MegaLMM improves genomic predictions in new environments using environmental covariates*, Genetics, DOI `10.1093/genetics/iyae171`, learns regressions of latent environment factor loadings on environmental covariates to predict genetic values in new environments.

This occupies another broad version of environment-conditioned response transport.

### 4. Prediction dispersion and shrinkage are established validation objects

Legarra and Reverter (2018), *Semi-parametric estimates of population accuracy and bias of predictions of breeding values and future phenotypes using the LR method*, Genetics Selection Evolution, DOI `10.1186/s12711-018-0426-6`, formalizes bias, dispersion and accuracy diagnostics for breeding-value prediction.

Sahebalam and Gholizadeh (2025), *Different approaches for estimating the shrinkage factor in ridge regression BLUP for genomic selection*, Scientific Reports, DOI `10.1038/s41598-025-26193-9`, directly studies shrinkage-factor estimation in RR-BLUP genomic selection.

Therefore a generic “correct genomic prediction shrinkage” method would be a crowded and weak novelty claim.

## Scientific conclusion

The B16 under-dispersion is real and important for this deployed frozen system, but **the phenomenon and its standard diagnostics are not methodologically novel**.

B17 therefore forbids all of the following:

- post-hoc multiplying 2024 predictions by an observed amplitude factor;
- fitting an environment-specific calibration slope to 2024 and calling it deployable;
- changing ridge strength after seeing the external under-dispersion;
- introducing MSED as if it were new;
- introducing reaction-norm slopes, random coefficients or latent environment factors as if they were new;
- reopening T2, support tuning, interval tuning, B5 changes or the T1 clock;
- accessing another outcome season merely to search for a favorable rescaling rule.

## Surviving narrower hypothesis

One question remains worth a kill test:

> Can the **fixed deployed prediction operator itself**, together with the forecast-time target design and no target outcomes, yield a mathematically valid certificate or bound for architecture-imposed within-environment contraction that is distinct from standard ridge shrinkage, BLUP reliability/prediction-error variance, kernel leverage and existing G×E reaction-norm uncertainty theory?

This is deliberately narrower than amplitude calibration. The intended object would separate:

1. contraction forced by the frozen estimation/prediction operator;
2. contraction caused by poor target support or covariate geometry;
3. unknown biological/environmental response amplitude that cannot be identified pre-outcome without assumptions.

No novelty is claimed for this object yet.

## Next locked action

**B17-T1 — Architecture-Contraction Novelty Test**

Before any new model is fitted:

1. write the frozen `G+E_T1` prediction map as an explicit linear/kernel smoothing operator conditional on its already-fixed training design and hyperparameters;
2. derive the exact spectral/leverage quantities that govern attenuation of target contrasts;
3. determine which quantities are computable without target outcomes;
4. compare theorem-by-theorem against ridge/BLUP shrinkage, prediction-error variance/reliability, kernel-ridge leverage and spectral-bias theory;
5. require a strict mathematical separation from that prior art;
6. terminate the branch if the proposed certificate is only a repackaging of known smoother contraction or reliability.

No model modification is permitted unless B17-T1 survives that hostile test.
