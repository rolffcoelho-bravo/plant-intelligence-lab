# Case Study B — Closure and Scientific Contribution Audit

## Terminal status

Case Study B is closed at B17-T1.

Final machine decision:

`CASE_STUDY_B_CLOSED_EXTERNAL_VALIDATION_CONTRIBUTION_SUPPORTED_METHOD_NOVELTY_NOT_SUPPORTED_B18_SEPARATE_HYPOTHESIS_GATE_ONLY`

Publication frame:

`SEAL_FIRST_BLINDED_EXTERNAL_VALIDATION_AND_FAILURE_ANALYSIS_NOT_NEW_PREDICTIVE_METHOD`

This closure does not create a new model, access a new outcome, regenerate predictions, retune uncertainty, change the B5 genomic representation, alter `T1_30DAP`, reopen T2, reseal an external experiment, or authorize post-result tuning.

The central question is no longer whether another technical variation can be attached to Case Study B. The question is what the completed sequence actually establishes and what it does not establish.

---

## 1. What Case Study B became

Case Study B began as external temporal validation of the frozen `G+E_T1` architecture and eventually became a much stricter study of **deployment-time scientific discipline**:

1. freeze the information state;
2. establish whether the external source can reproduce that information state;
3. seal predictions before repository outcome access;
4. preserve missing-key and source-interface failures rather than repairing them after reveal;
5. evaluate uncertainty rules without changing the predictor;
6. diagnose external failure only after the confirmatory evaluation is complete;
7. terminate proposed methodological novelties when primary literature already contains equivalent theory.

This sequence has scientific value, but that value is not a newly invented G×E algorithm.

---

## 2. Evidence hierarchy

### B12 primary — aborted confirmatory external test

The B12 prediction seal contained 420 cells across 14 environments and 43 frozen-genome hybrids. The official 2022 answer contained exact keys for only 387 of those cells; 33 sealed keys were absent.

The strict primary state remains:

`B12_PRIMARY_INCOMPLETE_OFFICIAL_OUTCOME_MATCH`

The correct classification is **aborted confirmatory external test due to outcome-key incompleteness**.

It is not scientifically valid to say that the original 420-cell B12 confirmatory cohort failed calibration, because that cohort was never completely observable.

### B12 available-case — diagnostic negative calibration-transport signal

The separately labeled 387-cell available-case diagnostic produced:

- RMSE: `2.8036753860`;
- MAE: `2.2800462441`;
- R²: `0.0889886630`;
- Pearson correlation: `0.3587629265`;
- 90% empirical coverage: `0.8527131783`;
- 90% environment-balanced coverage: `0.8487186683`;
- environment-cluster 95% CI: `[0.7740271226, 0.9253777638]`;
- absolute empirical coverage gap: approximately `4.73` percentage points.

The inherited calibration criterion was not met.

This remains **diagnostic evidence**, not a completed confirmatory result.

### B13 — prospective-within-execution uncertainty-rule lock

Before any 2023 outcome access, B13 locked exactly two 90% interval competitors:

- `FROZEN_B11_90`;
- `ONE_SIDED_CLUSTER_DRIFT_GUARD_90`.

Using the already-revealed B12 diagnostic environment-balanced coverage, the one-sided guard was fixed at

`0.9512813317177465`.

B13 also repaired the B12 missing-key problem at the protocol level by prospectively defining the primary estimand as:

`OFFICIALLY_OBSERVABLE_SEALED_KEYS`.

B13 itself is therefore a **pre-outcome protocol lock**, not a 2023 performance result.

### B13A and B13-S — negative information-interface result

The 2023 target year could not reproduce the frozen `T1_30DAP` state from the allowed official pre-outcome sources because no explicit planting date was available.

B13A:

`B13A_2023_T1_CONTEXT_INSUFFICIENT`

B13-S independently searched an authoritative historical metadata source and still recovered zero admissible exact planting dates:

`B13S_2023_NO_ADMISSIBLE_PLANTING_DATE_RECOVERY`

The 2023 path was correctly closed.

This is neither a predictor failure nor an uncertainty failure. It is an **information-interface/provenance failure**: a deployment claim is meaningless if the information required by the frozen predictor cannot be reconstructed at the declared decision time.

### B14A — positive source-compatibility gate

The 2024 source differed materially from 2023 because `Date_Planted` was explicit.

Under the unchanged architecture:

- 10,057 official submission cells;
- 1,063 official hybrids;
- 23 official environments;
- 92 hybrids with exact frozen-B5 support;
- 20 environments metadata-feasible;
- 19 environments fully reconstructing the frozen T1 state;
- 798 candidate cells.

Machine state:

