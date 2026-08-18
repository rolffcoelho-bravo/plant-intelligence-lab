# B15 Prior-Art Equivalence / Strict-Separation Test

## Verdict

The broad B15 claim **does not survive** the first theorem-by-theorem hostile comparison.

The exact transport decomposition, unrestricted sign non-identifiability, and bounded conditional-drift certificate remain useful project lemmas, but they are **not currently defensible as standalone methodological novelty**. They are demoted from candidate contribution to background machinery.

This is a productive negative result. It prevents the project from relabeling known distribution-shift theory.

## B15 notation

For fixed threshold `q` and nominal coverage `tau`, B15 writes

\[
\Delta_t(q)=C_t(q)-\tau,
\]

with

\[
C_t(q)=\int F_t(q\mid z)d\mu_t(z),
\]

and the exact identity

\[
\Delta_t-\Delta_s
=\Gamma^{\mathrm{mix}}_{s\to t}
+\Gamma^{\mathrm{cond}}_{s\to t}.
\]

The question is whether any part of this object, or the resulting certificate, remains nontrivial after translation into the closest prior art.

## Test 1 — Qiu, Dobriban & Tchetgen Tchetgen (2023)

### Their information set

They observe labeled source data and unlabeled target covariates under unknown covariate shift. Their key identification assumption is that the conditional outcome law given covariates is invariant from source to target, together with target/source covariate overlap.

They define the target-population coverage error as an identified functional and provide both a G-computation representation and a weighted representation. They then estimate this functional with semiparametric one-step methods and construct asymptotically PAC prediction sets.

### Translation into B15 notation

Under their covariate-shift assumption,

\[
F_t(q\mid z)=F_s(q\mid z),
\]

so

\[
\Gamma^{\mathrm{cond}}_{s\to t}(q)=0.
\]

Therefore B15 reduces to

\[
\Delta_t
=\Delta_s+\Gamma^{\mathrm{mix}}_{s\to t}
=\int F_s(q\mid z)d\mu_t(z)-\tau.
\]

That is precisely the target conditional-coverage functional averaged over the target covariate law. Qiu et al. go substantially beyond this algebra by deriving identification and efficient estimation under unknown covariate shift.

### Verdict

**B15 Theorem 1 is not novel in the covariate-shift case.** It is background notation.

The B15 overlap warning is also standard in substance: Qiu et al. require dominance/overlap so the target functional is identified from source information.

## Test 2 — Ai & Ren (2024)

### Their information set

Ai and Ren explicitly distinguish shift in the covariate distribution from shift in the conditional relationship between outcome and covariates. They reweight for identifiable covariate shift and protect against conditional shift bounded by an f-divergence ambiguity set.

### Translation into B15 notation

The B15 separation

\[
\Gamma^{\mathrm{mix}}+\Gamma^{\mathrm{cond}}
\]

is a coverage-at-threshold expression of the same high-level distinction: one component changes the target covariate/environment law and another changes the conditional law.

### Verdict

**The conceptual mixture-versus-conditional decomposition is not novel.** B15 may retain its algebra because it is convenient for the season/G×E setting, but it cannot be the contribution.

## Test 3 — Correia & Louizos (2025)

### Their information set

Correia and Louizos study non-exchangeable conformal prediction through optimal transport. Their stated aim includes estimating loss in coverage and mitigating arbitrary distribution shifts using unlabeled target data, rather than assuming a single named shift family.

### Translation into B15 notation

Their target is a bound/estimate on the total quantity that B15 writes as

\[
\Delta_t(q)-\Delta_s(q).
\]

Even if their route does not use the B15 additive decomposition, an estimator or bound for total coverage loss can subsume the practical objective of a transport certificate whenever it is at least as informative.

### Verdict

**B15 cannot claim novelty for estimating or bounding cross-domain coverage loss.** A strict-separation theorem would have to show that feedback-action identification contains information not recoverable from their coverage-loss object under the same observables.

## Test 4 — Siahkali, Verma & Gupta (2026)

### Their information set

Siahkali, Verma and Gupta analyze pseudo-calibrated conformal prediction under bounded label-conditional covariate shift. They derive target coverage lower bounds in terms of source-domain classifier loss, Lipschitz properties, and Wasserstein shift magnitude. Their paper explicitly frames part of the gap as understanding how source-domain errors translate to target-domain coverage.

