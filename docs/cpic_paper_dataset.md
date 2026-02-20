# CPIC Paper Dataset

## Overview

Dataset mapping CPIC pharmacogenomics guidelines to relevant papers (PMIDs/PMCIDs), variants, and drugs. Built from the CPIC database tables in `data/cpic_data/`.

**Script:** `cpic_reproduction/build_paper_dataset.py`
**Output:** `cpic_reproduction/cpic_paper_dataset.jsonl` and `cpic_paper_dataset.tsv`

## Dataset Schema

Each row represents one CPIC variant-drug recommendation.

| Field | Type | Description |
|---|---|---|
| `rec_id` | string | CPIC recommendation ID |
| `drug` | string | Drug name |
| `gene` | string | Gene(s), pipe-separated for multi-gene (e.g. `CYP2C19\|CYP2D6`) |
| `variants` | list[string] | Variant descriptions (e.g. `["HLA-B *57:01 positive"]`) |
| `guideline` | string | CPIC guideline name |
| `guideline_id` | string | CPIC guideline ID |
| `recommendation` | string | CPIC dosing recommendation text |
| `classification` | string | Recommendation strength (Strong/Moderate/Optional) |
| `guideline_pmids` | list[string] | PMIDs of CPIC guideline papers |
| `guideline_pmcids` | list[string] | PMCIDs of CPIC guideline papers |
| `evidence_pmids` | list[string] | PMIDs of underlying research papers |
| `evidence_pmcids` | list[string] | PMCIDs of underlying research papers |

## Dataset Stats

- **2,129 rows** (all CPIC variant-drug recommendations)
- **109 unique drugs**
- **21 unique genes**
- **26 unique guidelines**

## Paper Sources

### 1. Guideline Papers (from `publication.tsv` + `pair.tsv` citations)

The published CPIC clinical guideline papers themselves.

- **42 unique PMIDs, 42 unique PMCIDs (100% conversion)**
- These are the actual CPIC guideline publications (e.g. "CPIC Guideline for CYP2D6 and Codeine")

### 2. Evidence Papers (from `allele.tsv` citations + population frequency studies)

Underlying research that CPIC guidelines are based on. Two sub-sources:

- **Allele functional evidence** (`allele.tsv` → `citations` field): Papers supporting each allele's functional classification (e.g. enzyme activity studies)
- **Population frequency studies** (`allele_frequency.tsv` → `population.tsv` → `publication.tsv`): Papers reporting allele frequencies in different populations

Combined:
- **1,753 unique evidence PMIDs, 439 unique PMCIDs (25% conversion)**
- Evidence PMIDs per row: min=0, max=599, median=433
- Evidence PMCIDs per row: min=0, max=111, median=103

### 3. Overlap with Existing Papers

- 168 of 481 total PMCIDs already exist in `data/papers/` as markdown files
- The existing `data/papers/` corpus is PharmGKB annotation evidence — a different but partially overlapping set

## PMID → PMCID Conversion

PMIDs are converted to PMCIDs using the [NCBI ID Converter API](https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/). Many evidence PMIDs lack PMCIDs because the papers are not in PMC Open Access (often older population studies in journals without open-access mandates).

- Guideline papers: **100%** conversion (42/42)
- Evidence papers: **25%** conversion (439/1,753)
- 1,316 evidence PMIDs have no PMCID

## Evidence Coverage by Gene-Guideline

Ranked by PMCID conversion rate:

