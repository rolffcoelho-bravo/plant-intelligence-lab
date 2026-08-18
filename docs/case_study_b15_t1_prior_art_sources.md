# B15-T1 Primary-Source Boundary

B15-T1's novelty decision was based on primary research sources and publisher/proceedings records. This note records the closest sources used so the negative result remains auditable.

## Statistical decision theory under partial identification

### Manski — Identification and Statistical Decision Theory

Manski connects identification analysis directly to statistical decision theory. When the decision-relevant state is partially identified, the decision maker faces ambiguity; maximin and minimax-regret criteria are explicitly part of the analysis, including controlled randomization of actions.

**Boundary:** B15-T1 cannot claim novelty for moving from an identified set of possible future states to an ambiguity-aware decision rule.

### Christensen, Moon & Schorfheide — Optimal Decision Rules When Payoffs are Partially Identified

This work derives asymptotically optimal decision rules for discrete choice when payoffs depend on a partially identified parameter, using minimax handling of ambiguity together with average risk minimization.

**Boundary:** B15-T1 cannot claim that optimal action selection with partially identified payoffs is new.

### Montiel Olea, Qiu & Stoye — Decision Theory for Treatment Choice Problems with Partial Identification

This work applies classical statistical decision theory to partially identified choice problems and analyzes maximin and minimax-regret behavior, including multiplicity and randomization of optimal rules.

**Boundary:** B15-T1's set of admissible optimal feedback actions is a specialization of an established partially identified decision problem.

## Decision-theoretic conformal prediction

### Kiyani, Pappas, Roth & Hassani — Decision Theoretic Foundations for Conformal Prediction

The paper gives a decision-theoretic foundation linking prediction sets to risk-averse downstream actions. It characterizes a max-min policy mapping prediction sets to actions and derives prediction sets optimized for those decision makers.

**Boundary:** mapping calibrated uncertainty sets to downstream actions under risk aversion is established.

### Wang & Dobriban — Optimal Decision-Making Based on Prediction Sets

This 2026 work minimizes expected loss against a worst-case distribution consistent with a prediction set's coverage guarantee, characterizes the minimax optimal policy for fixed prediction sets, and optimizes prediction sets subject to coverage.

**Boundary:** the combination of coverage constraints, worst-case ambiguity, downstream loss, and optimal action is already explicit in conformal decision theory. This is the closest direct threat to B15-T1.

## Conformal robust optimization and risk control

### Johnstone & Cox — Conformal Uncertainty Sets for Robust Optimization

Connects conformal prediction regions to robust optimization.

### Patel, Rayan & Tewari — Conformal Contextual Robust Optimization

Uses conformal prediction regions in contextual predict-then-optimize decision problems.

### Bates et al. — Distribution-Free, Risk-Controlling Prediction Sets

Controls expected losses beyond ordinary miscoverage.

### Angelopoulos et al. — Conformal Risk Control

Extends conformal calibration to expected monotone loss functions and discusses distribution shift and adversarial risk control.

### Blot et al. — Automatically Adaptive Conformal Risk Control

Provides adaptive conditional risk-control methodology.

**Boundary:** substituting a proper interval score or generalized loss for miscoverage cannot by itself establish B15-T1 novelty.

## Source-level conclusion

The primary-source audit supports the machine decision:

`B15_T1_FEEDBACK_DECISION_NOVELTY_REJECTED_TERMINATE_B15`

The action-identification formulation remains useful for explaining why a calibration correction may be ambiguous, but it does not presently define a new mathematical class outside established partial-identification and robust decision theory.