`B14A_2024_READY_FOR_PREOUTCOME_SEAL`

No prediction or outcome was used in this compatibility stage.

### B14B — immutable blinded seal

B14B generated exactly 798 predictions across 92 genotypes and 19 environments and committed them before repository access to the 2024 observed-values object.

Prediction SHA-256:

`91c765ea994f557db1911865309bca94ebc2110b87a5fea483a03c879d1fb19d`

Machine state:

`B14B_2024_SEALED_PREDICTIONS_READY_FOR_REVEAL`

The frozen 2022 feedback state was carried forward because 2023 produced no admissible experiment:

`NO_2023_FEEDBACK_AVAILABLE_CARRY_FORWARD_2022_DRIFT_STATE`

### B14C — completed confirmatory external anchor

B14C is the only completed confirmatory external evaluation in the B12–B17 closure span.

Primary estimand:

`OFFICIALLY_OBSERVABLE_SEALED_KEYS`

Of the 798 sealed cells, 779 had official outcome keys. Nineteen did not. Selection depended only on key presence, never on the numerical yield.

Point prediction:

- n: `779`;
- environments: `19`;
- genotypes: `92`;
- RMSE: `2.6197348509`;
- MAE: `2.1234900140`;
- R²: `0.1484401927`;
- Pearson correlation: `0.3909010944`.

The point predictor was not changed after these values were observed.

#### B14C interval result

Control `FROZEN_B11_90`:

- empirical coverage: `0.9139922978`;
- environment-balanced coverage: `0.8997721030`;
- cluster CI: `[0.8784860752, 0.9441202836]`;
- mean half-width: `4.3517074116`;
- mean interval score: `10.5300724937`;
- inherited calibration criterion: **pass**.

Adaptive `ONE_SIDED_CLUSTER_DRIFT_GUARD_90`:

- empirical coverage: `0.9576379974`;
- environment-balanced coverage: `0.9521031534`;
- cluster CI: `[0.9316040864, 0.9786058431]`;
- mean half-width: `5.1412293605`;
- mean interval score: `11.1062518828`;
- inherited calibration criterion: **fail**.

The control rule passed and had the lower interval score. The one-sided carry-forward guard over-widened the 2024 intervals and was rejected.

The frozen terminal label `B14C_BOTH_INTERVAL_RULES_PASS_KEEP_FROZEN_B11` contains a legacy naming defect and must never be interpreted literally. The authoritative stored booleans are:

- `control_calibration_pass = true`;
- `adaptive_calibration_pass = false`.

No label was renamed after reveal because that would have changed the predeclared state machine after outcome access.

---

## 3. The strongest empirical result

The uncertainty result is more interesting than a simple claim of undercoverage.

B12 available-case diagnostic:

`environment-balanced coverage = 0.8487186683`

B14C frozen control:

`environment-balanced coverage = 0.8997721030`

B14C one-sided guard:

`environment-balanced coverage = 0.9521031534`

The 2022 diagnostic signal did not transport monotonically. A simple rule that reacted to previous undercoverage by permanently widening the next season over-corrected in 2024 and lost interval-score efficiency.

The defensible scientific statement is:

> Under this frozen deployment architecture and information boundary, realized seasonal calibration error was not sufficiently direction-stable for a one-sided previous-season correction to transport reliably.

The stronger statement that calibration drift is always nonmonotone is not supported.

---

## 4. B15 — why no new conformal method emerged

B15 asked whether the B12/B14C behavior could support new calibration-transport theory.

The broad transport decomposition, sign-nonidentifiability result, and bounded conditional-drift certificate were all demoted to background lemmas after direct comparison with prior work on target coverage under distribution shift, robust conformal inference, optimal-transport views of coverage loss, and source-to-target coverage bounds.

B15-T1 then formalized interval-feedback decisions as an ambiguity-set decision problem. That object collapsed into established partial-identification, robust-decision, minimax-regret, and conformal decision theory.

Terminal state:

`B15_T1_FEEDBACK_DECISION_NOVELTY_REJECTED_TERMINATE_B15`

This is a positive research-hygiene result: the repository contains enough formalism to explain why the tempting novelty claim is not defensible.

---

## 5. B16 — what failed in the 2024 point predictor

B16 used only the already-revealed B14C cohort and decomposed the 2024 squared error exactly into environment-wide mean offsets and centered within-environment error.

On 779 cells:

- environment mean-bias SSE fraction: `0.4296201954`;
- within-environment centered SSE fraction: `0.5703798046`;
- retrospective oracle environment-intercept RMSE: `1.9785152756`;
- oracle RMSE reduction fraction: `0.2447650666`;
- median within-environment Pearson: `0.2985229926`;
- median within-environment Spearman: `0.2386679001`;
- median predicted/observed within-environment SD ratio: `0.2882996097`.

