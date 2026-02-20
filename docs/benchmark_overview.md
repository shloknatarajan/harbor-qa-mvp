# Benchmark Overview

This document describes the four main benchmarks in the Harbor QA project. Each benchmark evaluates AI agents on pharmacogenomics (PGx) tasks of varying difficulty and format.

## Summary

| Benchmark | Tasks | Format | Context Provided | Evaluation Method |
|---|---|---|---|---|
| CPIC Evidence | 106 | Open-ended | 5–15 research papers | 1 deterministic + 4 LLM-judge tests |
| CPIC Zero-Context | 100 | Open-ended | None (parametric knowledge only) | 1 deterministic + 4 LLM-judge tests |
| PGx Drug QA | 100 | Multiple-choice | 1 research paper | Deterministic exact match (1 test per question) |
| Summary QA | 100 | Extraction | 16 papers + term banks | 3 deterministic tests (recall + exact count) |

Condensed subsets also exist for faster iteration: **CPIC Evidence Condensed** (27 tasks) and **CPIC Zero-Context Condensed** (72 tasks).

---

## 1. CPIC Evidence Benchmark

**Directory:** `cpic_evidence_benchmark/` — **106 tasks**

### How tasks were created

The `generate_dataset.py` script loads 106 target records from a CPIC paper dataset (`cpic_paper_dataset.jsonl`). For each gene-drug-genotype combination, it gathers the associated research papers (full-text markdown from PubMed Central, or PubMed abstracts as fallback), bundles them into a Docker environment at `/app/papers/`, and generates the task instruction and test harness. Papers are shared across tasks that belong to the same gene-guideline group.

Covers 5 CPIC guidelines: DPYD/fluoropyrimidines, UGT1A1/atazanavir, CACNA1S|RYR1/volatile anesthetics, CYP2B6/efavirenz, and SLCO1B1/statins.

### Task format

The agent is told the drug, gene, and patient genotype, then asked to read the provided papers and produce a JSON with three fields: `recommendation` (dosing recommendation), `classification` (Strong/Moderate/Optional/No Recommendation), and `implication` (clinical implication of the genotype).

### Evaluation

- **`test_classification`** — deterministic exact match on classification strength.
- **`test_action_correctness`**, **`test_recommendation_completeness`**, **`test_implication_accuracy`**, **`test_safety`** — each scored 1–5 by an LLM judge (Claude Sonnet) using a strict rubric. Must score >= 4 to pass.

### Example

**Task:** `dpyd_fluorouracil_7589436`

**Instruction (abbreviated):**
> You are a clinical pharmacogenomics expert.
> **Drug:** fluorouracil | **Gene:** DPYD | **Patient Genotype:** DPYD 2.0
> Research papers are available in `/app/papers/`. Read them and provide a clinical recommendation.

**Ground truth:**
```json
{
  "recommendation": "Based on genotype, there is no indication to change dose or therapy. Use label-recommended dosage and administration.",
  "classification": "Strong",
  "implication": ""
}
```

---

## 2. CPIC Zero-Context Benchmark

**Directory:** `cpic_zero_context/` — **100 tasks**

### How tasks were created

The `generate_dataset.py` script loads CPIC data tables (`recommendation.tsv`, `pair.tsv`, `variant_recommendations_consolidated.tsv`) and filters to Level A (strongest evidence) guidelines with single genes and clean variant descriptions. 100 tasks are selected via stratified sampling across gene-drug pairs to ensure diversity.

### Task format

Identical structure to the Evidence benchmark, except **no papers are provided**. The agent must rely entirely on its parametric knowledge of pharmacogenomics to produce the same three-field JSON.

### Evaluation

Same 5-test suite as the Evidence benchmark (1 deterministic + 4 LLM-judge).

### Example

**Task:** `cyp2d6_atomoxetine_7588715`

**Instruction (abbreviated):**
> You are a clinical pharmacogenomics expert.
> **Drug:** atomoxetine | **Gene:** CYP2D6 | **Patient Genotype:** CYP2D6 2.75
> Based on your knowledge of pharmacogenomics, provide a clinical recommendation.

