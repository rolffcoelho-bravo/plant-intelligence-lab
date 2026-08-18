# B18 — Forecast-Time Information Hypothesis Audit

## Status

B18 is a **hypothesis-first hostile novelty gate**, not a model-development stage.

It was opened only because the merged Case Study B closure permits one separate question before any further modeling:

> Does enforcing a forecast-time information set change the learnable G×E contrast operator and the external ranking of interaction-capable models relative to methods whose environmental representations contain information unavailable at the intended decision time?

The gate was locked before any model code, new prediction, new outcome access, hyperparameter search, point-model change, uncertainty tuning, B5 genomic change, T1-clock change, T2 reopening, or resealing.

The predeclared kill decision is:

`B18_FORECAST_TIME_INFORMATION_NOVELTY_REJECTED_NO_MODEL_DEVELOPMENT`

if any direct prior-art or mathematical-equivalence kill condition is met.

---

## 1. Why the broad B18 question fails the novelty gate

### Gillberg et al. (2019) is a direct collision

**DOI:** `10.1093/bioinformatics/btz197`

Gillberg et al. explicitly frame the practical G×E problem around the fact that weather from the future growth season is unavailable at prediction time. They construct an experiment in which test locations, test years and test genotypes are genuinely new and predict with historical weather rather than target-season in-season weather.

Critically for B18, they compare:

- a realistic historical-weather G×E model without in-season target-year weather;
- a non-realistic ideal G×E setting with in-season information;
- an additive `G+E` model;
- other G×E and genomic baselines.

That is already the essential architecture-versus-information comparison motivating the broad B18 question.

Therefore B18 cannot claim novelty for:

- making G×E prediction obey a forecast-time weather boundary;
- replacing unavailable future weather with historical weather;
- comparing a forecast-time-admissible predictor with an in-season oracle;
- testing interaction capacity under new years, locations and genotypes.

### de los Campos et al. (2020) occupies future-weather uncertainty

**DOI:** `10.1038/s41467-020-18480-y`

This work learns G×E from field trials, DNA and environmental covariates, then integrates historical weather and parameter uncertainty through Monte Carlo simulation to predict distributions of future cultivar performance under uncertain weather.

Therefore a B18 reformulation such as “model genotype response before the future weather is known by integrating over possible weather” is also occupied.

### Eckhoff et al. (2026) closes the modern ranking formulation

**DOI:** `10.1007/s00122-026-05280-z`

Eckhoff et al. explicitly discuss the decision-time impossibility of knowing actual future weather, use historical weather for untested future years, and target within-environment genotype differences and rankings.

Therefore narrowing B18 from yield prediction to **future genotype ranking under decision-time weather uncertainty** does not rescue novelty.

---

## 2. The architecture-versus-information decomposition

Let:

- `A0` denote a restricted architecture, such as additive `G+E`;
- `A1` denote an interaction-capable architecture;
- `F_t` denote the information legally available at the deployment decision time;
- `F_T` denote a richer later-season/oracle information set with `F_t ⊂ F_T`;
- `R(A,F)` denote predictive risk for architecture `A` under information set `F`.

The obvious decomposition is

\[
R(A_0,F_t)-R(A_1,F_T)
=
\big[R(A_0,F_t)-R(A_1,F_t)\big]
+
\big[R(A_1,F_t)-R(A_1,F_T)\big].
\]

The first term compares **architecture capacity while holding the admissible information fixed**.

The second term compares **information availability while holding the interaction-capable architecture fixed**.

This is useful experimental bookkeeping because it prevents an interaction model from receiving later-season information while an additive baseline is restricted to forecast-time information.

It is not new mathematics. It is an exact telescoping identity.

The executable B18 audit therefore classifies it as:

`BACKGROUND_IDENTITY_NOT_NOVEL`

rather than promoting it to a theorem contribution.

---

## 3. Nested information does not create a new theorem

Under squared loss, the Bayes predictor under information set `F` is the conditional expectation

\[
f_F^*(X)=\mathbb E[Y\mid F].
\]

If `F_t ⊂ F_T`, the richer information set cannot increase Bayes squared-error risk. B18 includes a finite-support executable witness in which coarse forecast-time information, partially refined information and oracle state information produce strictly decreasing Bayes risk.

This is standard conditional-expectation/information logic.

The B18 classification is therefore:

`STANDARD_CONDITIONAL_EXPECTATION_LOGIC`