The failure is therefore mixed:

1. substantial environment-level yield-potential error;
2. even more squared error remaining within environments;
3. weak-to-moderate genotype ordering;
4. severe compression of predicted genotype spread.

The outcome-dependent oracle intercept is diagnostic only and was never promoted.

B16 does not introduce a new decomposition methodology.

---

## 6. B17 and B17-T1 — structural explanation without novelty inflation

B17 tested whether response-amplitude transport could become a new method. It could not.

The 2026 primary literature directly occupies within-environment genotype-difference prediction, shrinkage/dispersion diagnostics, reaction norms, unseen-environment regression, and environment-conditioned latent-factor transport.

B17-T1 then isolated a sharper architectural fact.

For the deployed additive model

\[
\widehat y(g,e)=\widehat b_0+z_G(g)^\top\widehat\beta_G+z_E(e)^\top\widehat\beta_E,
\]

the predicted contrast of two genotypes in the same environment is

\[
\widehat y(g_i,e)-\widehat y(g_j,e)
=[z_G(g_i)-z_G(g_j)]^\top\widehat\beta_G.
\]

The environmental main effect cancels. In exact arithmetic, the architecture cannot change the predicted contrast of a genotype pair with environment.

Ridge regularization then contributes the separate, standard spectral attenuation factor

\[
\frac{\sigma_k^2}{\sigma_k^2+\alpha}.
\]

Neither object is new theory.

B17-T1 therefore closes with:

`B17_T1_ARCHITECTURE_CONTRACTION_NOVELTY_REJECTED_TERMINATE_B17`

The float32 implementation audit and its preserved first-run numerical failure remain part of B17-T1 provenance and do not alter this conclusion.

---

## 7. Current primary-literature boundary

The literature audit is frozen at **18 August 2026** and uses primary sources for the novelty boundary.

### G2F benchmark context

**Washburn et al.** — `10.1093/genetics/iyae195`

The earlier G2F competition compared diverse modeling strategies and allowed a small number of leaderboard/test submissions with feedback. This matters because Case Study B's repository protocol is stricter than repeated leaderboard adaptation, but stricter evaluation discipline is not automatically a new statistical method.

**Chen et al.** — `10.1186/s13104-026-07629-5`

The official 2024 resource states that 2024 observed yield was unavailable to competition participants but is now included for post-competition validation.

This creates an essential wording boundary for our manuscript:

> The 2026 B14B/B14C execution was **seal-first and blinded with respect to repository outcome access**, but it was not calendar-time prospective before the 2024 outcomes became public.

Calling it simply “prospective 2024 validation” would overstate the design.

### Interaction-capable G×E methods are already crowded

**Hu et al.** — `10.1093/genetics/iyae171`

MegaLMM predicts new environments by regressing latent environment factor loadings on environmental covariates.

**Xavier et al.** — `10.1093/genetics/iyae179`

MegaLMM, MegaSEM, extended factor-analytic and other scalable covariance structures directly capture complex G×E patterns.

**Avagyan et al.** — `10.1007/s00122-025-04865-4`

Penalized factorial regression provides flexible reaction-norm G×E prediction.

**Hrachov et al.** — `10.1007/s00122-025-05103-7`

Regression approaches explicitly target prediction into unseen environments.

**Morshedian & Domaratzki** — `10.1371/journal.pcbi.1013729`

A 2026 LSTM-attention GNN jointly models genotype and environment and evaluates a forward-time 2014–2021/2022 split with unseen genotypes and environments.

Therefore a B18 whose novelty statement is merely “add interactions,” “use a nonlinear model,” “use attention,” “use a GNN,” or “test in a future year” fails before implementation.

### Response differences and temporal information are also occupied

**Eckhoff et al.** — `10.1007/s00122-026-05280-z`

Target/loss engineering explicitly optimizes within-environment genotype differences and discusses shrinkage of predicted differences.

**Rogers et al.** — `10.1093/g3journal/jkab440`

Environment-specific maize genomic prediction with environmental covariates depends on environmental similarity to training data.

**Kick et al.** — `10.1093/g3journal/jkad006`

Deep learning integrates genomic, soil, weather and management data and permits interactions between modalities; early post-planting weather time points were already found highly salient.

**Adak et al.** — `10.1093/plphys/kiag344`

The July 2026 study integrates temporal phenomics, genomics and environmental indices, searches days-after-planting windows, and predicts across environments.

Therefore simply truncating the weather history at an earlier DAP is not enough to create B18 novelty.

---

## 8. What is publication-grade in Case Study B

### Strong enough to be central

#### A. Seal-first blinded external-validation discipline