**Ground truth (representative):**
```json
{
  "recommendation": "Initiate atomoxetine at recommended dose; adjust based on response and tolerability.",
  "classification": "Strong",
  "implication": "Normal metabolizer phenotype — expected normal atomoxetine metabolism"
}
```

---

## 3. PGx Drug QA Benchmark

**Directory:** `pgx_drug_qa/` — **100 tasks**

### How tasks were created

The `generate_dataset.py` groups pre-generated multiple-choice questions from `drug_mcq_options.jsonl` by their source paper (PMCID). It filters to PMCIDs that have an available full-text paper, then selects the first 100. Each task bundles all questions for a single paper together. Questions ask about drug-variant-phenotype associations extracted from that paper.

### Task format

The agent receives a single research paper at `/app/papers/{PMCID}.md` and a set of multiple-choice questions (typically 5–15 per paper). Each question has 4 options (a/b/c/d). The agent writes a JSON mapping question numbers to answer letters.

### Evaluation

One deterministic exact-match test per question (case-insensitive). Reward = fraction of questions answered correctly.

### Example

**Task:** `pmc10026301` (10 questions)

**Sample question:**
> GSTT1 null is not associated with increased likelihood of Drug Toxicity when treated with ______ in children with Leukemia, Myeloid, Acute.
> - a) 2-aminoheptanoate
> - b) 10-monohydroxy oxcarbazepine
> - c) cytarabine, daunorubicin
> - d) 1-hydroxymidazolam

**Ground truth:** `{"1": "c", "2": "d", "3": "b", "4": "b", "5": "b", "6": "a", "7": "c", "8": "c", "9": "c", "10": "b"}`

---

## 4. Summary QA Benchmark

**Directory:** `summary_qa/` — **100 tasks**

### How tasks were created

The `generate_dataset.py` loads PharmGKB summary annotations (`summary_annotations.tsv`) and their associated evidence links (`summary_ann_evidence.tsv`). It maps PMIDs to PMCIDs to locate full-text papers, then creates tasks with 16 papers each (a mix of relevant papers and distractors). Term banks of known drug and phenotype names are provided for constrained extraction.

### Task format

The agent is given a variant, gene, and phenotype category, plus 16 papers and two term banks (`drugs.txt`, `phenotypes.txt`). It must identify: (1) all drugs associated with the variant, (2) all phenotypes associated with the variant, and (3) the count of relevant papers.

### Evaluation

- **`test_drugs_recall`** — all expected drugs must appear in the agent's list.
- **`test_phenotypes_recall`** — all expected phenotypes must appear.
- **`test_relevant_paper_count`** — exact match on the count of relevant papers.

### Example

**Task:** `cyp2b6_1_cyp2b6_2_cyp2b6_6_cyp2b6_18_cyp2b6_38_1451243980`

**Instruction (abbreviated):**
> **Variant:** CYP2B6\*1, CYP2B6\*2, CYP2B6\*6, CYP2B6\*18, CYP2B6\*38
> **Gene:** CYP2B6 | **Phenotype Category:** Toxicity
> Read the papers and identify associated drugs, phenotypes, and count relevant papers.

**Ground truth:**
```json
{
  "drugs": ["efavirenz"],
  "phenotypes": ["hiv infectious disease"],
  "relevant_paper_count": 6
}
```

---

## Common Infrastructure

All benchmarks share a common task structure:

- **`task.toml`** — 600s timeout, 2048 MB memory, 10240 MB storage, internet enabled.
- **`environment/Dockerfile`** — Copies papers and resources into `/app/`.
- **`tests/test.sh`** — Runs pytest with JSON report output (`pytest-json-ctrf`).
- **Output format** — All tasks require writing structured JSON to `/app/answers.json`.
- **Scoring** — Reward = passed tests / total tests, written to `/logs/verifier/reward.txt`.
