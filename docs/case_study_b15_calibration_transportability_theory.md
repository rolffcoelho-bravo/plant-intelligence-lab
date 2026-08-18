# Case Study B15 — Calibration Transportability Theory

## Status

B15 is a theory-first stage opened after the sealed B14C 2024 reveal. It does **not** modify the frozen `G+E_T1` point predictor, the B5 genomic representation, the `T1_30DAP` clock, the closed T2 branch, the B11 interval rule, or any support threshold. It does not access a new outcome season and it does not propose or tune a replacement adaptive interval.

The scientific question is narrower:

> When does a realized calibration error in one deployment domain contain identified information about calibration error in a later deployment domain, and when is carrying that error forward mathematically unjustified?

B12 and B14C motivate the question, but the definitions and theorems below are population statements that do not depend on tuning to those realized outcomes.

## 1. Population object

Fix a prediction rule, an interval/nonconformity threshold `q`, and nominal coverage

\[
\tau\in(0,1).
\]

For deployment domain or season `t`, let:

- \(Z_t\) be a pre-outcome environment state with probability law \(\mu_t\);
- \(R_t\) be the nonconformity score produced by the frozen predictor and score construction;
- \(F_t(q\mid z)=\Pr(R_t\le q\mid Z_t=z)\) be the conditional score CDF evaluated at the fixed threshold.

Population coverage is

\[
C_t(q)=\int F_t(q\mid z)\,d\mu_t(z),
\]

and the **signed calibration gap** is

\[
\Delta_t(q)=C_t(q)-\tau.
\]

Therefore:

- \(\Delta_t<0\): undercoverage;
- \(\Delta_t=0\): exact population calibration;
- \(\Delta_t>0\): overcoverage.

B15 treats \(q\) as fixed. Changing the interval after observing the target outcomes is outside this stage.

## 2. Exact calibration-transport decomposition

For source domain `s` and target domain `t`, add and subtract the source conditional score law integrated under the target environment distribution:

\[
\begin{aligned}
\Delta_t(q)-\Delta_s(q)
&= \int F_t(q\mid z)d\mu_t(z)-\int F_s(q\mid z)d\mu_s(z)\\
&= \underbrace{\int F_s(q\mid z)d(\mu_t-\mu_s)(z)}_{\Gamma^{\mathrm{mix}}_{s\to t}(q)}
 + \underbrace{\int [F_t(q\mid z)-F_s(q\mid z)]d\mu_t(z)}_{\Gamma^{\mathrm{cond}}_{s\to t}(q)}.
\end{aligned}
\]

Thus

\[
\boxed{
\Delta_t=\Delta_s+\Gamma^{\mathrm{mix}}_{s\to t}+\Gamma^{\mathrm{cond}}_{s\to t}
}
\]

exactly.

### 2.1 Mixture term

\[
\Gamma^{\mathrm{mix}}_{s\to t}(q)
=\int F_s(q\mid z)d(\mu_t-\mu_s)(z).
\]

This term asks: **what would change solely because the target season has a different mixture of environment states, if the conditional score law stayed equal to the source law?**

It is not automatically observable. Prospective estimation requires both:

1. target pre-outcome environment descriptors sufficient to estimate or approximate \(\mu_t\); and
2. adequate source support/overlap to estimate \(F_s(q\mid z)\) over the target-relevant environment region.

If target environments lie outside supported source regions, B15 does not impute the missing conditional law and call the resulting quantity identified. That unsupported component belongs in the uncertainty of the transport certificate.

### 2.2 Conditional-drift term

\[
\Gamma^{\mathrm{cond}}_{s\to t}(q)
=\int [F_t(q\mid z)-F_s(q\mid z)]d\mu_t(z).
\]

This term asks: **after accounting for the target environment mixture, did the conditional nonconformity distribution itself change?**

Before target outcomes are observed, this term is generally not identified from the past calibration gap alone. This is the source of the transportability problem.

## 3. Theorem 1 — Exact transport identity

**Theorem 1 (Calibration transport decomposition).** For any fixed threshold \(q\), nominal level \(\tau\), source conditional score CDF \(F_s\), target conditional score CDF \(F_t\), and source/target environment laws \(\mu_s,\mu_t\) for which the integrals exist,

\[
\Delta_t(q)-\Delta_s(q)
=\Gamma^{\mathrm{mix}}_{s\to t}(q)+\Gamma^{\mathrm{cond}}_{s\to t}(q).
\]