### Translation into B15 notation

A bound of the form

\[
C_t(q)\ge C_s(q)-B(P_s,P_t,f)
\]

immediately yields

\[
\Delta_t(q)\ge \Delta_s(q)-B(P_s,P_t,f).
\]

That is a one-sided calibration transport certificate. The exact form of their bound is classification/pseudo-calibration specific, but the mathematical role directly overlaps B15 Theorem 3: restrict target drift and propagate that restriction into a target coverage guarantee.

### Verdict

**B15 Theorem 3 is not presently novel as a generic bounded-drift certificate.** A sup-norm bound is simpler than the prior robust/domain-adaptation constructions, not a stronger contribution.

## Test 5 — B15 unrestricted no-free-transport theorem

B15 Theorem 2 says that without restrictions on the target conditional score law, past signed calibration error and target environment composition do not identify the target signed gap.

This is correct but too weak as novelty. It follows immediately from missing target-label information when the conditional target law is unrestricted, and it sits beside stronger impossibility/identification results in the unknown-shift literature. Qiu et al., for example, prove a nontrivial finite-sample negative result for PAC prediction sets under unknown covariate shift before imposing identification assumptions.

### Verdict

**B15 Theorem 2 is background impossibility logic, not a standalone contribution.**

## Formal demotion

The following B15 objects are retained but demoted:

- `B15_THEOREM_1_EXACT_CALIBRATION_TRANSPORT_DECOMPOSITION` → `BACKGROUND_LEMMA_1`;
- `B15_THEOREM_2_NO_FREE_TRANSPORT_SIGN_NONIDENTIFIABILITY` → `BACKGROUND_LEMMA_2`;
- `B15_THEOREM_3_BOUNDED_CONDITIONAL_DRIFT_TRANSPORT_CERTIFICATE` → `BACKGROUND_LEMMA_3`.

No manuscript may call these three objects the main methodological novelty without a later theorem that establishes a genuinely stronger result.

## Surviving research hypothesis

The hostile audit leaves one narrower candidate that is not yet eliminated:

> **Calibration-feedback action identifiability:** Given source calibration history and the information observable before the next season’s outcomes, determine whether the *direction and proper-loss value of changing the interval rule* are point-identified, partially identified, or non-identified.

The difference from target-coverage estimation must be mathematical, not rhetorical.

A future theorem must introduce an action `a` from a predeclared action space and a target decision criterion combining:

1. a coverage admissibility constraint; and
2. a proper interval loss or score.

For an ambiguity class \(\mathcal P(I_t)\) compatible with pre-outcome information \(I_t\), define the set of optimal actions

\[
\mathcal A^*(I_t)
=
\bigcup_{P\in\mathcal P(I_t)}
\arg\min_{a\in\mathcal A:\,C_P(a)\ge\tau} L_P(a).
\]

The correction action is **identified** only if the admissible optimal-action set collapses appropriately under the chosen identification concept. If the same pre-outcome information supports worlds in which widening, retaining, or narrowing are respectively optimal, then a past calibration gap is not an identified feedback command even if target coverage itself admits a coarse bound.

This definition is provisional. Robust decision theory and partial-identification literature may already subsume it. The next hostile audit must therefore compare it not only with conformal prediction, but also with distributionally robust decision-making and partial identification.

## Required next stage inside B15

Before overlap or finite-sample extensions, perform:

### B15-T1 — Feedback-Decision Novelty Test

1. formalize the action space without using new outcomes;
2. define proper interval loss and coverage feasibility independently of B14C results;
3. derive the action-identification set under an ambiguity class;
4. audit against robust optimization, minimax regret, partial identification and conformal risk-control literature;
5. prove either a strict-separation theorem or terminate the novelty branch.

The empirical B12/B14C evidence remains motivation only. It must not select the action space, ambiguity radius, loss weights or theorem assumptions.

## Research-state decision

`B15_BROAD_CALIBRATION_TRANSPORT_NOVELTY_REJECTED_RETAIN_BACKGROUND_LEMMAS_TEST_FEEDBACK_DECISION_IDENTIFIABILITY`

This is the scientifically preferred outcome over preserving an inflated novelty claim.
