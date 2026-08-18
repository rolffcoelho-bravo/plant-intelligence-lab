# B18-T0 — Forecast-Time G×E Novelty Gate

## Status

B18-T0 is the only B18 action authorized by the terminal Case Study B closure. It is a hypothesis-first hostile novelty audit. It does **not** fit or alter a predictive model.

Machine decision:

`B18_T0_BROAD_FORECAST_TIME_GXE_NOVELTY_REJECTED_INFORMATION_PARITY_BENCHMARK_HYPOTHESIS_SURVIVES_KILL_TEST_ONLY`

The broad forecast-time G×E methodology claim is rejected. A narrower information-parity benchmark hypothesis may enter one further novelty kill test. Model development remains forbidden.

## Parent boundary

The merged Case Study B closure permits `B18_SEPARATE_HYPOTHESIS_AND_NOVELTY_AUDIT` but forbids automatic B18 model development. It also forbids using the revealed B14C result to tune a new hypothesis and then present that hypothesis as prospective.

B18-T0 therefore uses only:

- the merged Case Study B closure decision;
- the merged B18 gate;
- primary literature.

It reads no outcome-bearing artifact and generates no prediction.

## Candidate broad hypothesis

The starting question authorized by the closure was whether enforcing a forecast-time information set changes the learnable G×E contrast operator and external ranking relative to methods that use environmental information unavailable at the intended decision time.

The strongest possible broad claim would be:

> Forecast-time environmental-information restrictions define a new G×E prediction problem not already addressed in genomic prediction.

That claim does not survive.

## Direct prior-art collision: Gillberg et al. 2019

Gillberg, Marttinen, Mamitsuka and Kaski, *Modelling G×E with historical weather information improves genomic prediction in new environments*, Bioinformatics, DOI `10.1093/bioinformatics/btz197`, is a direct collision.

The paper explicitly states that weather from the target growth season is unavailable at prediction time. It constructs a realistic prediction setup in which:

- test locations are new;
- test years are new;
- test genotypes are new offspring of the training material;
- target-season phenotype data are unavailable;
- in-season target weather is unavailable;
- historical weather and static environmental information are used instead.

It then compares a historical-weather G×E interaction model against:

- a non-realistic ideal interaction model using actual in-season target weather;
- an additive `G+E` model;
- GE-BLUP;
- GBLUP.

Therefore B18 cannot claim novelty for the idea that practical G×E prediction must respect environmental information available at prediction time, nor for contrasting realistic weather availability with ex-post in-season information.

## Reinforcement: future-year genotype ranking

Eckhoff et al. 2026, *Tailoring AI and ML models for genotype-by-environment prediction leveraging environmental covariates: A European rye example*, DOI `10.1007/s00122-026-05280-z`, studies inference for future years using historical weather and evaluates environment-specific genotype rankings across G×E ML/DNN approaches.

This closes another obvious route: future environment-specific genotype ranking from forecast-available historical weather proxies is not a new B18 concept.

## Partial information prefixes are also not new by themselves

Shahhosseini et al. 2020, *Forecasting Corn Yield With Machine Learning Ensembles*, DOI `10.3389/fpls.2020.01120`, compares full in-season weather with partial weather information available at multiple issue dates.

That study is not genotype-specific genomic G×E prediction, so it does not fully answer the remaining B18 question. But it establishes that nested partial-weather forecast horizons are a standard operational forecasting design rather than a new mathematical idea.

Adak et al. 2026, DOI `10.1093/plphys/kiag344`, further shows that temporal days-after-planting environmental and phenomic windows are already used inside genomic prediction across environments. Kick et al. 2023, DOI `10.1093/g3journal/jkad006`, uses genomic, environmental and management interactions with time-indexed weather. EXGEP and recent graph/recurrent G×E methods occupy the nonlinear architecture route.

Therefore none of the following can support B18 novelty:

- “use only early weather”;
- “truncate weather at 30 DAP”;
- “add G×E interaction layers”;
- “use a GNN/LSTM/Transformer”;
- “use a future-year split”;
- “predict genotype rankings in future environments using historical weather.”

## Narrower object that remains uneliminated

The literature audit did not identify, in the primary G×E sources reviewed here, a standardized benchmark that simultaneously does all of the following:

1. fixes a common set of candidate G×E model classes;
2. fixes the same training data and target genotypes/environments;
3. defines nested information sets
   \[
   \mathcal I_0 \subset \mathcal I_{t_1} \subset \cdots \subset \mathcal I_{T},
   \]
   where each \(\mathcal I_t\) contains only variables observable by decision time \(t\);
4. evaluates every model under every identical information set rather than allowing each method its preferred ex-post environmental representation;
5. measures both point-yield performance and within-environment genotype contrast/ranking skill;
6. tests whether model ordering under full-season information is preserved under deployable information prefixes.

This is **not yet a novelty claim**. It is a surviving benchmark/protocol hypothesis.

The scientific question becomes:

> Does ex-post model superiority survive when all candidate G×E methods are evaluated under information parity at the actual decision time?

The candidate object is an **information-time optimism/ranking-instability benchmark**, not a new predictive architecture.

## Why this could matter

Many G×E models use environmental covariates aggregated over the full target growing season. Those features may be useful for retrospective biological modeling but can be unavailable at an early breeding or deployment decision.

If model rankings change materially when future environmental information is removed, then a literature leaderboard based on full-season covariates may not identify the best deployable model. That would be an evaluation problem, not necessarily an algorithm problem.

The corresponding quantities could include:

- information-time performance curve \(R_m(t)\) for model class \(m\);
- pairwise ranking reversal indicator between model classes across \(t\);
- genotype-contrast/rank skill as a function of \(t\);
- ex-post optimism gap \(R_m(T)-R_m(t)\);
- Pareto frontier between decision lead time and predictive skill.

These quantities are not declared novel in B18-T0.

## B18-T1 kill condition

Only **B18-T1 — Information-Parity Benchmark Novelty Test** is permitted next.

Before any model fitting, B18-T1 must search primary literature for an equivalent benchmark. B18 terminates if an existing study already benchmarks multiple G×E model classes under common nested decision-time information prefixes while evaluating target genotype ranking or contrasts.

If no equivalent benchmark is found, the surviving contribution must still be described as an **evaluation/protocol contribution**, unless a separate theorem or method survives an independent audit.

## Guardrails

B18-T0 and B18-T1 permit no:

- new target outcome access;
- prediction generation;
- model fitting;
- hyperparameter tuning;
- G×E architecture development;
- B5 genomic representation change;
- T1 clock change;
- T2 reopening;
- support/interval tuning;
- resealing;
- post-result tuning;
- use of B14C performance to select the B18 hypothesis.

B18 model development remains forbidden after T0.