| Gene | Guideline | PMIDs | PMCIDs | Rate |
|---|---|---|---|---|
| DPYD | Fluoropyrimidines | 9 | 7 | 77.8% |
| UGT1A1 | Atazanavir | 22 | 11 | 50.0% |
| CACNA1S\|RYR1 | Volatile anesthetics/Succinylcholine | 10 | 5 | 50.0% |
| CYP2B6 | Efavirenz | 88 | 39 | 44.3% |
| SLCO1B1 | Statins | 62 | 25 | 40.3% |
| ABCG2\|SLCO1B1 | Statins | 76 | 30 | 39.5% |
| MT-RNR1 | Aminoglycosides | 113 | 36 | 31.9% |
| NAT2 | Hydralazine | 73 | 23 | 31.5% |
| NUDT15\|TPMT | Thiopurines | 213 | 62 | 29.1% |
| HLA-A\|HLA-B | Carbamazepine/Oxcarbazepine | 31 | 9 | 29.0% |
| CYP2C9\|SLCO1B1 | Statins | 365 | 103 | 28.2% |
| HLA-B | Abacavir | 29 | 8 | 27.6% |
| HLA-B | Allopurinol | 29 | 8 | 27.6% |
| HLA-B | Carbamazepine/Oxcarbazepine | 29 | 8 | 27.6% |
| CYP2C9 | NSAIDs | 303 | 78 | 25.7% |
| CYP2C9\|HLA-B | Phenytoin | 331 | 85 | 25.7% |
| CYP2B6\|CYP2C19 | SRI Antidepressants | 433 | 94 | 21.7% |
| CYP2D6 | Opioids | 282 | 61 | 21.6% |
| CYP2D6 | Atomoxetine | 282 | 61 | 21.6% |
| CYP2D6 | Tamoxifen | 282 | 61 | 21.6% |
| CYP2D6 | SRI Antidepressants | 282 | 61 | 21.6% |
| CYP2D6 | Tricyclic Antidepressants | 282 | 61 | 21.6% |
| CYP2D6 | Beta-Blockers | 282 | 61 | 21.6% |
| CYP2D6 | Ondansetron/Tropisetron | 282 | 61 | 21.6% |
| CYP2C19\|CYP2D6 | Tricyclic Antidepressants | 599 | 111 | 18.5% |
| CYP2C19 | SRI Antidepressants | 347 | 55 | 15.9% |
| CYP2C19 | Clopidogrel | 347 | 55 | 15.9% |
| CYP2C19 | Proton Pump Inhibitors | 347 | 55 | 15.9% |
| CYP2C19 | Voriconazole | 347 | 55 | 15.9% |
| G6PD | G6PD | 140 | 22 | 15.7% |
| CYP3A5 | Tacrolimus | 134 | 18 | 13.4% |
| CFTR | Ivacaftor | 0 | 0 | 0.0% |

### Key Observations

- **No recommendation has 100% evidence PMCID coverage.** Even DPYD (the best at 77.8%) is missing 2 PMIDs.
- **DPYD is the best candidate** for evidence-based reproduction: only 9 evidence papers total, 7 available as PMCIDs, and a small focused guideline (10 recommendations).
- **Genes with large evidence bases** (CYP2D6: 282, CYP2C19: 347, CYP2C9: 303) have low conversion rates (15-25%) — many are older population studies not in PMC Open Access.
- **Evidence is linked at the gene level**, not the recommendation level. All recommendations for the same gene share the same evidence PMIDs. Multi-gene recommendations (e.g. CYP2C19|CYP2D6) combine evidence from both genes.
- **CFTR has zero evidence PMIDs** in the CPIC database tables — its allele functional assignments don't cite papers through the `allele.tsv` citations mechanism.

## Data Lineage

```
recommendation.tsv ──→ guidelineid ──→ guideline.tsv (guideline name)
                   ──→ guidelineid ──→ publication.tsv (guideline paper PMIDs/PMCIDs)
                   ──→ guidelineid ──→ pair.tsv → citations (guideline paper PMIDs)

variant_recommendations_consolidated.tsv ──→ lookup_genes ──→ allele.tsv → citations (evidence PMIDs)
                                                           ──→ allele_frequency.tsv
                                                               → population.tsv → publicationid
                                                               → publication.tsv → pmid (evidence PMIDs)

All PMIDs ──→ NCBI ID Converter API ──→ PMCIDs
```
