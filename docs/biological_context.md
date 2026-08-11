# Biological Context

Plant Intelligence Lab focuses on computational questions that arise when biological performance depends jointly on genotype, treatment, environment, and time.

## Why prediction is difficult in plant biotechnology

Plant phenotypes are not determined by genotype alone. The same accession or line can respond differently under different environmental conditions or experimental treatments. In addition, many biologically important outcomes require time to observe, while the available sample size can be small relative to genomic dimensionality.

This creates several recurring challenges:

- high-dimensional genomic predictors
- limited sample sizes
- population structure and relatedness
- genotype × environment interaction
- genotype × protocol interaction
- longitudinal dependence
- distribution shift between experimental settings
- noisy phenotypes
- costly or slow experiments

The project is designed around these constraints rather than treating plant data as generic tabular ML data.

## In-vitro regeneration as a first use case

A useful first public case study is shoot regeneration in *Arabidopsis thaliana*. The conceptual structure is particularly relevant because it combines:

```text
Genetic variation
    + in-vitro treatment variation
    + measured regeneration phenotype
```

This supports a concrete set of prediction questions:

- whether regeneration-related traits can be predicted for unseen accessions
- whether treatment information improves predictions
- whether genotype × treatment interactions are informative
- how uncertain each forecast is
- whether a model can identify observations for which prediction is unreliable

The purpose is not to claim that results from *Arabidopsis* directly transfer to commercial plant species. The value lies in demonstrating a rigorous computational architecture on a public biological system.

## Genotype × environment forecasting

A second use case extends the project to multi-environment data.

The biological question is:

> If a genotype performs well in one environment, how confidently can its performance be forecast in another?

This matters because biological performance may shift when environmental conditions change. Models therefore need to represent both stable genetic signal and context-dependent response.

## Early outcome prediction

Many plant processes require days, weeks, months, or longer before the final outcome is observed. If reliable early measurements exist, a forecasting system may help estimate final outcomes earlier.

The relevant structure is:

```text
Early phenotype + genotype + treatment + environment
                         ->
                future biological outcome
```

The value of such a system depends on prospective validation. A model that predicts well retrospectively but fails on unseen biological material has little operational value.

## From prediction to experiment selection

Biological experiments are often constrained by laboratory capacity, material availability, time, and cost. Once a predictive model is sufficiently reliable, uncertainty can be used constructively.

Instead of asking only:

> What outcome do we expect?

we can also ask:

> Which experiment should be run next because it is either promising or highly informative?

This is the connection between biological forecasting and active learning.

## Scientific interpretation

Throughout the repository:

- predictive importance is not treated as causal evidence
- genomic association is not automatically interpreted as biological mechanism
- external validity is not assumed across species or production systems
- uncertainty is reported explicitly
- biological conclusions remain bounded by the available data

The goal is to build computational tools that respect biological complexity while still producing outputs that can support practical decisions.
