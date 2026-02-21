# Model Performance Summary

Last updated: 2026-02-20

## Agents

| Agent | Model | Interface |
|-------|-------|-----------|
| Codex CLI | GPT-5 (OpenAI) | Shell-based coding agent with file I/O and web search |
| Claude Code | Claude Sonnet 4.6 (Anthropic) | Shell-based coding agent with file I/O |

All tasks run in isolated Docker environments via the Harbor benchmark framework (600s timeout, 2048 MB memory, 10240 MB storage, single-task concurrency).

---

## Results at a Glance

| Benchmark | Format | N | Agent | Mean Reward | Pass (1.0) | Partial | Fail (0.0) |
|-----------|--------|:-:|-------|:-:|:-:|:-:|:-:|
| **PGx Drug QA** | Multiple-choice | 98 | Codex (GPT-5) | **0.845** | 82 (83.7%) | 1 (1.0%) | 15 (15.3%) |
| | | 30 | Claude Code | **0.883** | 26 (86.7%) | 1 (3.3%) | 3 (10.0%) |
| **Summary QA** | Extraction | 100 | Codex (GPT-5) | **0.63** | 24 (24.0%) | 68 (68.0%) | 8 (8.0%) |
| | | 100 | Claude Code | **0.60** | 31 (31.0%) | 44 (44.0%) | 19 (19.0%) |
| **CPIC Evidence** | Open-ended + papers | 70* | Codex (GPT-5) | **0.546** | 15 (21.4%) | 52 (74.3%) | 3 (4.3%) |
| | | 15† | Claude Code | **0.747** | 8 (53.3%) | 7 (46.7%) | 0 (0.0%) |
| **CPIC Zero-Context** | Open-ended, no papers | 67* | Codex (GPT-5) | **0.129** | 0 (0.0%) | 45 (67.2%) | 22 (32.8%) |
| | | 50 | Claude Code | **0.64** | 18 (36.0%) | 31 (62.0%) | 1 (2.0%) |

\* Codex CPIC runs used the condensed task subsets (27 evidence tasks, 72 zero-context tasks). 3 infra errors excluded from zero-context count.
† Claude Code attempted 50 CPIC Evidence tasks but only 15 produced valid evaluations (9 infra errors, 26 no output).

---

## 1. PGx Drug QA

**100 tasks** — multiple-choice questions (4 options) derived from individual PubMed Central papers. Agent reads one full-text paper and answers 2–98 questions per task. Scored by deterministic exact match; reward = fraction correct.

### Best runs

| Agent | Tasks Evaluated | Mean Reward | Duration | Job |
|-------|:-:|:-:|:-:|---|
| Codex (GPT-5) | 98 | 0.845 | 244 min | `2026-02-20__02-47-55` |
| Claude Code | 30 | 0.883 | — | `2026-02-20__02-40-26` |

Codex excluded 2 tasks (infra timeouts on 98-question and 20-question papers). Claude Code stopped after 30 tasks due to API credit exhaustion.

### Head-to-head (30 overlapping tasks)

| Agent | Mean Reward | Pass | Fail |
|-------|:-:|:-:|:-:|
| Codex (GPT-5) | 0.917 | 27 | 2 |
| Claude Code | 0.883 | 26 | 3 |

Agents agreed on 25/30 tasks. On 5 disagreements: Claude won 3 (edoxaban, tramadol, fulvestrant/anastrozole), Codex won 1 (codeine/morphine/tramadol), split on 1 (carbamazepine).

### Failure patterns

- **Multi-drug regimens** are hardest — both agents fail on complex combinations (e.g., ethambutol/isoniazid/pyrazinamide/rifampin).
- **Drug class vs. specific drug confusion** — e.g., "Platinum compounds" vs. specific agents within the class.
- **Single-drug fixation (Claude)** — anchors on one drug, ignoring others (e.g., morphine-3-glucuronide instead of codeine/morphine/tramadol).

---

## 2. Summary QA

**100 tasks** — structured extraction from 16 papers per task (mix of relevant + distractors). Agent identifies drugs, phenotypes (constrained by term banks), and counts relevant papers. Three deterministic tests: drug recall, phenotype recall, paper count exact match. Reward = fraction of 3 tests passed.

### Best runs

| Agent | Tasks | Mean Reward | Pass | Partial | Fail | Duration | Job |
|-------|:-:|:-:|:-:|:-:|:-:|:-:|---|
| Codex (GPT-5) | 100 | 0.63 | 24 | 68 | 8 | 247 min | `2026-02-17__23-48-08` |
| Claude Code | 100 | 0.60 | 31 | 44 | 19 | 242 min | `2026-02-17__23-25-36` |
| Codex (o4-mini) | 100 | 0.00 | 0 | 0 | 100 | 78 min | `2026-02-18__03-55-41` |

