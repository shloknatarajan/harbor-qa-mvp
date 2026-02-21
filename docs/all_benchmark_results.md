# Benchmark Results: Evaluating AI Coding Agents on Pharmacogenomics Tasks

## Overview

We evaluated two AI coding agent systems — **Codex CLI** (OpenAI, using GPT-5) and **Claude Code** (Anthropic, using Claude Sonnet 4.6) — across four pharmacogenomics (PGx) benchmarks of increasing complexity. Each benchmark tests a distinct capability: multiple-choice comprehension, structured information extraction, evidence-based clinical reasoning, and parametric knowledge recall. All tasks were executed in isolated Docker environments via the Harbor benchmark framework, with a 600-second timeout, 2048 MB memory, and 10240 MB storage per task.

### Agents Under Evaluation

| Agent | Underlying Model | Interface |
|-------|-----------------|-----------|
| Codex CLI | GPT-5 (OpenAI) | Shell-based coding agent with file I/O and web search tools |
| Claude Code | Claude Sonnet 4.6 (Anthropic) | Shell-based coding agent with file I/O tools |

### Summary of Results

| Benchmark | Task Format | N (evaluated) | Agent | Mean Reward | Pass Rate |
|-----------|------------|:-:|-------|:-:|:-:|
| PGx Drug QA | Multiple-choice | 98 | Codex (GPT-5) | 0.845 | 83.7% |
| PGx Drug QA | Multiple-choice | 30 | Claude Code | 0.883 | 86.7% |
| Summary QA | Extraction | 100 | Codex (GPT-5) | 0.63 | 24.0% |
| Summary QA | Extraction | 100 | Claude Code | 0.60 | 31.0% |
| CPIC Evidence | Open-ended generation | 15 | Claude Code | 0.747 | 53.3% |
| CPIC Zero-Context | Open-ended generation | 50 | Claude Code | 0.64 | 36.0% |

---

## 1. PGx Drug QA Benchmark

### Task Design

The PGx Drug QA benchmark consists of **100 tasks**, each containing multiple-choice questions (4 options, a/b/c/d) derived from a single PubMed Central research paper. Questions assess drug–variant–phenotype associations extracted from the paper. Each task bundles 2–98 questions for one paper (median: 4 questions), and the agent receives the full-text paper as a markdown file. The agent must output a JSON mapping question numbers to answer letters.

**Evaluation.** Each question is scored by deterministic exact match (case-insensitive). The task reward is the fraction of questions answered correctly (0.0–1.0).

### Results

**Table 1.** PGx Drug QA performance on the full dataset.

| Agent | Model | Tasks Attempted | Tasks Evaluated | Mean Reward | Pass (1.0) | Partial | Fail (0.0) |
|-------|-------|:-:|:-:|:-:|:-:|:-:|:-:|
| Codex CLI | GPT-5 | 100 | 98 | **0.845** | 82 (83.7%) | 1 (1.0%) | 15 (15.3%) |
| Claude Code | Claude Sonnet 4.6 | 100 | 30 | **0.883** | 26 (86.7%) | 1 (3.3%) | 3 (10.0%) |

Two Codex tasks were excluded due to infrastructure timeouts (tasks with 98 and 20 questions exceeding the 600s limit). The Claude Code run was terminated after 30 tasks due to API credit exhaustion; the remaining 70 tasks are not included.

**Head-to-head comparison.** On the 30 tasks where both agents produced valid results:

| Agent | Mean Reward | Pass | Partial | Fail |
|-------|:-:|:-:|:-:|:-:|
| Codex (GPT-5) | 0.917 | 27 (90.0%) | 1 (3.3%) | 2 (6.7%) |
| Claude Code | 0.883 | 26 (86.7%) | 1 (3.3%) | 3 (10.0%) |

The agents agreed on 25 of 30 tasks. Among the 5 disagreements, Claude Code outperformed Codex on 3 tasks (edoxaban, tramadol, and fulvestrant/anastrozole questions), while Codex outperformed on 1 task (codeine/morphine/tramadol). One task showed a split (Claude partial, Codex fail on carbamazepine). Both agents failed on 2 tasks involving multi-drug regimens (platinum compounds, ethambutol/isoniazid/pyrazinamide/rifampin).

### Error Analysis

We identified three recurring failure patterns across both agents:

1. **Multi-drug combination tasks** are disproportionately difficult. Tasks involving complex regimens (e.g., ethambutol/isoniazid/pyrazinamide/rifampin) had the highest failure rates for both agents, likely due to the difficulty of attributing pharmacogenomic effects to individual drugs within a combination.

2. **Drug class vs. specific drug confusion.** Some failures involved agents selecting answers at the wrong level of specificity — confusing a drug class (e.g., "Platinum compounds," "SSRIs") with specific agents within that class.

