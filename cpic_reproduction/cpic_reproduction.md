# CPIC Reproduction

## Overview
**Goal:** Have a model attempt to reproduce CPIC clinical pharmacogenomics guidelines for a variant–drug combination using relevant papers as context. Compare the model's output against the actual CPIC guideline recommendation.

## Data Landscape

### Ground Truth: CPIC Recommendations
- `data/cpic_data/variant_recommendations_consolidated.tsv` — 2,129 variant–drug recommendations
  - 727 single-gene, 1,402 multi-gene (combinatorial)
  - 109 unique drugs, 21 unique gene/gene-combo groups
  - Fields: `rec_id`, `drug`, `recommendation`, `variants` (JSON array), `lookup_genes`, `component_count`
- `data/cpic_data/recommendation.tsv` — Full detail: includes `implications`, `classification` (Strong/Moderate/Optional), `phenotypes`, `activityscore`, `population`, `comments`
- `data/cpic_data/guideline.tsv` — 31 CPIC guidelines mapping gene–drug pairs to guideline IDs and URLs
- `data/cpic_data/pair.tsv` — Gene–drug pairs with CPIC level (A/B/C/D), evidence level, and citation PMIDs

### Paper Availability
- `data/papers/` — 3,064 PMC papers as Markdown (from PharmGKB annotations, **not** CPIC guideline papers)
- `data/cpic_data/publication.tsv` — CPIC guideline publications (the actual CPIC clinical guideline papers), ~33 with PMCIDs
- **Key gap:** The CPIC guideline papers themselves are NOT in `data/papers/`. The existing papers are PharmGKB variant annotation evidence papers — a different corpus.

### Linking Tables
- `pair.tsv` citations → PMIDs of the CPIC guideline papers (not the underlying evidence)
- `publication.tsv` → Maps guideline IDs to the published CPIC guideline paper PMIDs/PMCIDs
- `recommendation.tsv` → Maps each recommendation to a `guidelineid`

## Task Design Options

### Option A: Evidence-Based Reproduction (Preferred — Hardest, Most Interesting)
Give the model the **underlying research papers** that CPIC guidelines cite as evidence, and ask it to derive the clinical recommendation.

- **Input:** Primary research papers + variant + drug + gene
- **Output:** Model produces a dosing recommendation
- **Evaluation:** Compare against CPIC guideline recommendation text
- **Challenge:** Need to source the evidence papers. These are cited *within* the CPIC guideline papers, not directly available in our data. Requires either:
  1. Fetching CPIC guideline papers → parsing their references → fetching those papers
  2. Using PharmGKB annotation evidence papers where they overlap with CPIC gene–drug pairs

### Option B: Guideline Paper Reading Comprehension
Give the model the **CPIC guideline paper itself** and ask it to extract the recommendation for a specific variant–drug pair.

- **Input:** CPIC guideline paper + variant + drug
- **Output:** Extracted recommendation
- **Evaluation:** Exact/fuzzy match against `recommendation.tsv`
- **Pro:** Straightforward, tests reading comprehension of dense clinical tables
- **Con:** Somewhat trivial — the answer is literally in the paper

### Option C: Zero-Context Prediction (No Papers)
Give the model only the variant, drug, and gene — no papers — and test if it can produce the CPIC recommendation from parametric knowledge alone.

- **Input:** Variant + drug + gene (no papers)
- **Output:** Model's predicted recommendation
- **Evaluation:** Compare against CPIC guideline
- **Pro:** Tests model's internalized pharmacogenomics knowledge, easy to set up
- **Con:** Not really "reproduction from evidence" — more of a knowledge recall benchmark

### Recommended: Start with Option C, then build toward Option A
Option C requires no paper fetching and tests an interesting baseline. Option A is the end goal but needs a paper-sourcing pipeline.

## Implementation Plan

### Phase 1: Dataset Preparation (`generate_dataset.py`)

#### Step 1.1: Filter Recommendations for the Benchmark
- Start with **single-gene recommendations** (`component_count == 1`) — 727 rows. Multi-gene combinatorial recs are more complex and can be added later.
- Group by `guidelineid` via `recommendation.tsv` join.
- Filter to CPIC Level A pairs (strongest evidence) via `pair.tsv` join — these have the most robust ground truth.
- Select a representative subset (e.g., 100 tasks) sampling across different genes, drugs, and recommendation types.

#### Step 1.2: Build the Ground Truth for Each Task
From `recommendation.tsv`, extract for each selected recommendation:
- `drugrecommendation` — the target text to reproduce
- `classification` — strength of recommendation (Strong/Moderate/Optional)
- `implications` — JSON dict of gene → clinical implication
- `phenotypes`, `activityscore`, `lookupkey` — context about the patient's genotype

