# Case Study B15 — Hostile Literature and Novelty Boundary

## Purpose

B15 must not obtain novelty by renaming established conformal-prediction ideas. This note defines the prior-art boundary that the calibration-transportability theory must survive before any methodological novelty claim is made.

The audit is deliberately hostile: if an existing framework already solves the same mathematical problem under comparable information, B15 should be narrowed or abandoned rather than advertised as new.

## 1. Covariate shift is established territory

Tibshirani, Barber, Candès and Ramdas (2019), **Conformal Prediction Under Covariate Shift**, extend conformal prediction using likelihood-ratio weighting when the covariate distribution changes while the relevant conditional mechanism is stable. This already establishes that observable changes in deployment covariates can sometimes be corrected by reweighting.

**Boundary for B15:** the mixture term

\[
\Gamma^{\mathrm{mix}}_{s\to t}
=\int F_s(q\mid z)d(\mu_t-\mu_s)(z)
\]

must not be sold as a reinvention of covariate-shift weighting. Its role in B15 is diagnostic: it isolates the part of a calibration change attributable to deployment composition so that the remaining conditional-score drift is exposed.

## 2. Distribution drift beyond exchangeability is established territory

Barber, Candès, Ramdas and Tibshirani (2022), **Conformal Prediction Beyond Exchangeability**, develop weighted/randomized conformal tools that degrade gracefully under nonexchangeability and distribution drift.

**Boundary for B15:** B15 does not claim that distribution drift invalidates ordinary exchangeable conformal guarantees as a new observation, nor that weighting recent observations is new.

## 3. Online adaptive conformal inference is established territory

Gibbs and Candès (2021), **Adaptive Conformal Inference Under Distribution Shift**, adapt a coverage-control parameter online and obtain long-run coverage-frequency guarantees under arbitrary distribution evolution.

Gibbs and Candès (2022), **Conformal Inference for Online Prediction with Arbitrary Distribution Shifts**, add locally adaptive regret control.

Zaffran et al. (2022), **Adaptive Conformal Predictions for Time Series**, analyze ACI in dependent time-series settings and propose parameter-free expert aggregation (AgACI).

Bhatnagar et al. (2023), **Improved Online Conformal Prediction via Strongly Adaptive Online Learning**, target coverage and regret over changing time intervals.

Angelopoulos, Candès and Tibshirani (2023), **Conformal PID Control for Time Series Prediction**, explicitly use control ideas to adapt to systematic errors, seasonality, trends and general shift.

Areces, Mohri, Hashimoto and Duchi (2025), **Online Conformal Prediction via Online Optimization**, develop adversarial/stochastic online conformal algorithms and time-local guarantees under structural assumptions.

**Boundary for B15:** B15 is not an online coverage controller, learning-rate selection method, PID method, regret algorithm, or adaptive quantile update. The one-sided B13 rule has already been tested and rejected for 2024. B15 asks an earlier information question: *before using a realized calibration error as feedback, is the sign of the target calibration error identified at all from the available source history and pre-outcome target information?*

## 4. Fine-grained covariate versus conditional shift is already recognized

Ai and Ren (2024), **Not all distributional shifts are equal: Fine-grained robust conformal inference**, explicitly distinguish covariate-distribution shift from conditional outcome-distribution shift. Their method combines covariate reweighting with robustness to conditional shift bounded by an f-divergence neighborhood.

**Boundary for B15:** the conceptual separation between mixture/covariate shift and conditional shift is therefore not, by itself, novel. B15 must earn value from the *calibration-error transport* object and its prospective identifiability/certification problem, not from merely decomposing “shift” into two verbal categories.

The closest hostile comparison is:

- robust conformal work asks how to construct valid/efficient prediction regions under specified shift classes;
- B15 asks whether a **realized source calibration error** is itself transportable evidence about the signed **target calibration error** before a feedback correction is allowed.

If robust-CP theory already implies an equivalent sign-identification certificate under the same information set, B15's novelty claim must be narrowed accordingly.

## 5. Conditional/group coverage is established territory

Gibbs, Cherian and Candès (2023), **Conformal Prediction With Conditional Guarantees**, study finite-sample conditional guarantees, connect conditional coverage to classes of covariate shifts, and quantify errors when exact coverage is impossible for richer classes.

**Boundary for B15:** environment-specific or group-conditional coverage is not a B15 invention. B15's environment states are used to define cross-domain transport, not to claim universal conditional validity.

## 6. Unlabeled target-domain adaptation is active prior art

Kasa et al. (2025), **Adapting Prediction Sets to Distribution Shifts Without Labels**, adjust conformal score behavior using unlabeled shifted-domain information.