3. **Single-drug fixation (Claude Code).** Claude Code showed a tendency to anchor on a single drug mentioned in the paper, ignoring other relevant drugs. For example, on `pmc10318569`, Claude fixated on morphine-3-glucuronide rather than identifying the full set of codeine, morphine, and tramadol.

**Codex failures on the full 98-task set** (15 failures, 15.3%) included: opioid multi-drug tasks (pmc10139129), CHOP/rituximab combinations (pmc10216814), multi-drug anti-TB regimens (pmc10501134, pmc10541540), SSRI class confusion (pmc10416089), and capecitabine/fluorouracil differentiation (pmc10487873).

---

## 2. Summary QA Benchmark

### Task Design

The Summary QA benchmark consists of **100 tasks** derived from PharmGKB summary annotations. Each task provides the agent with a variant, gene, and phenotype category, along with 16 research papers (a mix of relevant papers and distractors) and two term banks constraining the answer vocabulary (`drugs.txt` and `phenotypes.txt`). The agent must identify: (1) all drugs associated with the variant from the term bank, (2) all phenotypes associated with the variant from the term bank, and (3) the exact count of relevant papers.

**Evaluation.** Three deterministic tests:
- `test_drugs_recall` — all expected drugs must appear in the agent's list (recall-only; extra drugs are permitted).
- `test_phenotypes_recall` — all expected phenotypes must appear (recall-only; extra phenotypes are permitted).
- `test_relevant_paper_count` — exact match on the integer count of relevant papers.

Task reward = fraction of tests passed (0.0, 0.33, 0.67, or 1.0).

### Results

**Table 2.** Summary QA performance on the full 100-task dataset.

| Agent | Model | Tasks Evaluated | Errors | Mean Reward | Pass (1.0) | Partial | Fail (0.0) | Duration |
|-------|-------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Codex CLI | GPT-5 | 100 | 0 | **0.63** | 24 (24.0%) | 68 (68.0%) | 8 (8.0%) | 247 min |
| Claude Code | Claude Sonnet 4.6 | 100 | 5 | **0.60** | 31 (31.0%) | 44 (44.0%) | 19 (19.0%) | 242 min |

Both agents completed the full 100-task dataset in approximately 4 hours with single-task concurrency. An additional Codex run using o4-mini achieved 0.0 mean reward across all 100 tasks — o4-mini preferentially invoked web search over reading local files and never produced output files.

### Error Analysis

**Reward distribution.** The two agents exhibit complementary error profiles. Claude Code achieves more perfect scores (31 vs. 24 full passes) but fails completely more often (19 vs. 8 zero-reward tasks). Codex is more consistent, with 68% of tasks earning partial credit vs. 44% for Claude Code.

**Per-subtask failure rates** (estimated from partial-score distributions):

| Subtask | Primary Failure Mode | Frequency |
|---------|---------------------|-----------|
| Drug recall | Reliable for both agents | < 10% failure rate |
| Phenotype recall | String-matching mismatches | ~40–50% failure rate |
| Paper count | Off-by-1-to-4 errors in both directions | ~50–60% failure rate |

**Phenotype string-matching failures.** The dominant failure mode across both agents is semantic mismatch between agent-generated phenotype terms and the gold-standard vocabulary. Common examples:

| Agent Output | Expected Term |
|-------------|---------------|
| "depression", "major depressive disorder" | "mental disorders" |
| "drug hypersensitivity syndrome" | "drug hypersensitivity" |

Agents identify the correct medical concepts but at a different level of granularity than the gold standard. This is partially an artifact of the evaluation design: 22 of 100 tasks have empty expected phenotype lists, making the phenotype test vacuously true and inflating overall accuracy.

**Paper count errors.** Paper count mismatches are typically small (off by 1–4) and occur in both directions. The ground truth is derived indirectly through a PMID-to-PMCID mapping chain (annotation evidence → PMIDs → PMCID conversion → papers on disk), introducing potential ambiguity in what constitutes a "relevant" paper.

**Agent-specific failure modes.** When both agents fail completely, they do so differently:
- **Codex** writes `answers.json` with empty fields (`{"drugs": [], "phenotypes": [], "relevant_paper_count": 0}`), indicating it ran but failed to extract information.
- **Claude Code** fails to create `answers.json` entirely, indicating the agent either timed out or did not complete execution, resulting in test setup errors rather than test failures.

**Resource consumption.** Token usage varies dramatically across tasks. The largest observed single-task input was 2.6M tokens (a CYP2D6 task where the agent read most or all 16 papers in full), while smaller tasks consumed as few as 112K tokens. Output tokens are consistently minimal (42–235 tokens), as the final answer is a small JSON object.

---

## 3. CPIC Evidence Benchmark

### Task Design