Case Study B contains a rare, unusually strict end-to-end chain:

source compatibility → immutable candidate universe → prediction seal → hash verification → reveal → no silent missing-key deletion → no post-result tuning.

This is a **research-design and reproducibility contribution**.

It should be presented as such, not as a new estimator.

#### B. External 2024 point and interval evidence

B14C is a genuine completed external evaluation of the frozen system under the repository's pre-reveal protocol.

The result is neither spectacular nor trivial. The point model generalizes nontrivially but modestly, while the frozen uncertainty rule performs much better than the naive seasonal feedback correction.

#### C. Failure analysis that remains faithful to the frozen experiment

B16/B17 explain why the external result is not reducible to a single calibration or environment-mean problem.

The scientific narrative becomes stronger because the analysis does not rewrite the model after failure.

### Valuable but secondary

- the 2023 source-interface closure;
- the B12 diagnostic external signal;
- the exact provenance guards;
- the negative novelty audits.

These are unusually useful for transparency and methodological discipline, but they should support the paper rather than be oversold as standalone inventions.

### Not publication-grade as novelty claims

- one-sided drift guard as a new conformal method;
- support abstention as a validated selective predictor;
- response-amplitude shrinkage as a new concept;
- architecture contraction as new theory;
- additive G+E limitation as new theory;
- ordinary ridge spectral attenuation;
- post-hoc environment intercept correction.

---

## 9. Recommended manuscript identity

A defensible paper is not:

> A new state-of-the-art genomic prediction algorithm.

The strongest identity is closer to:

> **Seal-first external validation of early-information maize G×E prediction: calibration transport failure, source-interface constraints, and structural under-dispersion.**

The paper would make four linked contributions:

1. an auditable blinded external-validation protocol under a fixed decision-time information set;
2. a completed 2024 external test of a frozen point-and-uncertainty system;
3. negative evidence against a simple previous-season calibration-feedback rule;
4. a mechanistic diagnosis showing that residual failure includes both environment-level and within-environment G×E components.

That is a coherent scientific contribution even though the predictor itself is not novel.

For a high-end methods journal, this is probably insufficient **as a methods paper** without a genuinely new method or theorem. For a strong genetics/plant-breeding/computational-agriculture paper centered on external validation, reproducibility and model failure, it is much more credible.

No journal acceptance claim is made by this audit.

---

## 10. B18 gate

B18 does **not** open automatically.

### Forbidden B18 starts

B18 may not begin with:

- “add G×E interactions”;
- “use a GNN/Transformer/LSTM”;
- “retune ridge because B16 showed under-dispersion”;
- “learn a 2024 amplitude correction”;
- “repair 2024 environment means”;
- “choose a better support threshold”;
- “use full-season weather because it improves the revealed 2024 result.”

Those are either established ideas or post-result repairs.

### The only B18 route currently permitted

A separate **B18 hypothesis and novelty audit** may be opened before model coding.

The candidate question should be sharper:

> **Does enforcing a forecast-time information set change the learnable G×E contrast operator and the external ranking of interaction-capable models relative to methods whose environmental representations contain information unavailable at the intended decision time?**

This question is not yet declared novel.

Its purpose would be to distinguish **predictive architecture capacity** from **information-time admissibility**.

The B18 gate would have to answer, before fitting a new model:

1. What exactly is the deployment decision time?
2. Which environmental variables are measurably available by that time?
3. How is leakage from later-season weather, phenology, remote sensing or management prevented?
4. Is there existing theory or empirical work on information-set-constrained G×E prediction that makes the proposed contribution redundant?
5. Can a theorem or estimand distinguish the value of interaction capacity from the value of simply observing more of the season?
6. What future sealed external target can evaluate the resulting hypothesis without using B14C to select the winning architecture?

Only if that gate survives should B18 become a model-development project.

---

## 11. Final closure

Case Study B is scientifically successful in a narrower and more defensible sense than a novel-algorithm claim.

It establishes that:

- external validation can be made auditable and outcome-sealed even on public retrospective resources;
- information-source compatibility is part of deployability, not clerical preprocessing;
- calibration error from one season does not justify a directional next-season correction without stronger transport assumptions;
- the frozen 2024 point predictor generalizes only modestly;
- its external failure is mixed rather than attributable to a single offset or calibration defect;
- the additive `G+E_T1` architecture cannot represent environment-specific genotype contrast modulation in exact arithmetic;
- the obvious theoretical and response-amplitude novelty routes are already occupied by prior art.

The correct terminal state is therefore:

**close Case Study B, preserve its external-validation contribution, reject algorithmic/method novelty inflation, and permit B18 only as an independent hypothesis-first research program.**