### Error profiles

The agents have complementary failure modes:

| | Codex (GPT-5) | Claude Code |
|---|---|---|
| Full passes (1.0) | 24 | **31** |
| Complete failures (0.0) | **8** | 19 |
| Failure mode | Writes empty `answers.json` | Never creates `answers.json` |

**Per-subtask failure rates:**

| Subtask | Failure Rate | Primary Issue |
|---------|:-:|---|
| Drug recall | < 10% | Reliable for both agents |
| Phenotype recall | ~40–50% | String-matching mismatches (e.g., "depression" vs. "mental disorders") |
| Paper count | ~50–60% | Off-by-1-to-4 errors in both directions |

### Why o4-mini scores 0.0

Codex CLI unconditionally registers `web_search_preview`. o4-mini preferentially invokes web search over reading local files and never writes output. Only GPT-5 correctly prioritizes shell-based file I/O.

---

## 3. CPIC Evidence Benchmark

**106 tasks** (condensed subset: 27 tasks) across 5 CPIC guidelines. Agent receives drug, gene, patient genotype, and 5–88 research papers. Must produce a JSON with `recommendation`, `classification` (Strong/Moderate/Optional/No Recommendation), and `implication`. Five tests: 1 deterministic (classification match) + 4 LLM-judge (scored 1–5, must be >= 4).

### Best runs

| Agent | Dataset | Tasks Evaluated | Mean Reward | Pass | Partial | Fail | Job |
|-------|---------|:-:|:-:|:-:|:-:|:-:|---|
| Codex (GPT-5) | Condensed (27 tasks) | 70 | 0.546 | 15 | 52 | 3 | `2026-02-20__15-48-37` |
| Claude Code | Full (106 tasks) | 15* | 0.747 | 8 | 7 | 0 | `2026-02-20__00-32-10` |
| Claude Code | Full (106 tasks) | 10 | 0.900 | 7 | 3 | 0 | `2026-02-19__22-58-33` |

\* 50 attempted; 9 infra errors + 26 no output = 15 valid evaluations.

The 10-task Claude run (0.90) is inflated — 8/10 tasks came from a single CACNA1S/RYR1 guideline sharing the same papers.

### Codex vs. Claude on CPIC Evidence

Codex achieves a lower mean reward (0.546 vs. 0.747) but runs on a broader set of tasks with zero infra errors. Claude's higher score comes from a smaller, potentially easier subset. Codex partial scores cluster at 0.2–0.4 (classification correct + 0–1 LLM tests passing), while Claude partials cluster at 0.4–0.8.

### Difficulty by guideline

| Guideline | Difficulty | Notes |
|-----------|-----------|-------|
| CACNA1S/RYR1 (volatile anesthetics) | Easiest | Uniform recommendations, well-defined |
| HLA-B (abacavir, allopurinol) | Easy | Clear binary recommendations |
| DPYD (fluoropyrimidines) | Moderate | Nuanced dose-adjustment by genotype |
| SLCO1B1 (statins) | Hard | Complex dose-response relationships |
| CYP2D6 (atomoxetine, nortriptyline) | Hard | Many genotype variants, subtle distinctions |

---

## 4. CPIC Zero-Context Benchmark

**100 tasks** (condensed subset: 72 tasks) — identical format to CPIC Evidence but **no papers provided**. Agent relies entirely on parametric knowledge. Same 5-test evaluation.

### Best runs

| Agent | Dataset | Tasks | Mean Reward | Pass | Partial | Fail | Job |
|-------|---------|:-:|:-:|:-:|:-:|:-:|---|
| Claude Code | Full (100 tasks) | 50 | 0.64 | 18 | 31 | 1 | `2026-02-19__23-51-11` |
| Codex (GPT-5) | Condensed (72 tasks) | 67* | 0.129 | 0 | 45 | 22 | `2026-02-20__18-26-02` |

\* 3 infra errors excluded.

### Large gap between agents

Claude Code dramatically outperforms Codex on zero-context tasks (0.64 vs. 0.129). Codex achieves at most 0.2 reward on any single task, never passing all 5 tests. This suggests GPT-5's parametric pharmacogenomics knowledge is substantially weaker than Claude Sonnet 4.6's, or that Codex CLI's shell-based execution introduces overhead that hinders pure knowledge tasks.

### Value of retrieval augmentation (Claude Code)