**Proof.** Starting from the difference in coverages, add and subtract \(\int F_s(q\mid z)d\mu_t(z)\):

\[
\begin{aligned}
C_t-C_s
&=\int F_t d\mu_t-\int F_s d\mu_s\\
&=\left(\int F_s d\mu_t-\int F_s d\mu_s\right)
+\left(\int F_t d\mu_t-\int F_s d\mu_t\right)\\
&=\Gamma^{\mathrm{mix}}_{s\to t}+\Gamma^{\mathrm{cond}}_{s\to t}.
\end{aligned}
\]

Subtracting the same nominal \(\tau\) from source and target coverage leaves the difference unchanged. QED.

This identity is algebraic. Its value is not that it makes shift disappear; it exposes exactly which part can potentially be learned from pre-outcome composition and which part requires a transport assumption or bound.

## 4. Theorem 2 — No free transport from past calibration error

**Theorem 2 (No-free-transport / sign non-identifiability).** Suppose a source history fixes \(F_s\), \(\mu_s\), \(\Delta_s\), and the target pre-outcome environment law \(\mu_t\). If no restriction is imposed on the target conditional score law \(F_t(q\mid z)\) beyond being a valid conditional CDF value, then the sign and magnitude of \(\Delta_t(q)\) are not identified by \(\Delta_s(q)\) and \(\mu_t\). In particular, there can exist two target worlds with identical source history and identical target environment distribution but target gaps of opposite sign.

**Constructive proof.** Consider a finite supported target domain on which the source conditional CDF has room on both sides: for some \(a>0\),

\[
a\le F_s(q\mid z)\le 1-a
\]

on target-supported states. Choose \(0<\delta\le a\) and define two admissible target conditional laws at threshold \(q\):

\[
F_t^{-}(q\mid z)=F_s(q\mid z)-\delta,
\qquad
F_t^{+}(q\mid z)=F_s(q\mid z)+\delta.
\]

Both worlds have the same \(F_s\), \(\mu_s\), past coverage history and target \(\mu_t\). Their conditional-drift terms differ by \(2\delta\):

\[
\Gamma_{s\to t}^{\mathrm{cond},-}=-\delta,
\qquad
\Gamma_{s\to t}^{\mathrm{cond},+}=+\delta.
\]

Their target gaps therefore satisfy

\[
\Delta_t^{-}=\Delta_s+\Gamma^{\mathrm{mix}}-\delta,
\qquad
\Delta_t^{+}=\Delta_s+\Gamma^{\mathrm{mix}}+\delta.
\]

Whenever \(|\Delta_s+\Gamma^{\mathrm{mix}}|<\delta\), these two target gaps have opposite signs despite identical observable pre-outcome information. Therefore neither the sign nor the appropriate direction of a calibration correction is identified without further restrictions on conditional drift. QED.

### Consequence for feedback rules

A deterministic rule of the form

\[
\text{past undercoverage}\Longrightarrow\text{widen next season}
\]

cannot be uniformly justified from past coverage error alone. Two future worlds can present the rule with the same past deficit and target covariates while requiring opposite actions. A one-sided widening rule can improve one world and overcover the other.

This is an impossibility result about **information**, not a claim that online adaptation is never useful. Adaptation can be justified when additional assumptions, labels, structural models, or valid drift bounds provide information beyond the past signed coverage error.

## 5. Theorem 3 — Bounded conditional-drift transport certificate

**Theorem 3 (Bounded transport).** If, prospectively,

\[
\sup_z |F_t(q\mid z)-F_s(q\mid z)|\le\varepsilon_{\mathrm{cond}},
\]

then

\[
|\Gamma^{\mathrm{cond}}_{s\to t}(q)|\le\varepsilon_{\mathrm{cond}}
\]

and hence

\[
\boxed{
\Delta_t(q)\in
[\Delta_s+\Gamma^{\mathrm{mix}}-\varepsilon_{\mathrm{cond}},
 \Delta_s+\Gamma^{\mathrm{mix}}+\varepsilon_{\mathrm{cond}}]
}.
\]

**Proof.** Since \(\mu_t\) is a probability measure,

\[
|\Gamma^{\mathrm{cond}}|
=\left|\int (F_t-F_s)d\mu_t\right|
\le\int |F_t-F_s|d\mu_t
\le\varepsilon_{\mathrm{cond}}.
\]