The CPIC Evidence benchmark consists of **106 tasks** spanning 5 CPIC pharmacogenomics guidelines: DPYD/fluoropyrimidines (10 tasks), UGT1A1/atazanavir (4 tasks), CACNA1S|RYR1/volatile anesthetics and succinylcholine (56 tasks), CYP2B6/efavirenz (6 tasks), and SLCO1B1/statins (30 tasks). For each task, the agent receives a drug, gene, and patient genotype along with 5–88 research papers (full-text markdown from PubMed Central when available, PubMed abstracts as fallback). Paper availability varies by guideline: DPYD has 78% full-text coverage, UGT1A1 and CACNA1S|RYR1 have 50%, CYP2B6 has 44%, and SLCO1B1 has 40%.

The agent must produce a structured JSON with three fields:
- `recommendation` — a clinical dosing recommendation
- `classification` — recommendation strength (Strong / Moderate / Optional / No Recommendation)
- `implication` — the clinical implication of the patient's genotype

**Evaluation.** Five tests per task:
- `test_classification` — deterministic exact match on recommendation strength.
- `test_action_correctness`, `test_recommendation_completeness`, `test_implication_accuracy`, `test_safety` — each scored 1–5 by an LLM judge (Claude Sonnet) using a standardized rubric. A score ≥ 4 is required to pass.

Task reward = fraction of 5 tests passed (0.0, 0.2, 0.4, 0.6, 0.8, or 1.0).

### Results

**Table 3.** CPIC Evidence benchmark results (Claude Code only; no Codex runs attempted).

| Run | Tasks Attempted | Tasks Evaluated | Mean Reward | Pass (1.0) | Partial (>0, <1) | Fail (0.0) | Infra Errors |
|-----|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 50-task run | 50 | 15 | **0.747** | 8 (53.3%) | 7 (46.7%) | 0 (0.0%) | 9 |

Of the 50 tasks attempted, 9 failed due to agent setup errors (exit code 56) and 26 produced no results, leaving **15 tasks with valid evaluations**. The limited sample size warrants caution in interpreting these results.

**Smaller exploratory runs** (not used for primary reporting due to sampling bias):

| Tasks Attempted | Tasks Evaluated | Mean Reward | Notes |
|:-:|:-:|:-:|---|
| 10 | 10 | 0.90 | 8/10 tasks from a single CACNA1S/RYR1 guideline — not independent |
| 5 | 5 | 0.95 | Small, easy subset |
| 5 | 5 | 0.68 | Small subset, harder tasks |

The inflated scores in small runs (0.90–0.95) reflect sampling bias: the 10-task run contained 8 CACNA1S/RYR1 volatile anesthetic tasks from a single guideline that share the same evidence papers, making them effectively a single independent data point. The 50-task run included harder tasks (DPYD fluorouracil, SLCO1B1 statins) with scores of 0.2–0.6.

### Error Analysis

**Partial score distribution.** Partial scores cluster at 0.4 (2 of 5 tests passed), typically reflecting correct classification plus one passing LLM-judge test. The most common failure mode is on the implication and completeness dimensions, where the LLM judge scores edge-case responses below the ≥ 4 threshold.

**Task difficulty varies by guideline.** CACNA1S/RYR1 tasks (volatile anesthetics, succinylcholine) appear to be the easiest — likely because the clinical recommendations are well-defined and relatively uniform across genotype combinations. In contrast, DPYD (fluoropyrimidines) and SLCO1B1 (statins) tasks require nuanced dose-adjustment reasoning that varies substantially by genotype, leading to lower scores.

---

## 4. CPIC Zero-Context Benchmark

### Task Design

The CPIC Zero-Context benchmark consists of **100 tasks** selected via stratified sampling across gene–drug pairs from Level A (strongest evidence) CPIC guidelines. The task format is identical to the Evidence benchmark — the agent must produce the same three-field JSON (recommendation, classification, implication) — but **no research papers are provided**. The agent must rely entirely on its parametric knowledge of pharmacogenomics.

Tasks were generated from CPIC data tables (`recommendation.tsv`, `pair.tsv`, `variant_recommendations_consolidated.tsv`), filtered to single-gene entries with clean variant descriptions.

**Evaluation.** Same 5-test suite as the Evidence benchmark (1 deterministic + 4 LLM-judge).

### Results

**Table 4.** CPIC Zero-Context benchmark results (Claude Code only; no Codex runs attempted).

| Tasks Attempted | Tasks Evaluated | Mean Reward | Pass (1.0) | Partial | Fail (0.0) | Duration |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 50 | 50 | **0.64** | 18 (36.0%) | 31 (62.0%) | 1 (2.0%) | 14 min 55s |

### Error Analysis

**Effect of retrieval augmentation.** Comparing the Evidence and Zero-Context benchmarks provides a direct measure of the value of provided research papers. Claude Code achieves a mean reward of 0.747 with evidence papers vs. 0.64 without — a **0.107 absolute improvement** (16.7% relative) from retrieval augmentation. While the Evidence sample (n=15) is small, the direction is consistent: providing relevant literature improves clinical recommendation quality.