| Condition | Mean Reward | N |
|-----------|:-:|:-:|
| With papers (Evidence) | 0.747 | 15 |
| Without papers (Zero-Context) | 0.64 | 50 |
| **Improvement from papers** | **+0.107** (+16.7% relative) | |

Providing research papers improves performance, particularly on recommendation strength classification and nuanced dose-adjustment reasoning.

### Performance by gene-drug pair (Claude, Zero-Context)

| Tier | Gene-Drug Pairs |
|------|----------------|
| Strong (>= 0.8) | G6PD (rasburicase, tafenoquine, primaquine), MT-RNR1 (aminoglycosides), HLA-B (abacavir) |
| Moderate (0.4–0.8) | CYP2D6 (codeine, tramadol), DPYD (fluorouracil), TPMT (azathioprine) |
| Weak (< 0.4) | CYP2C19 (lansoprazole, piroxicam), CYP2D6 (atomoxetine), NAT2 (hydralazine) |

---

## Cross-Benchmark Summary

### Performance by task format

| Rank | Benchmark | Best Score | Format |
|:-:|-----------|:-:|---|
| 1 | PGx Drug QA | 0.883 | Multiple-choice with paper |
| 2 | CPIC Evidence | 0.747 | Open-ended generation with papers |
| 3 | CPIC Zero-Context | 0.64 | Open-ended generation, no papers |
| 4 | Summary QA | 0.63 | Structured extraction from multiple papers |

Multiple-choice is easiest; structured extraction from many papers is hardest.

### Agent comparison (benchmarks with both agents)

| Benchmark | Codex (GPT-5) | Claude Code | Delta |
|-----------|:-:|:-:|:-:|
| PGx Drug QA (head-to-head, n=30) | 0.917 | 0.883 | +0.034 Codex |
| Summary QA (n=100) | 0.63 | 0.60 | +0.03 Codex |
| CPIC Evidence (condensed vs. full) | 0.546 | 0.747 | +0.201 Claude* |
| CPIC Zero-Context (condensed vs. full) | 0.129 | 0.64 | +0.511 Claude |

\* Not directly comparable — different task subsets and sample sizes.

On closed-ended tasks (PGx Drug QA, Summary QA), performance is nearly identical. On open-ended clinical reasoning tasks (CPIC), Claude Code substantially outperforms Codex.

---

## Known Limitations

1. **Incomplete coverage.** Claude Code completed only 30/100 PGx Drug QA tasks (credit exhaustion). Only 15/50 CPIC Evidence tasks yielded valid evaluations. Codex CPIC runs used condensed subsets, not the full benchmarks.

2. **Task overlap in CPIC.** The CPIC Evidence benchmark has 56/106 tasks from a single CACNA1S/RYR1 guideline sharing the same papers, inflating apparent performance in small runs.

3. **LLM-judge variability.** 4 of 5 CPIC tests use an LLM judge (Claude Sonnet). Borderline cases may be scored inconsistently across runs.

4. **Evaluation artifacts.** 22% of Summary QA tasks have empty expected phenotype lists (vacuously true). Paper count ground truth is derived indirectly via PMID-to-PMCID mapping.

5. **Condensed vs. full benchmarks.** Codex CPIC results use condensed subsets; Claude Code uses the full benchmarks. Direct comparison requires running both on identical task sets.

---

## Run Index

All raw results are in `run_results/`. Key job IDs:

| Benchmark | Agent | Job ID | Notes |
|-----------|-------|--------|-------|
| PGx Drug QA | Codex | `2026-02-20__02-47-55` | 100 tasks, best run |
| PGx Drug QA | Claude Code | `2026-02-20__02-40-26` | 30 tasks (credit limit) |
| Summary QA | Codex (GPT-5) | `2026-02-17__23-48-08` | 100 tasks, best run |
| Summary QA | Claude Code | `2026-02-17__23-25-36` | 100 tasks, best run |
| Summary QA | Codex (o4-mini) | `2026-02-18__03-55-41` | 100 tasks, 0.0 score |
| CPIC Evidence | Codex | `2026-02-20__15-48-37` | 70 tasks (condensed) |
| CPIC Evidence | Claude Code | `2026-02-20__00-32-10` | 50 tasks (15 valid) |
| CPIC Evidence | Claude Code | `2026-02-19__22-58-33` | 10 tasks (biased sample) |
| CPIC Zero-Context | Codex | `2026-02-20__18-26-02` | 70 tasks (condensed) |
| CPIC Zero-Context | Claude Code | `2026-02-19__23-51-11` | 50 tasks, best run |