#### Step 1.3: Source Papers (for Option A, Phase 2)
- Fetch CPIC guideline papers using PMCIDs from `publication.tsv` (many available via PMC Open Access)
- Parse references within those papers to find the underlying evidence PMIDs
- Cross-reference with `data/papers/` for any overlap
- Fetch additional evidence papers as needed via PMC API
- Store in `data/cpic_papers/`

### Phase 2: Harbor Task Generation

#### Task Structure (per recommendation)
```
harbor-qa-mvp/
  cpic_reproduction/                    # shared data and docs
    build_paper_dataset.py
    cpic_paper_dataset.jsonl
    cpic_paper_dataset.tsv
    cpic_reproduction.md
  cpic_zero_context/                    # zero-context tasks
    generate_dataset.py
    <task dirs...>
  cpic_evidence_benchmark/              # LLM-judge benchmark
    generate_dataset.py
    <task dirs...>
```

#### Instruction Prompt Design
The prompt should ask the model to:
1. Given a patient genotype (variant/phenotype), predict the clinical recommendation for a specific drug
2. Provide the recommendation text (dosing guidance)
3. Classify the strength (Strong/Moderate/Optional)
4. Explain the clinical implication

```markdown
You are a clinical pharmacogenomics expert.

**Drug:** {drug}
**Gene:** {gene}
**Patient Genotype:** {variant_description}
**Phenotype/Activity:** {phenotype_or_activity_score}

Based on pharmacogenomics evidence, what is the clinical dosing recommendation
for this patient? Provide:
1. A specific dosing recommendation
2. The strength of this recommendation (Strong, Moderate, or Optional)
3. The clinical implication of this genotype for this drug

Write your answer to `/app/answers.json`.
```

#### Evaluation Strategy
Pharmacogenomics recommendations are semi-structured natural language — exact string match is too strict. Evaluation options:

1. **Semantic similarity** — Embed both the predicted and ground truth recommendation, compute cosine similarity. Threshold for pass/fail.
2. **Key phrase extraction** — Check if critical action words appear (e.g., "contraindicated", "avoid", "standard dosing", "reduce dose by 50%").
3. **Classification accuracy** — Did the model get the *direction* right? Categories:
   - Standard dosing / no change
   - Dose reduction (with magnitude)
   - Alternative drug recommended
   - Contraindicated / avoid
   - Increased dose
4. **LLM-as-judge** — Use a separate model call to score the prediction against ground truth (most flexible, but adds cost/complexity).

**Recommended approach:** Combine (3) and (2). Map each CPIC recommendation to a discrete action category, then check if the model's response matches the category AND contains key clinical terms.

### Phase 3: Run and Analyze

#### Running
```bash
# Zero-context tasks
python main.py -p cpic_zero_context -a claude-code -n 3 -l 50

# Evidence benchmark (LLM-judge)
python main.py -p cpic_evidence_benchmark -a claude-code -n 3 -l 50
```

#### Metrics to Track
- **Action category accuracy** — Did the model recommend the right action direction?
- **Classification accuracy** — Did it get Strong/Moderate/Optional right?
- **Per-gene accuracy** — Are some genes easier than others?
- **Single vs. multi-gene** — How does performance degrade with combinatorial genotypes?
- **By CPIC level** — Is Level A (most evidence) easier than Level B?

## Open Questions
1. **Paper sourcing for Option A:** What's the best way to get the underlying evidence papers? PMC API? Manual curation for a subset?
2. **Multi-gene recommendations:** Should we tackle these in Phase 1 or defer? They represent 65% of recommendations but are significantly more complex.
3. **Evaluation granularity:** Is action-category matching sufficient, or do we need to capture dose-magnitude accuracy (e.g., "reduce by 25%" vs "reduce by 50%")?
4. **Distractor papers:** Should we include irrelevant papers (as in `summary_qa`) to test the model's ability to identify relevant evidence?
5. **How to handle "No Result" / "Indeterminate" variants** — many recommendations cover these edge cases. Include or exclude?

## File References
- Ground truth: `data/cpic_data/variant_recommendations_consolidated.tsv`
- Full recommendations: `data/cpic_data/recommendation.tsv`
- Guidelines: `data/cpic_data/guideline.tsv`
- Gene–drug pairs: `data/cpic_data/pair.tsv`
- Guideline publications: `data/cpic_data/publication.tsv`
- Existing papers: `data/papers/`
- PharmGKB annotations: `data/raw/summaryAnnotations/`
- Existing task generators: `summary_qa/generate_questions.py`, `pgx_drug_qa/generate_dataset.py`