**Performance by gene–drug pair.** Performance varies substantially across pharmacogenomic domains:

| Performance Tier | Gene–Drug Pairs |
|-----------------|-----------------|
| Strong (≥ 0.8 reward) | G6PD (rasburicase, tafenoquine, primaquine), MT-RNR1 (aminoglycosides), HLA-B (abacavir) |
| Moderate (0.4–0.8) | CYP2D6 (codeine, tramadol), DPYD (fluorouracil), TPMT (azathioprine) |
| Weak (< 0.4) | CYP2C19 (lansoprazole, piroxicam), CYP2D6 (atomoxetine), NAT2 (hydralazine) |

**Dominant error mode.** The most frequent error is recommendation classification mismatch — the agent produces a clinically reasonable recommendation but assigns the wrong strength level (e.g., "Strong" vs. "Moderate"). This suggests that while the model's parametric knowledge captures the general clinical guidance, it struggles with the specific evidence-grading criteria used by CPIC.

---

## Cross-Benchmark Analysis

### Effect of Task Format on Performance

Performance varies systematically with task format. Multiple-choice tasks (PGx Drug QA) yield the highest scores (0.845–0.883), followed by open-ended generation with evidence (CPIC Evidence, 0.747), open-ended generation without evidence (CPIC Zero-Context, 0.64), and structured extraction (Summary QA, 0.60–0.63). This ordering likely reflects both the intrinsic difficulty of each format and the degree of output constraint: multiple-choice tasks require only letter selection, while extraction and generation tasks demand precise string matching against gold-standard vocabularies.

### Agent Comparison

On the two benchmarks where both agents were evaluated on the same task set:

| Benchmark | Codex (GPT-5) | Claude Code | Difference |
|-----------|:-:|:-:|:-:|
| PGx Drug QA (head-to-head, n=30) | 0.917 | 0.883 | +0.034 (Codex) |
| Summary QA (full, n=100) | 0.63 | 0.60 | +0.03 (Codex) |

Performance differences between agents are small (≤ 0.034 mean reward) and not statistically significant given the sample sizes. The agents exhibit complementary strengths: Claude Code achieves more perfect scores on Summary QA (31 vs. 24) but fails completely more often (19 vs. 8), while Codex is more consistent. On PGx Drug QA, Codex outperforms on aggregate but Claude Code wins on 3 of 5 disagreement tasks.

### Value of Retrieval Augmentation

The CPIC Evidence vs. Zero-Context comparison provides a controlled measurement of retrieval-augmented generation (RAG) value for clinical pharmacogenomics tasks. With the same agent, model, and evaluation criteria, providing relevant research papers improves mean reward from 0.64 to 0.747 — a meaningful but not transformative gain. This suggests that current frontier models encode substantial pharmacogenomics knowledge parametrically, but evidence-grounded reasoning still provides measurable benefit, particularly for nuanced dose-adjustment recommendations and recommendation strength classification.

### Model Compatibility

Not all model–agent combinations are functional for these benchmarks. Codex CLI with o4-mini achieved 0.0 across all 100 Summary QA tasks because the Codex CLI unconditionally registers a `web_search_preview` tool, and o4-mini preferentially invokes web search over reading local files — it never executes shell commands to read papers or write output. Codex CLI with o3-mini fails entirely because o3-mini does not support the `web_search_preview` tool, causing API errors. Only GPT-5 correctly prioritizes shell-based file I/O over web search in the Codex CLI environment.

### Limitations

1. **Incomplete agent coverage.** Codex was not evaluated on the CPIC Evidence or CPIC Zero-Context benchmarks, and Claude Code completed only 30 of 100 PGx Drug QA tasks due to API credit exhaustion.

2. **Small effective sample sizes.** The CPIC Evidence benchmark yielded only 15 valid evaluations from 50 attempted tasks due to infrastructure failures, limiting statistical power.

3. **LLM-judge evaluation.** The CPIC benchmarks use an LLM judge (Claude Sonnet) for 4 of 5 tests, introducing potential scoring variability. The ≥ 4/5 pass threshold was chosen to balance sensitivity with specificity, but borderline cases may be scored inconsistently across runs.

4. **Task clustering.** The CPIC Evidence benchmark contains 56 CACNA1S/RYR1 tasks from a single guideline (53% of all tasks), which share the same evidence papers. Performance on these tasks is highly correlated, reducing the effective independent sample size.

5. **Evaluation artifacts.** In Summary QA, 22% of tasks have empty expected phenotype lists, making the phenotype recall test vacuously true. The paper count ground truth is derived through an indirect PMID-to-PMCID mapping chain rather than direct relevance annotation, potentially introducing noise.
