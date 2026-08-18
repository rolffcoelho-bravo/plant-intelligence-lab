# PUB-B2 — Case Study B Manuscript Scaffold and Frozen Publication Assets

## Status

PUB-B2 is a **publication-only manuscript assembly stage** downstream of the merged PUB-B1 lock.

Parent checkpoint:

`7bd267138d8481804de393a01870278bc1492619`

Parent status:

`PUB_B1_CASE_STUDY_B_PUBLICATION_SYNTHESIS_LOCKED`

Publication frame:

`SEAL_FIRST_BLINDED_EXTERNAL_VALIDATION_AND_FAILURE_ANALYSIS_NOT_NEW_PREDICTIVE_METHOD`

PUB-B2 performs no new science. It does not acquire outcomes, generate predictions, fit or rescale models, alter B5 genomics, change `T1_30DAP`, reopen T2, tune intervals or support, reseal an experiment, repair cohorts after reveal, or authorize B19.

The sole purpose of PUB-B2 is to convert frozen evidence through B18 into an auditable paper architecture and deterministic publication assets.

---

# 1. Working manuscript identity

## Recommended title

**Seal Before Reveal: Auditable External Validation of Early-Season Genomic–Environment Prediction**

## Alternative title

**When Prediction Meets Deployment: Source Compatibility, Sealed External Validation, and Failure Analysis in Genomic–Environment Forecasting**

## Article type

Empirical computational biology / genomic prediction / reproducible external validation study.

## Central contribution

The paper does **not** introduce a new G×E estimator. Its contribution is an end-to-end external-validation discipline in which decision-time information, source compatibility, immutable prediction state, official-key observability, uncertainty evaluation, failure diagnosis, and novelty claims are all kept auditable without post-result repair.

The manuscript should repeatedly distinguish:

- predictive performance;
- deployability of the information interface;
- uncertainty transport;
- postoutcome diagnosis;
- methodology novelty.

These are related but not interchangeable scientific questions.

---

# 2. Abstract scaffold

The final abstract should use the following claim order and no stronger wording.

### Background

Genomic-environment prediction is commonly evaluated as a predictive modeling problem, but deployment additionally requires that the decision-time information state be reconstructible, prediction outputs be frozen before outcome access, missing official target keys be handled transparently, and uncertainty rules be evaluated without post-reveal repair.

### Methods

Describe the frozen early-season `G+E_T1` predictor and inherited chronological uncertainty layer, then summarize the sequence of source-compatibility gates, immutable prediction sealing, official-key reveal, confirmatory evaluation, postoutcome diagnostics, and hostile novelty audits.

### Results

The abstract may report:

- B12 primary: 420 sealed predictions, 33 official keys absent, therefore incomplete primary confirmatory evaluation;
- B12 available-case diagnostic: 387 cells, RMSE 2.8037, 90% coverage 0.8527;
- 2023: unevaluable under the frozen T1 interface because no admissible exact planting date was recoverable from the audited sources;
- B14B/B14C: 798 sealed 2024 predictions, 779 officially observable keys, RMSE 2.6197, R² 0.1484;
- frozen B11 90% rule: environment-balanced coverage 0.8998 and calibration pass;
- one-sided drift guard: environment-balanced coverage 0.9521, calibration fail, worse interval score;
- B16: mixed error structure with environment-offset SSE fraction 0.4296, within-environment SSE fraction 0.5704, and median predicted/observed SD ratio 0.2883.

### Conclusion

The conclusion should state that deployment validity depended on information provenance and sealing discipline as much as model performance, that the tested one-sided calibration feedback did not transport reliably to the next evaluable season, and that the postoutcome failure analysis exposed limitations of the frozen additive architecture without retrofitting a new method.

### Abstract wording prohibited

Do not use:

- “prospective 2024 validation” without the repository-access qualifier;
- “new G×E method”;
- “new conformal method”;
- “validated abstention mechanism”;
- “general nonmonotone calibration law”;
- “B12 confirmatory calibration failure.”

