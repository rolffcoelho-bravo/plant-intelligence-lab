# B15 Hostile Audit Addendum — Close Prior Art Found

## Revised verdict

The initial B15 decomposition is mathematically valid, but **novelty is not established**. A second hostile search found work materially closer to the target-coverage transport question than the first boundary pass. B15 must therefore pass a formal equivalence/separation test before any publication-level novelty claim is allowed.

This addendum is binding on the B15 theory lock.

## 1. Qiu, Dobriban and Tchetgen Tchetgen (JRSSB 2023)

**Prediction sets adaptive to unknown covariate shift** studies the true target-population coverage error when the covariate shift is unknown. It develops estimators of that target coverage functional and asymptotically PAC prediction sets using semiparametric one-step methods.

### Threat to B15

This work already treats target coverage error as an estimand under source-to-target distribution change. Therefore B15 cannot claim novelty for merely:

- defining target calibration/coverage error;
- expressing target coverage as an integral over target covariates;
- estimating a target coverage functional under covariate shift;
- saying that unknown shift creates uncertainty in target coverage.

### Possible separation still requiring proof

Qiu et al. focus on target coverage under **covariate shift** and construction of prediction sets. B15's candidate narrower question is whether a **realized source signed calibration error should be used as a directional feedback signal for a future season when conditional score-law drift is not identified**. That distinction is only meaningful if it yields a theorem not reducible to their target-coverage functional plus a standard decision rule.

## 2. Correia and Louizos (2025)

**Non-exchangeable Conformal Prediction with Optimal Transport: Tackling Distribution Shifts with Unlabeled Data** explicitly proposes estimating loss in conformal coverage under arbitrary distribution shifts using optimal transport and mitigating that loss with unlabeled data.

### Threat to B15

This is closer than ordinary covariate-shift conformal prediction because it directly targets coverage degradation under nonexchangeability and general shift. B15 cannot claim that estimating or bounding coverage loss under distribution shift is new.

### Required equivalence test

B15 must determine whether its proposed transport certificate can be written as a direct special case, relaxation or corollary of an optimal-transport coverage-loss bound. If yes, the certificate is not a standalone methodological contribution.

## 3. Siahkali, Verma and Gupta (2026)

**Coverage Guarantees for Pseudo-Calibrated Conformal Prediction under Distribution Shift** is the strongest direct threat found in this pass. The paper explicitly states that existing conformal methods under shift do not explain how source-domain errors translate to the target domain, then imports domain-adaptation theory to derive target coverage bounds in terms of source-domain loss and a Wasserstein measure of shift.

### Threat to B15

The language and objective overlap directly with the phrase “source error transport”. The paper also defines coverage gaps under source/target score distributions and derives quantitative target-coverage guarantees under bounded shift.

B15 therefore cannot claim novelty for:

- asking how source errors translate to target coverage;
- deriving a target coverage bound from source error plus a shift radius;
- inflating a conformal threshold because a bound predicts coverage loss;
- using a Wasserstein-style drift bound as a transport certificate.

### Candidate separation still requiring proof

The potentially distinct object is not “target coverage bound”. It is the **decision-identifiability of a feedback action based on a previously realized signed calibration gap**, especially when:

1. seasons are batched rather than online;
2. target environment composition is partly observable before labels;
3. conditional score-law drift remains unidentified;
4. the action is evaluated under both a coverage constraint and a proper interval loss;
5. abstention/no-update is an admissible decision when the direction of correction is not identified.

This distinction is only useful if a formal decision theorem establishes something not already implied by robust/optimal-transport coverage bounds.

## 4. Ai and Ren (ICML 2024)

**Not all distributional shifts are equal: Fine-grained robust conformal inference** already separates covariate-distribution shift from conditional-distribution shift and protects against bounded conditional shift.

### Threat to B15

The B15 `Gamma_mix + Gamma_cond` decomposition cannot be advertised as conceptually novel simply because it separates environment composition from conditional score-law drift. That separation is already established in robust conformal inference.

The decomposition remains useful as project notation and as a bridge to G×E deployment, but by itself it is not a novelty result.

## 5. Revised B15 contribution test

B15 survives only if the following stronger object can be established:

> **Calibration-feedback transportability:** Given source calibration history and the pre-outcome information available for a future deployment domain, characterize whether the *direction and decision value of a calibration correction* are identified, partially identified, or non-identified under an explicit proper-loss objective and coverage constraint.

This differs from merely estimating target coverage if all of the following can be shown:

- two target domains can share the same admissible pre-outcome information and target-coverage bounds yet imply different optimal feedback actions under proper interval loss;
- a no-update/abstain action is minimax-optimal over a nontrivial ambiguity class when correction direction is not identified;
- when additional transport assumptions shrink the ambiguity class, a correction becomes uniquely action-identifiable;
- the resulting decision certificate has operational content in season-batched G×E deployment that is not a restatement of existing robust CP.

These are theorem targets, not established results.

## 6. Immediate kill test before further theorem expansion

The next B15 action must be a **prior-art equivalence or strict-separation test**:

1. write the Qiu et al. target-coverage functional in B15 notation;
2. write the Correia–Louizos coverage-loss bound in B15 notation;
3. write the Siahkali–Verma–Gupta source-loss/shift target-coverage bound in B15 notation;
4. write the Ai–Ren covariate/conditional shift decomposition in B15 notation;
5. determine whether B15 Theorems 1–3 add any nontrivial statement after those translations;
6. if not, demote Theorems 1–3 to background lemmas and move the research target to the proper-loss feedback decision theorem;
7. if the decision theorem is also a standard robust-decision corollary, terminate B15 rather than relabel it.

No new adaptive competitor, tuning parameter or 2025/2026 outcome may be introduced to rescue the theory.

## Revised novelty status

`NOT_ESTABLISHED_CLOSE_PRIOR_ART_REQUIRES_EQUIVALENCE_TEST`

That status is intentionally stronger than “candidate novelty.” It prevents the repository from presenting B15 as novel before the closest known results have been translated theorem-by-theorem.

## Added references

- Qiu, Hongxiang, Edgar Dobriban, and Eric Tchetgen Tchetgen. 2023. *Prediction sets adaptive to unknown covariate shift*. Journal of the Royal Statistical Society Series B 85(5):1680–1705. DOI: 10.1093/jrsssb/qkad069.
- Correia, Alvaro H. C., and Christos Louizos. 2025. *Non-exchangeable Conformal Prediction with Optimal Transport: Tackling Distribution Shifts with Unlabeled Data*. arXiv:2507.10425.
- Siahkali, Farbod, Ashwin Verma, and Vijay Gupta. 2026. *Coverage Guarantees for Pseudo-Calibrated Conformal Prediction under Distribution Shift*. arXiv:2602.14913.
- Ai, Jiahao, and Zhimei Ren. 2024. *Not all distributional shifts are equal: Fine-grained robust conformal inference*. ICML, PMLR 235:641–665.
