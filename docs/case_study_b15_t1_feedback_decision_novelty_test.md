# Case Study B15-T1 — Feedback-Decision Novelty Test

## Status

B15-T1 executes the kill test predeclared at the end of B15.

It asks whether **calibration-feedback action identifiability** is a genuinely new methodological object or a specialization of existing statistical decision theory, partial identification, robust optimization, and decision-theoretic conformal prediction.

B15-T1 accesses no new outcomes, generates no new predictions, changes no predictor, changes no interval rule, tunes no ambiguity radius, and introduces no new adaptive competitor.

## 1. Candidate object made explicit

Let `I_t` denote all information legitimately available before the next deployment outcomes. Let

\[
\mathcal P(I_t)
\]

be the ambiguity class of future data-generating distributions compatible with that information.

Let the predeclared action set be

\[
\mathcal A=\{a_1,\ldots,a_K\},
\]

where an action may represent, for example, retaining, narrowing, or widening an interval rule. For each admissible world \(P\in\mathcal P(I_t)\), define:

- \(C_P(a)\): population interval coverage after taking action \(a\);
- \(L_P(a)\): population decision loss, such as expected proper interval score.

For nominal coverage \(\tau\), the statewise optimal action set is

\[
\mathcal A^*(P)
=
\arg\min_{a\in\mathcal A:\,C_P(a)\ge\tau}L_P(a).
\]

The ambiguity-induced identified set of optimal actions is

\[
\mathcal I_A(I_t)
=
\bigcup_{P\in\mathcal P(I_t)}\mathcal A^*(P).
\]

The action is point-identified only if \(\mathcal I_A(I_t)\) is a singleton.

If actions carry signed feedback directions \(d(a)\in\{-1,0,+1\}\), the feedback direction is identified only if

\[
\{d(a):a\in\mathcal I_A(I_t)\}
\]

is a singleton.

This definition is now executable in `maize_b15_t1_feedback_decision.py`.

## 2. Robust decision objects

A feedback action is robustly coverage-feasible when

\[
\inf_{P\in\mathcal P(I_t)}C_P(a)\ge\tau.
\]

The robustly feasible action set is

\[
\mathcal A_R(I_t)
=
\left\{a\in\mathcal A:
\inf_{P\in\mathcal P(I_t)}C_P(a)\ge\tau
\right\}.
\]

Two natural robust decision rules are then

\[
a_{MM}
\in
\arg\min_{a\in\mathcal A_R(I_t)}
\sup_{P\in\mathcal P(I_t)}L_P(a)
\]

and

\[
a_{MR}
\in
\arg\min_{a\in\mathcal A_R(I_t)}
\sup_{P\in\mathcal P(I_t)}
\left[L_P(a)-\min_{b:C_P(b)\ge\tau}L_P(b)\right].
\]

These are respectively a coverage-constrained minimax-loss rule and minimax-regret rule.

## 3. Hostile equivalence result

The B15-T1 candidate does **not** survive as a general methodological novelty.

### 3.1 Identification plus decision theory already exists

Manski's *Identification and Statistical Decision Theory* explicitly studies how identification analysis informs decision-making when the true state is partially identified and the decision must be made under ambiguity. It discusses maximin and minimax-regret criteria and shows that randomized actions can improve decision performance under partial identification.

Christensen, Moon and Schorfheide's *Optimal Decision Rules When Payoffs are Partially Identified* derives asymptotically optimal statistical decision rules when decision payoffs depend on a partially identified parameter, using minimax treatment of ambiguity combined with average risk minimization.

Montiel Olea, Qiu and Stoye's *Decision Theory for Treatment Choice Problems with Partial Identification* applies classical statistical decision theory directly to partially identified choice problems and characterizes minimax-regret behavior, including multiplicity and randomization of optimal decision rules.

Therefore the move

\[
\text{ambiguity class}
\rightarrow
\text{identified/partially identified optimal action}
\rightarrow
\text{minimax or minimax-regret decision}
\]

is established statistical decision theory, not a B15 contribution.

### 3.2 Decision-theoretic conformal prediction already links coverage and downstream action

Kiyani, Pappas, Roth and Hassani (ICML 2025) develop a decision-theoretic foundation for prediction sets used by risk-averse decision makers. They characterize an optimal max-min policy mapping prediction sets to actions and derive prediction sets optimal for such decision makers.

Wang and Dobriban (2026), *Optimal Decision-Making Based on Prediction Sets*, are even closer to B15-T1. Their framework minimizes expected loss against a worst-case distribution consistent with a prediction set's coverage guarantee, characterizes the minimax optimal policy for a fixed prediction set, and derives an optimal prediction-set construction by minimizing robust risk subject to coverage.

Thus the B15-T1 combination

\[
\text{coverage constraint}
+
\text{worst-case ambiguity}
+
\text{downstream loss}
+
\text{optimal action}
\]

is already present in decision-theoretic conformal prediction.

### 3.3 Robust optimization already uses conformal uncertainty sets for decisions

Johnstone and Cox (2021) connect conformal prediction regions to robust optimization. Patel, Rayan and Tewari (AISTATS 2024) develop conformal contextual robust optimization for predict-then-optimize problems. These works further reduce the plausibility that a generic coverage-constrained robust action-selection layer is new.