---

# 3. Introduction scaffold

## 3.1 Deployment validity is more than predictive accuracy

Open with the practical distinction between a model that can be evaluated retrospectively and a system whose required information is actually available at the intended decision time.

Core question:

> Can a genomic-environment prediction system be externally evaluated without allowing source incompatibility, missing target keys, calibration drift, or model failure to trigger post-result reconstruction of the experiment?

Use source-map claims `M01`, `M04`, `R04`, and `L03`.

## 3.2 Why environmental information creates an interface problem

Explain that early-season environmental prediction requires not only covariate values but a reproducible temporal anchor. In this program the anchor is `T1_30DAP`; without an admissible planting date, the deployment state cannot be reconstructed under the frozen protocol.

Use `R04` and `R05`.

## 3.3 Why uncertainty transport must be evaluated separately

Motivate the difference between a point predictor and an inherited residual-calibration rule. B12 supplied diagnostic evidence that the frozen 90% rule undercovered on the available official keys, motivating a pre-outcome B13 feedback experiment rather than post-reveal widening of B12.

Use `R02`, `R03`, and `M03`.

## 3.4 Contribution statement

The introduction should end with four contributions, stated narrowly:

1. an auditable source-compatibility and seal-before-reveal external-validation protocol;
2. a completed 2024 confirmatory external evaluation of a frozen early-season predictor on officially observable sealed keys;
3. a predeclared comparison showing that a simple one-sided previous-season widening rule did not outperform the frozen uncertainty control;
4. a postoutcome failure analysis and novelty audit that explain limitations without rewriting the predictive system after reveal.

Do not include algorithmic novelty among the contributions.

---

# 4. Methods scaffold

## 4.1 Frozen deployment object

State that the external program evaluates the previously frozen `G+E_T1` system at `T1_30DAP`. PUB-B2 does not re-estimate model coefficients or reconstruct an alternative genomic representation.

Primary source-map claim: `M01`.

## 4.2 B12 sealed 2022 external block

Describe the blind prediction seal, the 420-cell cohort, the immutable prediction hash, and the subsequent official-answer key mismatch.

Source-map claims: `M02`, `R01`.

## 4.3 Available-case diagnostic rule

Explain that the 387-cell B12 available-case cohort was constructed only by exact official-key presence after reveal and was explicitly non-confirmatory.

Source-map claims: `R02`, `R03`.

## 4.4 B13 pre-outcome interval protocol

Define the two locked competitors:

- `FROZEN_B11_90`;
- `ONE_SIDED_CLUSTER_DRIFT_GUARD_90`.

State the adaptive quantile level exactly:

`0.9512813317177465`.

State that the primary estimand is `OFFICIALLY_OBSERVABLE_SEALED_KEYS` and that numerical outcomes cannot determine cohort membership.

Source-map claims: `M03`, `M04`.

## 4.5 Source-compatibility gates

### 4.5.1 2023

Describe B13A and B13-S as pre-outcome source audits. No valid exact planting date was available under the frozen source boundary, so no 2023 T1 prediction cohort was sealed.

Source-map claims: `R04`, `R05`.

### 4.5.2 2024

Describe B14A as the compatibility pass that established 92 supported hybrids, 19 fully reconstructible T1 environments, and 798 candidate cells before prediction issuance.

Source-map claim: `R06`.

## 4.6 Immutable B14B 2024 prediction seal

Report:

- 798 predictions;
- 92 genotypes;
- 19 environments;
- candidate-universe SHA-256 `32e4f308522ee849e498d2bf0614f3ec349574a27bb327fefeb80e0f4e05bf7f`;
- prediction SHA-256 `91c765ea994f557db1911865309bca94ebc2110b87a5fea483a03c879d1fb19d`.

Use the design wording:

> seal-first blinded external validation relative to repository outcome access.

Source-map claim: `M05`.

## 4.7 Primary 2024 estimand and evaluation metrics