Substitute this bound into Theorem 1. QED.

The interval

\[
\mathcal C_{s\to t}
=[\Delta_s+\Gamma^{\mathrm{mix}}-\varepsilon_{\mathrm{cond}},
  \Delta_s+\Gamma^{\mathrm{mix}}+\varepsilon_{\mathrm{cond}}]
\]

is the first B15 **transport certificate**.

Its interpretation is deliberately conservative:

- if \(\sup\mathcal C_{s\to t}<0\), undercoverage is sign-identified under the stated bound;
- if \(\inf\mathcal C_{s\to t}>0\), overcoverage is sign-identified;
- if \(0\in\mathcal C_{s\to t}\), the sign is not identified and the certificate itself does not justify a signed feedback action.

B15 does not yet define how \(\varepsilon_{\mathrm{cond}}\) should be estimated in deployment. That is a separate theorem/validation problem, not a free tuning parameter.

## 6. Population transport is not sample transport

The objects above are population quantities. Empirical coverage estimates add sampling error:

\[
\widehat\Delta_s=\Delta_s+e_s,
\]

and an estimated mixture term adds estimation error:

\[
\widehat\Gamma^{\mathrm{mix}}
=\Gamma^{\mathrm{mix}}+e_{\mathrm{mix}}.
\]

A valid finite-sample/prospective certificate must therefore propagate at least three uncertainties:

1. uncertainty in the source calibration gap;
2. uncertainty in the mixture-shift term, including environment-support error;
3. uncertainty/bounds on conditional score-law drift.

B15 does **not** equate a realized empirical gap with the population state. The B11 environment-cluster bootstrap remains evidence about finite-sample uncertainty, not a proof of cross-season transport.

## 7. Why B12 → B14C is motivation, not derivation

The already-revealed evidence is:

- 2022 B12 available-case environment-balanced 90% coverage: `0.8487186682822535`, signed gap `-0.0512813317177465`;
- B13/B14 carried that deficit into adaptive semantic level `0.9512813317177465` because no admissible 2023 feedback was available;
- 2024 B14C frozen-C0 environment-balanced coverage: `0.8997721030003023`, signed gap approximately `-0.0002278969996977`;
- 2024 B14C C1 environment-balanced coverage: `0.9521031534328204`, signed gap approximately `+0.0521031534328204`;
- C0 passed the inherited 90% calibration criterion and had lower mean interval score than C1; C1 failed.

These observations falsify a simple empirical story in which the 2022 signed deficit persists monotonically into 2024. They do **not** prove the general theorem. The theorem follows from the information structure above and would hold even if B14C had produced a different numerical result.

## 8. Research claims B15 may and may not make

### B15 may claim, if the proofs and hostile audit survive

1. an exact decomposition of cross-domain calibration error into environment-mixture and conditional-score-law components;
2. a non-identifiability result showing why past signed calibration error alone cannot determine future signed calibration error;
3. a bounded-drift certificate that states sufficient information for sign-identifiable calibration transport;
4. a deployment research program for testing whether such certificates can be estimated prospectively in season-batched G×E prediction.

### B15 may not claim

- invention of conformal prediction under distribution shift;
- invention of covariate-shift weighting;
- invention of adaptive/online conformal inference;
- a universal conditional-coverage guarantee;
- that the current support score estimates \(\varepsilon_{\mathrm{cond}}\);
- that environment descriptors make conditional drift observable;
- that B12/B14C are sufficient to estimate a transport law;
- that the new certificate has already been prospectively validated;
- permission to change the frozen predictor or intervals in B15.

## 9. Locked next theorem questions

Before any B16-style prospective adaptation experiment, B15 should answer these in order:

1. **Overlap theorem:** how should unsupported target environment mass enter the transport bound?
2. **Finite-sample theorem:** how do environment-clustered uncertainty and estimated mixture shift combine with a conditional-drift bound?
3. **Testability theorem:** which parts of a proposed conditional-drift bound are falsifiable using historical season pairs without leaking future outcomes?
4. **Decision theorem:** under a proper interval loss, when does a sign-identified calibration gap actually justify changing the interval rather than retaining the simpler frozen rule?

No new adaptive competitor should be introduced until these theorem tests either survive or fail explicitly.