### 3.4 Conformal risk-control literature already extends calibration beyond miscoverage

Distribution-free risk-controlling prediction sets, Conformal Risk Control, and Automatically Adaptive Conformal Risk Control already control losses substantially more general than ordinary miscoverage. Therefore replacing miscoverage with a proper interval loss or another monotone risk functional does not by itself establish novelty.

## 4. Formal equivalence statement

For a finite ambiguity class and finite action set, the B15-T1 object is a standard robust/partially identified decision problem:

1. the future distribution \(P\) is the unknown state of nature;
2. \(\mathcal P(I_t)\) is the identified/ambiguity set;
3. \(C_P(a)\ge\tau\) is an action-feasibility restriction;
4. \(L_P(a)\) is the payoff/loss;
5. \(\mathcal I_A(I_t)\) is the set of statewise optimal decisions consistent with the identified state set;
6. minimax loss and minimax regret are standard ambiguity criteria.

Restricting the actions to `NARROW`, `RETAIN`, and `WIDEN` changes the application, not the mathematical class.

No theorem found in B15-T1 demonstrates that this specialization escapes the existing decision-theory framework.

## 5. Why the apparent "no-update" idea does not rescue novelty

A result such as

> retain the current interval whenever widening and narrowing are not robustly preferred

can be useful operationally. But unless its optimality follows from a new information structure or a new nonstandard decision criterion, it is a corollary of robust/minimax decision theory over a restricted action set.

Likewise, proving that two admissible future worlds select opposite feedback directions establishes partial identification of the decision. That is a useful diagnostic but not a new theory of identification.

## 6. Executable witness

The B15-T1 tests construct one pre-outcome ambiguity class with three admissible future worlds in which:

- `NARROW` is statewise optimal in one world;
- `RETAIN` is statewise optimal in another;
- `WIDEN` is statewise optimal in a third.

The resulting identified optimal-action set is

\[
\{\text{NARROW},\text{RETAIN},\text{WIDEN}\},
\]

and the direction set is

\[
\{-1,0,+1\}.
\]

This confirms that the decision can be non-identified. It does **not** establish novelty, because that conclusion is exactly what partial-identification decision theory predicts.

## 7. B15-T1 decision

The predeclared kill criterion is met.

\[
\boxed{
\text{B15-T1 feedback-decision novelty is rejected.}
}
\]

Machine state:

`B15_T1_FEEDBACK_DECISION_NOVELTY_REJECTED_TERMINATE_B15`

Consequences:

- B15's three transport objects remain background lemmas only;
- B15-T1's action-identification, minimax, and minimax-regret objects are background decision-theory machinery only;
- there is no B15-T2;
- no new adaptive calibration rule may be created as a rescue;
- no new outcomes may be opened to manufacture a distinction;
- B15 is closed as a novelty branch.

## 8. Scientific value of the negative result

B15 still added value to Case Study B by demonstrating, with a traceable hostile audit, why two tempting research directions should **not** be marketed as new methodology:

1. calibration-error transport under distribution shift;
2. action selection under ambiguity using coverage and proper loss.

The repository now has explicit mathematical and executable boundaries showing where established conformal and statistical decision theory already reaches.

That protects subsequent work from drifting into relabeling.

## References used in the hostile audit

- Manski, Charles F. 2024/2025. *Identification and Statistical Decision Theory*. Econometric Theory 41(4):977–993.
- Christensen, Timothy, Hyungsik Roger Moon, and Frank Schorfheide. 2026. *Optimal Decision Rules When Payoffs are Partially Identified*. Review of Economic Studies, corrected proof.
- Montiel Olea, José Luis, Chen Qiu, and Jörg Stoye. 2026. *Decision Theory for Treatment Choice Problems with Partial Identification*. Review of Economic Studies, corrected proof.
- Kiyani, Shayan, George J. Pappas, Aaron Roth, and Hamed Hassani. 2025. *Decision Theoretic Foundations for Conformal Prediction: Optimal Uncertainty Quantification for Risk-Averse Agents*. ICML, PMLR 267.
- Wang, Tao, and Edgar Dobriban. 2026. *Optimal Decision-Making Based on Prediction Sets*. arXiv:2602.00989.
- Johnstone, Chancellor, and Bruce Cox. 2021. *Conformal Uncertainty Sets for Robust Optimization*. PMLR 152.
- Patel, Yash P., Sahana Rayan, and Ambuj Tewari. 2024. *Conformal Contextual Robust Optimization*. AISTATS, PMLR 238.
- Bates, Stephen, Anastasios Angelopoulos, Lihua Lei, Jitendra Malik, and Michael I. Jordan. 2021. *Distribution-Free, Risk-Controlling Prediction Sets*. arXiv:2101.02703.
- Angelopoulos, Anastasios N., Stephen Bates, Adam Fisch, Lihua Lei, and Tal Schuster. 2022. *Conformal Risk Control*. arXiv:2208.02814.
- Blot, Vincent, Anastasios Nikolas Angelopoulos, Michael Jordan, and Nicolas J-B. Brunel. 2025. *Automatically Adaptive Conformal Risk Control*. AISTATS, PMLR 258.