The primary cohort consists of sealed keys present in the official observed-key set. Numerical yield values do not determine inclusion. Report RMSE, MAE, R², Pearson correlation, empirical interval coverage, environment-balanced coverage, environment-cluster interval, mean half-width, and mean interval score.

Source-map claims: `R07` through `R10`.

## 4.8 Postoutcome diagnostic boundary

State explicitly that B16 is diagnostic and outcome-closed relative to future modeling: it decomposes already-revealed B14C error but does not promote an oracle correction or alter the frozen predictor.

Source-map claims: `R11`, `R12`.

## 4.9 Structural architecture audit

Present the additive identity

\[
\widehat y(g,e)=\widehat b_0+z_G(g)^\top\widehat\beta_G+z_E(e)^\top\widehat\beta_E,
\]

and therefore

\[
\widehat y(g_i,e)-\widehat y(g_j,e)
=[z_G(g_i)-z_G(g_j)]^\top\widehat\beta_G.
\]

The identity is explanatory background, not a theorem contribution.

Source-map claims: `D02`, `D03`.

## 4.10 Hostile novelty-audit protocol

Explain that proposed B15, B17, and B18 method claims were compared against existing theory and primary literature before being promoted. When equivalence or direct prior-art collision was found, the branch terminated.

Source-map claims: `D04`, `D05`, `D06`.

---

# 5. Results scaffold

## 5.1 B12: the first external seal exposed an outcome-key problem

Lead with the primary result, not the diagnostic metric:

- 420 sealed predictions;
- 387 exact official keys present;
- 33 absent;
- machine state `B12_PRIMARY_INCOMPLETE_OFFICIAL_OUTCOME_MATCH`.

Then report the separately labeled diagnostic metrics.

Use **Table 2** and source-map claims `R01`–`R03`.

## 5.2 B13/B13-S: 2023 failed at the information interface

Report:

- 27 safe metadata environments;
- zero T1-metadata-feasible environments;
- zero admissible exact planting dates recovered in B13-S;
- no 2023 prediction cohort sealed.

This subsection must say “source-interface/provenance failure,” not “model failure.”

Use source-map claims `R04`, `R05`.

## 5.3 B14A/B14B: 2024 passed the source gate and was sealed before reveal

Report the 798-cell compatible universe and immutable prediction hash.

Use **Figure 1** for chronology and source-map claims `R06`, `M05`.

## 5.4 B14C: completed 2024 external point prediction

Report:

- n = 779 officially observable sealed keys;
- 19 absent official keys;
- 92 genotypes;
- 19 environments;
- RMSE = 2.6197348509;
- MAE = 2.1234900140;
- R² = 0.1484401927;
- Pearson = 0.3909010944.

Use **Figure 2** and **Table 2**.

Interpret as modest but nontrivial external generalization.

## 5.5 The frozen 90% rule beat the predeclared one-sided feedback guard

Frozen control:

- empirical coverage 0.9139922978;
- environment-balanced coverage 0.8997721030;
- cluster CI [0.8784860752, 0.9441202836];
- mean interval score 10.5300724937;
- calibration pass.

One-sided guard:

- empirical coverage 0.9576379974;
- environment-balanced coverage 0.9521031534;
- cluster CI [0.9316040864, 0.9786058431];
- mean interval score 11.1062518828;
- calibration fail.

Use **Figure 3** and **Table 3**.

The allowed inference is the directional nontransport of this particular feedback action. Do not infer a general seasonal law.

## 5.6 B16: external failure was mixed rather than one-dimensional

Report:

- environment mean-bias SSE fraction 0.4296201954;
- within-environment centered SSE fraction 0.5703798046;
- diagnostic oracle environment-intercept RMSE 1.9785152756;
- median environment Pearson 0.2985229926;
- median environment Spearman 0.2386679001;
- median predicted/observed SD ratio 0.2882996097.

Use **Figure 4** and **Table 4**.

