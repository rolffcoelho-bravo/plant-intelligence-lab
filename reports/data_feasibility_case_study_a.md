# Case Study A — Data Feasibility

## In-Vitro Regeneration Intelligence

### Objective

Case Study A tests whether genetic information and protocol variation contain sufficient predictive signal to model regeneration-related phenotypes in *Arabidopsis thaliana*, with emphasis on generalization to unseen accessions and uncertainty-aware prediction.

The intended modelling problem is:

\[
G + P + X_t \rightarrow \widehat{Y}_{t+h}
\]

where `G` represents genomic information, `P` represents protocol or treatment, `X_t` represents biological information available by time `t`, and `Y_(t+h)` is a later regeneration phenotype.

This case study uses real public biological resources. Synthetic data are not required for the principal empirical analysis.

## Primary phenotype resource

**AraPheno Study 80 — Genetic dissection of shoot regeneration from root explants in Arabidopsis (Lardon et al., 2020)**

- AraPheno study DOI: `10.21958/study:80`
- Original publication DOI: `10.1038/s42003-020-01274-9`
- Species: *Arabidopsis thaliana*
- Experimental scope reported by AraPheno: 170 natural accessions
- Experimental design: two shoot-regeneration protocol variants
- Biological system: shoot regeneration from root explants
- Trait family: in-vitro plant structure morphology

The study records substantial variation in regenerated shoot numbers and related *in vitro* traits. The public phenotype catalogue includes measurements at 15 and 21 days under protocol A and protocol B, creating a useful structure for protocol-aware and time-aware prediction.

## Confirmed phenotype structure

The public study catalogue contains regeneration-related outcomes including:

- regenerated shoots
- shoot primordia
- root-like structures
- undefined structures
- callus score
- greening
- explant area

Measurements are represented at combinations of:

- 15 days / 21 days
- protocol A / protocol B

This creates three immediately valuable prediction settings.

### 1. Genomic regeneration prediction

\[
G \rightarrow Y_{regeneration}
\]

Question: can regeneration phenotype variation be predicted for unseen accessions from genomic information?

### 2. Genotype × protocol prediction

\[
G + P + G\times P \rightarrow Y_{regeneration}
\]

Question: does protocol information materially improve prediction, and is there evidence that accessions respond differently to protocol A and protocol B?

### 3. Early-to-later biological forecasting

\[
G + P + X_{15d} \rightarrow Y_{21d}
\]

Question: can 15-day biological measurements improve forecasts of 21-day regeneration outcomes?

This third task is especially important because it turns the dataset from a static phenotype-prediction benchmark into a biological forecasting problem with direct decision relevance.

## Example primary outcome

AraPheno phenotype `1267` is **shoots 15d protocol a**. It is defined as a manual count of regenerated shoots from root explants after 15 days on shoot induction medium under protocol A.

The study also exposes corresponding later and alternate-protocol outcomes, allowing the project to construct coherent outcome families rather than treating individual phenotype files as unrelated prediction targets.

## Genomic resource

The **1001 Genomes Project** provides the genomic layer for *Arabidopsis thaliana*.

The first major project phase reported 1,135 genomes and provides public variation resources for the species. The Case Study A accessions must be intersected explicitly with available genomic identifiers before modelling.

The expected statistical regime is high dimensional:

\[
p \gg n
\]

with genomic marker dimensionality potentially orders of magnitude larger than the number of accessions in the regeneration study.

This makes the case study suitable for comparing classical genomic prediction with regularized and nonlinear machine-learning approaches.

## Planned modelling matrix

The first modelling-ready representation should be accession-centric.

| Layer | Candidate information |
|---|---|
| Genomics | SNP / genomic relationship representation |
| Protocol | A or B |
| Early phenotype | 15-day regeneration measurements |
| Later phenotype | 21-day regeneration measurements |
| Outcome family | shoots, primordia, greening, area, callus, related structures |
| Metadata | accession identifiers and validated public metadata |

The exact feature matrix will be determined only after identifier matching and missingness assessment.