not a new non-anticipation theorem.

---

## 4. Genotype ranking can change when later information arrives

B18 also records a finite contrast witness. The forecast-time expected contrast between two genotypes is positive, yet one possible later environmental state produces a negative realized contrast.

This shows why the optimal genotype ranking can be state-dependent and why later environmental information may change a ranking.

Again, this is useful for defining an honest deployment benchmark, but it is ordinary state-contingent prediction/decision behavior. It does not create a novel identification theorem.

---

## 5. The decision-value escape route also fails

A possible rescue would be to abandon prediction novelty and define the contribution as the value of weather information for cultivar choice.

That route is already occupied by, among others:

- Zhong et al. (2018), `10.1007/s10669-018-9695-4`, on risk-sensitive seed-variety yield modeling and future planting decisions;
- Kayamo et al. (2023), `10.1016/j.crm.2023.100541`, on value of seasonal forecasts for cultivar choice.

Therefore a generic “forecast-time value of information for variety selection” is not a surviving B18 methodology claim.

---

## 6. Interaction-capable architecture is not the missing novelty

The closure already established that simply adding interactions, attention, a GNN, LSTM, Transformer, reaction norm or latent factor is not a defensible B18 novelty route.

Current examples include:

- Morshedian & Domaratzki (2026), `10.1371/journal.pcbi.1013729`, with an LSTM-attention GNN and forward-time G×E evaluation;
- Li et al. (2026), `10.1016/j.fcr.2026.110593`, with cultivar-specific crop-climate fusion and phenology-aligned climate factors.

These sources reinforce the closure rule: **interaction capacity is an engineering/modeling choice, not itself the novelty.**

---

## 7. Hostile audit classification

| Candidate object | Result |
|---|---|
| Forecast-time G×E prediction without in-season weather | Direct prior-art collision |
| Historical-weather proxy for future environments | Direct prior-art collision |
| Interaction model versus in-season oracle | Direct prior-art collision |
| Future performance integrated over uncertain weather | Direct prior-art collision |
| Future genotype rankings from historical weather | Direct prior-art collision |
| Architecture-capacity vs information-risk decomposition | Exact background identity, not novel |
| Bayes-risk benefit of richer information | Standard conditional-expectation result |
| Ranking changes after future environmental state is observed | Useful witness, not new theorem |
| Value of weather information for cultivar choice | Existing value-of-information / risk-sensitive decision territory |
| Add G×E / GNN / attention / nonlinear fusion | Existing architecture territory |

No formal object survives as a distinct method or theorem.

---

## 8. Terminal B18 decision

The predeclared kill conditions are met by direct primary prior art and by mathematical equivalence of the remaining decomposition.

Machine decision:

`B18_FORECAST_TIME_INFORMATION_NOVELTY_REJECTED_NO_MODEL_DEVELOPMENT`

This means:

- **method novelty supported:** false;
- **model development permitted inside B18:** false;
- **new outcome access:** false;
- **new predictions:** false;
- **hyperparameter search:** false;
- **B14C-driven repair:** false;
- **T2 reopening:** false;
- **post-result tuning:** false.

B18 is therefore a negative novelty audit and should be retained as such.

---

## 9. Scientific value retained

The negative result is useful because it prevents a tempting but incorrect claim: that forecast-time information discipline is itself a new G×E methodology.

The stronger repository contribution remains the one established by the Case Study B closure:

1. an explicit decision-time information boundary;
2. source-compatibility auditing before external prediction;
3. immutable seal-before-reveal validation;
4. preservation of missing-source and missing-key failures;
5. external uncertainty evaluation without post-result repair;
6. mechanistic diagnosis after the confirmatory stage;
7. hostile termination of novelty claims that collide with existing theory or methods.

B18 strengthens that contribution by showing that the obvious next “novel method” route is already known territory.

---

## 10. Next research routing

B18 does not authorize B19 automatically.

The scientifically defensible next action is to return to the repository roadmap and decide between two distinct paths:

- **manuscript/productization path:** consolidate the validated Case Study B external-validation contribution without claiming a new predictive method;
- **new research-program path:** only if a genuinely different biological, statistical or decision problem is identified independently of the B14C failure and survives a fresh literature/identifiability gate.

A future interaction-capable benchmark may still be valuable as an **application benchmark**, but it would need a new predeclared external target and must be labeled non-novel unless a separate methodological contribution survives hostile audit. It is not a continuation of B18 novelty development.