The oracle intercept must remain labeled retrospective and diagnostic.

## 5.7 B17: additive architecture explains part of the under-dispersion limitation

Explain that the environmental main effect cannot alter within-environment genotype contrasts in exact arithmetic. Preserve the documented float32 numerical amendment as implementation provenance.

Use source-map claims `D02`, `D03`.

## 5.8 Negative novelty results

Report B15, B17, and B18 as research-hygiene results. The purpose is to show that the project did not relabel existing conformal, robust-decision, additive-model, or forecast-time G×E ideas as new methods.

Use source-map claims `D04`, `D05`, `D06`.

---

# 6. Discussion scaffold

## 6.1 The main scientific result is a deployment-validity chain

The central discussion should argue that external validation can fail before a numerical score exists. The 2023 path demonstrates this directly: the declared information state could not be reconstructed from the allowed source interface.

## 6.2 Missing official keys are scientific evidence

Contrast B12 and B14C handling. B12 preserved the incomplete 420-cell primary seal. B13 then prospectively defined the officially observable sealed-key estimand so later missing-key handling did not require a post-reveal protocol amendment.

## 6.3 Calibration feedback can fail even when motivated by real prior undercoverage

The 2022 diagnostic signal was real within its available-case scope, but the predeclared one-sided widening action was not beneficial on the next evaluable external season. This supports caution about directional feedback from sparse seasonal calibration history.

Use `D01` only. Do not write a general theorem or seasonal law.

## 6.4 Point-model failure and interval calibration are different

The 2024 frozen interval rule passed its inherited criterion even though point prediction remained modest and the postoutcome diagnostic exposed strong under-dispersion. This distinction is important: acceptable marginal interval calibration does not imply strong environment-specific genotype ranking or amplitude recovery.

## 6.5 Why the additive architecture matters

Use B17 as a structural explanation for a specific limitation. An additive environmental main effect can shift environment-wide level but cannot modulate genotype contrasts by environment. This helps interpret the observed response-spread compression without claiming that B17 discovered new mathematics.

## 6.6 Why negative novelty audits belong in the paper

Argue that reproducible computational research should record when an appealing “new method” interpretation fails against existing theory or prior art. This is part of claim calibration, not a side note.

---

# 7. Limitations scaffold

The final manuscript must include all of the following.

1. Only B14C is a completed confirmatory external target in the B12–B18 closure span.
2. B12 primary was incomplete because of missing official keys.
3. B12 available-case evidence is diagnostic only.
4. 2023 was unevaluable under the frozen T1 information interface.
5. The 2024 execution was seal-first blinded relative to repository outcome access, not calendar-time prospective before outcomes became public.
6. The frozen point predictor showed modest external performance.
7. The current support geometry did not validate a selective-risk abstention mechanism in Case Study B.
8. B16 is retrospective postoutcome diagnosis and does not constitute a deployed correction.
9. The additive architecture cannot express environment-dependent genotype contrasts through its environmental main-effect term.
10. No new predictive-method novelty is claimed for B15, B17, or B18.

Use source-map claims `L01`–`L03` plus PUB-B1 claim ledger.

---

# 8. Reproducibility and data-provenance scaffold

The manuscript should make the following artifacts first-class references in the repository supplement:

- B12 sealed prediction hash and missing-key audit;
- B13 pre-outcome lock;
- B13A/B13-S source manifests and negative compatibility results;
- B14A candidate-universe hash;
- B14B prediction hash;
- B14C official-key audit, primary cohort, point summary, and interval summary;
- B16 diagnostic summary;
- B17 numerical amendment and structural audit;
- B18 novelty decision and literature boundary;
- PUB-B1 claim ledger and evidence hierarchy;
- PUB-B2 source map, table/figure manifests, and input/output SHA-256 asset manifest.

PUB-B2 publication assets are deterministic transformations of those frozen files and must be regenerable with:

```bash
python -m plant_intelligence.publication.case_study_b_pub_b2 --repo-root .
```