## Validation design

Random observation-level splitting is not sufficient for the principal claims.

The primary validation target is **generalization to unseen genotypes/accessions**. Splitting must therefore occur at accession level, with additional relatedness-aware grouping if genomic structure indicates that ordinary accession-level splitting remains overly optimistic.

The benchmark sequence is:

1. intercept / phenotype-only reference
2. classical quantitative-genetics baseline
3. GBLUP or genomic relationship model
4. regularized high-dimensional model
5. selected nonlinear ML models
6. uncertainty-aware versions of the strongest defensible models

Performance should be evaluated using metrics appropriate to each phenotype, including RMSE, MAE, predictive correlation and `R²` for continuous outcomes where appropriate.

Model ranking alone is not the goal. The analysis must answer whether the model generalizes biologically and whether uncertainty is sufficiently calibrated to support decisions.

## Uncertainty and abstention

Every decision-facing prediction should ultimately be accompanied by uncertainty.

Candidate methods include:

- bootstrap predictive intervals
- conformal prediction
- Bayesian predictive distributions
- calibrated residual or ensemble uncertainty

The system should also detect observations that are insufficiently represented by the training data and support an abstention state:

> **LOW CONFIDENCE — insufficient evidence for reliable prediction**

The out-of-distribution criterion must be defined quantitatively from genomic and/or feature-space structure rather than manually assigned.

## Direct biotechnology value

This case study is designed around decisions that occur naturally in experimental plant biotechnology:

- anticipating regeneration outcomes before the full observation horizon
- comparing genotype response across alternative protocols
- identifying accessions with high predicted potential but high uncertainty
- identifying combinations where additional experiments are most informative
- separating confident predictions from cases requiring new evidence

The industrial value is not the *Arabidopsis* species itself. The value is the transferable quantitative architecture:

```text
Genetic variation
      +
Protocol / treatment
      +
Early biological observations
      ↓
Predictive biological model
      ↓
Forecast + uncertainty
      ↓
Experiment prioritization / decision support
```

Transfer to another plant-biotechnology system would require appropriate proprietary or public data and fresh validation. No cross-system performance claim is implied.

## Data engineering tasks

The first executable data layer must:

1. retrieve the selected AraPheno phenotype records reproducibly;
2. preserve accession identifiers and phenotype metadata;
3. construct a phenotype dictionary across day × protocol × trait combinations;
4. retrieve or reference compatible 1001 Genomes variation resources;
5. quantify accession overlap between phenotype and genomic layers;
6. report missingness and replicate structure;
7. construct modelling-ready accession-level targets without undocumented manual edits;
8. record source provenance and checksums where practical.

## First target outcome family

The initial implementation should prioritize **regenerated shoots** because it is biologically direct and available across time/protocol combinations. Shoot primordia, greening, callus score and area can then be incorporated as secondary outcomes or early predictive features where scientifically defensible.

The initial forecasting comparison should therefore investigate:

\[
G + P \rightarrow Y_{21d}^{shoots}
\]

versus

\[
G + P + X_{15d} \rightarrow Y_{21d}^{shoots}
\]

This directly tests whether early biological information improves later-outcome prediction beyond genomic and protocol information alone.

## Feasibility verdict

**Proceed.**

The public data structure supports the intended first case study at the conceptual level: real genetic variation, two protocol variants, multiple regeneration-related traits, and repeated biological observation horizons are available in the same experimental study.

The next empirical requirement is to verify the exact accession-level intersection with the genomic resource and construct the reproducible phenotype acquisition layer. Final model feasibility depends on the matched sample size, genomic representation, population structure, phenotype missingness and effective independent information after relatedness is considered.

## Public sources

- AraPheno Study 80: `https://arapheno.1001genomes.org/study/80/`
- AraPheno phenotype 1267: `https://arapheno.1001genomes.org/phenotype/1267/`
- 1001 Genomes Project: `https://www.1001genomes.org/`
- Lardon et al. (2020), *Communications Biology*: DOI `10.1038/s42003-020-01274-9`