**Boundary for B15:** the statement “target covariates can be useful before labels arrive” is not novel. B15 must distinguish information about target environment composition from information about the unobserved target conditional score law.

## 7. Sequential/time-series conformal methods are established territory

Xu and Xie (2023), **Sequential Predictive Conformal Inference for Time Series**, adaptively estimate conditional quantiles of nonconformity scores under temporal dependence.

**Boundary for B15:** B15 cannot claim novelty from using residual-score dynamics or season ordering. It is season-batched and theory-first, with no online score-quantile estimator introduced in this stage.

## 8. Candidate B15 contribution after the hostile audit

The candidate contribution is intentionally narrow:

> **Calibration-error transportability:** characterize when the signed calibration error observed in a source deployment domain is identified, bounded, or non-identifiable as information about the signed calibration error of a later deployment domain, conditional on the pre-outcome information actually available before feedback is applied.

The mathematical core is:

\[
\Delta_t
=\Delta_s
+\Gamma^{\mathrm{mix}}_{s\to t}
+\Gamma^{\mathrm{cond}}_{s\to t},
\]

paired with:

1. a no-free-transport result when \(\Gamma^{\mathrm{cond}}\) is unrestricted;
2. a sign-identification certificate when conditional drift is prospectively bounded;
3. explicit treatment of environment-support/overlap and finite-sample uncertainty before an adaptive action can be authorized.

This is **not yet declared a literature-level novel theorem family**. The decomposition is elementary algebra, and non-identifiability constructions are a standard proof pattern. The research value must come from a rigorous transportability framework, sharp bounds/testability results, and a prospective G×E validation protocol that solves a problem not already subsumed by existing robust/online conformal theory.

## 9. Kill criteria

B15 should be terminated or materially reframed if any of the following occurs:

1. an existing paper already defines an equivalent source-calibration-error-to-target-calibration-error transport object and proves the same identification/bounding results under the same information set;
2. the proposed transport certificate collapses to a direct corollary of standard robust conformal bounds without new operational/testability content;
3. the conditional-drift bound cannot be specified or falsified prospectively without target labels, making the certificate vacuous;
4. environment-support uncertainty dominates every historically realistic certificate, so the framework never identifies an actionable sign;
5. the proper-loss decision layer shows no practical advantage over retaining the frozen interval rule whenever transport is uncertain.

A negative outcome under these kill criteria is a valid research result. B15 must not be rescued by inventing a tuned heuristic after the fact.

## References used for the boundary

- Tibshirani, Ryan J., Rina Foygel Barber, Emmanuel J. Candès, and Aaditya Ramdas. 2019. *Conformal Prediction Under Covariate Shift*. arXiv:1904.06019.
- Gibbs, Isaac, and Emmanuel Candès. 2021. *Adaptive Conformal Inference Under Distribution Shift*. arXiv:2106.00170.
- Barber, Rina Foygel, Emmanuel J. Candès, Aaditya Ramdas, and Ryan J. Tibshirani. 2022. *Conformal Prediction Beyond Exchangeability*. arXiv:2202.13415.
- Gibbs, Isaac, and Emmanuel Candès. 2022. *Conformal Inference for Online Prediction with Arbitrary Distribution Shifts*. arXiv:2208.08401.
- Zaffran, Margaux, Olivier Féron, Yannig Goude, Julie Josse, and Aymeric Dieuleveut. 2022. *Adaptive Conformal Predictions for Time Series*. ICML, PMLR 162.
- Bhatnagar, Aadyot, Huan Wang, Caiming Xiong, and Yu Bai. 2023. *Improved Online Conformal Prediction via Strongly Adaptive Online Learning*. ICML, PMLR 202.
- Gibbs, Isaac, John J. Cherian, and Emmanuel J. Candès. 2023. *Conformal Prediction With Conditional Guarantees*. arXiv:2305.12616.
- Xu, Chen, and Yao Xie. 2023. *Sequential Predictive Conformal Inference for Time Series*. ICML, PMLR 202.
- Angelopoulos, Anastasios N., Emmanuel J. Candès, and Ryan J. Tibshirani. 2023. *Conformal PID Control for Time Series Prediction*. arXiv:2307.16895.
- Ai, Jiahao, and Zhimei Ren. 2024. *Not all distributional shifts are equal: Fine-grained robust conformal inference*. ICML, PMLR 235.
- Kasa, Kevin, Zhiyu Zhang, Heng Yang, and Graham W. Taylor. 2025. *Adapting Prediction Sets to Distribution Shifts Without Labels*. UAI, PMLR 286.
- Areces, Felipe, Christopher Mohri, Tatsunori Hashimoto, and John Duchi. 2025. *Online Conformal Prediction via Online Optimization*. ICML, PMLR 267.
