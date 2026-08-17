# B13 Literature Boundary

B13 is deliberately narrow in its novelty claim.

The research literature already contains adaptive conformal inference under distribution shift, parameter-free/aggregated ACI variants for time series, strongly adaptive online conformal methods, conformal PID control, and online-optimization formulations with time-varying coverage targets.

Accordingly, B13 does **not** claim invention of adaptive conformal prediction.

Its empirical contribution is the sealed evaluation of a season-batched, environment-balanced feedback rule in a genotype-by-environment forecasting system with:

- a frozen genomic predictor;
- a frozen forecast horizon;
- clustered environments with unequal cell counts;
- one feedback update per revealed season;
- explicit separation between point-model transport and calibration transport;
- SHA-256 prediction/interval sealing before future outcome access;
- a predeclared official-answer-key estimand;
- an efficiency gate using proper interval score so wider intervals cannot win on coverage alone.

The main hostile comparators for interpretation are:

1. Gibbs & Candès — Adaptive Conformal Inference under distribution shift.
2. Zaffran et al. — adaptive/aggregated conformal prediction for time series.
3. Bhatnagar et al. — strongly adaptive online conformal prediction.
4. Angelopoulos, Candès & Tibshirani — conformal PID control.
5. Areces et al. — online conformal prediction via online optimization.
6. Retzlaff et al. — formal marginal/conditional coverage testing under nonstationarity.

Any later manuscript should frame the B13 rule as a constrained domain-specific controller unless theorem-level work establishes a broader methodological contribution.