---

# 9. Main table plan

## Table 1 — Evidence hierarchy

Purpose: classify each stage as aborted confirmatory, diagnostic, pre-outcome protocol, source-interface result, immutable seal, completed confirmatory evaluation, postoutcome diagnosis, structural background, or negative novelty audit.

Generated file:

`reports/publication/case_study_b/case_study_b_pub_b2_table_01_evidence_hierarchy.csv`

## Table 2 — External validation metrics

Purpose: place the 2022 diagnostic and 2024 confirmatory metrics side by side while preserving evidence class.

Generated file:

`reports/publication/case_study_b/case_study_b_pub_b2_table_02_external_validation_metrics.csv`

## Table 3 — 2024 uncertainty comparison

Purpose: compare the frozen control with the predeclared one-sided drift guard.

Generated file:

`reports/publication/case_study_b/case_study_b_pub_b2_table_03_2024_uncertainty_comparison.csv`

## Table 4 — 2024 failure structure

Purpose: summarize the B16 postoutcome diagnostic without promoting it to a model repair.

Generated file:

`reports/publication/case_study_b/case_study_b_pub_b2_table_04_2024_failure_structure.csv`

---

# 10. Main figure plan

## Figure 1 — Protocol chronology

A publication-only chronology from B12 through PUB-B2.

Generated SVG:

`reports/publication/case_study_b/case_study_b_pub_b2_figure_01_protocol_chronology.svg`

## Figure 2 — 2024 sealed point prediction

Observed yield versus the immutable B14B prediction on the 779-cell B14C primary cohort. The figure is descriptive of the frozen confirmatory cohort only.

Generated SVG:

`reports/publication/case_study_b/case_study_b_pub_b2_figure_02_2024_external_point_prediction.svg`

## Figure 3 — 2024 uncertainty-rule comparison

Environment-balanced coverage with environment-cluster intervals for the two predeclared rules. Mean interval score and calibration-pass status are annotated.

Generated SVG:

`reports/publication/case_study_b/case_study_b_pub_b2_figure_03_2024_uncertainty_comparison.svg`

## Figure 4 — 2024 failure structure

A compact diagnostic view of environment-offset SSE fraction, within-environment SSE fraction, and predicted/observed response-spread ratio.

Generated SVG:

`reports/publication/case_study_b/case_study_b_pub_b2_figure_04_2024_failure_structure.svg`

---

# 11. Literature/source routing

PUB-B2 does not perform a new literature search. The manuscript literature map must be assembled from the already frozen primary-literature audits in:

- `docs/case_study_b15_literature_boundary.md`;
- `docs/case_study_b15_t1_prior_art_sources.md`;
- `docs/case_study_b17_response_amplitude_transport_audit.md`;
- `docs/case_study_b17_t1_architecture_contraction_novelty.md`;
- `docs/case_study_b18_forecast_time_hypothesis_audit.md`;
- `docs/case_study_b_closure_and_contribution_audit.md`.

The paper must distinguish literature used to contextualize the application from literature used to kill a novelty claim.

No reference should be added in PUB-B2 merely because it is generally relevant. PUB-B3, if approved, should first inherit this frozen literature map and only then decide whether a separate reference-verification pass is necessary.

---

# 12. PUB-B2 terminal decision

`PUB_B2_CASE_STUDY_B_MANUSCRIPT_SCAFFOLD_AND_FROZEN_ASSETS_LOCKED`

PUB-B2 locks:

- the manuscript section order;
- evidence-to-section routing;
- quantitative source authority;
- main table plan;
- main figure plan;
- publication asset generator;
- the prohibition against evidence-class upgrading;
- the prohibition against B19 or any scientific reopening.

The next publication stage is **proposed, not automatically authorized**:

`PUB-B3 — full manuscript draft from the PUB-B2 scaffold, source map, and frozen publication assets only.`

PUB-B3 requires explicit approval before execution.
