# Summary QA — Longest Runs Snapshot

This document summarizes the longest `summary_qa` runs currently recorded in this repo, including detailed descriptions of what failures and successes look like with concrete examples from the runs.

## Scoring Overview

Each task is verified with 3 pytest tests. The reward is the fraction that pass (0/3 = 0.0, 1/3 = 0.33, 2/3 = 0.67, 3/3 = 1.0):

1. **`test_drugs_recall`** — are all expected drugs present in the agent's answer? (recall-only; extra drugs are OK)
2. **`test_phenotypes_recall`** — are all expected phenotypes present? (recall-only; extra phenotypes are OK)
3. **`test_relevant_paper_count`** — does the agent's count exactly match the expected number of relevant papers?

## Longest overall run (full 100-task dataset)

- **Date**: 2026-02-17 23:48
- **Agent**: codex
- **Model**: gpt-5
- **Duration**: 247m
- **Mean Reward**: 0.63
- **Outcomes (100 tasks)**
  - Pass: 24
  - Partial: 68
  - Fail: 8
  - Errors: 0

### What passes look like (codex)

A full pass means drugs, phenotypes, and paper count all match. Example:

> **Task**: `pmc1401654_nat2_4_nat2_5_nat2_6` (NAT2 alleles) — reward=1.0, 6m 43s, 1.4M input tokens
>
> ```
> PASSED test_drugs_recall
> PASSED test_phenotypes_recall
> PASSED test_relevant_paper_count
> ============================== 3 passed in 0.03s ===============================
> ```

Other codex passes include `pmc1873971_cyp2c19` (CYP2C19 alleles, 5m 39s), `pmc2360725_rs121434568` (3m 45s), and `pmc4502741_rs121908755` (2m 16s). Passes tend to be tasks with well-defined drug/phenotype sets and lower paper counts where the agent can make correct relevance calls.

### What failures look like (codex)

Codex failures (reward=0.0) have a distinctive pattern: the agent writes `answers.json` but with **all-empty fields**. This means the agent ran but found nothing, likely because it couldn't locate or parse the papers. Example:

> **Task**: `pmc11401437_rs186089140_summary` — reward=0.0, 1m 27s, 167K input tokens
>
> Agent answer: `{'drugs': [], 'phenotypes': [], 'relevant_paper_count': 0}`
> ```
> FAILED test_drugs_recall - Missing drugs: {'elexacaftor / tezacaftor / ivacaftor', 'ivacaftor'}. Got: []
> FAILED test_phenotypes_recall - Missing phenotypes: {'cystic fibrosis'}. Got: []
> FAILED test_relevant_paper_count - Expected 1 relevant papers, got 0
> ============================== 3 failed in 0.04s ===============================
> ```

The same pattern appears in `pmc11672886_rs80224560` (reward=0.0, 2m 6s) — the agent returned empty lists and missed the expected drugs (ivacaftor, elexacaftor/tezacaftor/ivacaftor), phenotype (cystic fibrosis), and paper count (1). These failed tasks tend to have low input token counts (112K–305K), suggesting the agent barely read any papers before giving up.

### What partial results look like (codex)

Partial results are the most common outcome (68/100). They split into two tiers:

**Partial at 0.67** — typically drugs and phenotypes pass, but paper count is wrong:

> **Task**: `pmc1856436_tpmt_1_tpmt_2_tpmt_3a` (TPMT alleles) — reward=0.67, 4m 17s
>
> Agent answer: `{'drugs': ['azathioprine', 'mercaptopurine', 'thioguanine'], 'phenotypes': ['febrile neutropenia', 'leukopenia', 'myelosuppression', 'neutropenia', 'thrombocytopenia'], 'relevant_paper_count': 7}`
> ```
> PASSED test_drugs_recall
> PASSED test_phenotypes_recall
> FAILED test_relevant_paper_count - Expected 11 relevant papers, got 7
> ========================= 1 failed, 2 passed in 0.04s =========================
> ```
>
> The agent got all drugs and phenotypes right but under-counted relevant papers (7 vs 11).

**Partial at 0.33** — typically only drug recall passes, while phenotypes and paper count both fail:

> **Task**: `pmc1365132_cyp2d6_1_cyp2d6_3_cyp2d6_4_cyp2d6_5` (CYP2D6 alleles) — reward=0.33, 4m 50s
>
> Agent answer: `{'drugs': ['fluoxetine', 'imipramine', 'desipramine', 'sparteine'], 'phenotypes': ['depression', 'major depressive disorder', 'atrial fibrillation', 'bradycardia', 'death', 'inflammation'], 'relevant_paper_count': 2}`
> ```
> PASSED test_drugs_recall
> FAILED test_phenotypes_recall - Missing phenotypes: {'mental disorders'}. Got: ['atrial fibrillation', 'bradycardia', 'death', 'depression', 'inflammation', 'major depressive disorder']
> FAILED test_relevant_paper_count - Expected 1 relevant papers, got 2
> ========================= 2 failed, 1 passed in 0.04s =========================
> ```
>
> The agent listed many phenotypes (depression, major depressive disorder, etc.) but missed the exact expected term "mental disorders". It also over-counted relevant papers (2 vs 1).

---

## Longest Claude run (full 100-task dataset)

- **Date**: 2026-02-17 23:25
- **Agent**: claude-code
- **Model**: (default)
- **Duration**: 242m
- **Mean Reward**: 0.60
- **Outcomes (100 tasks)**
  - Pass: 31
  - Partial: 44
  - Fail: 19
  - Errors: 5

### What passes look like (claude)

Claude passes look identical to codex passes — all three tests green:

> **Task**: `pmc4043918_rs9923231_summary` — reward=1.0
>
> ```
> PASSED test_drugs_recall
> PASSED test_phenotypes_recall
> PASSED test_relevant_paper_count
> ============================== 3 passed in 0.03s ===============================
> ```

Claude achieves **more full passes than codex** (31 vs 24), suggesting it is better at nailing all three checks simultaneously when it succeeds.

### What failures look like (claude)

Claude failures are fundamentally different from codex failures. Instead of producing an empty answer, Claude **fails to create `answers.json` at all**. All 19 zero-reward Claude tasks show this identical error pattern:

> **Task**: `pmc3657889_rs9923231_summary` — reward=0.0
>
> ```
> ERROR at setup of test_drugs_recall - AssertionError: answers.json not found
> ERROR at setup of test_phenotypes_recall - AssertionError: answers.json not found
> ERROR at setup of test_relevant_paper_count - AssertionError: answers.json not found
> ============================== 3 errors in 0.04s ===============================
> ```

This is a **setup error**, not a test failure — the verification harness can't even run the tests because the output file doesn't exist. This suggests Claude either hit a timeout, errored during execution, or didn't understand the instruction to write to `/app/answers.json`. The 5 additional errors in the run are the same pattern (answers.json not found).

**Key difference**: Codex writes empty answers (structured failure); Claude doesn't write the file at all (infrastructure failure).

### What partial results look like (claude)

Claude partials show the same patterns as codex — string mismatches on phenotypes and paper count disagreements:

**Partial at 0.67** — drugs and phenotypes pass, paper count off by 1:

> **Task**: `pmc6777606_cyp2c9_1_cyp2c9_2_cyp2c9_3` — reward=0.67
>
> Agent answer: `{'drugs': ['warfarin', 'acenocoumarol', 'phenprocoumon'], 'phenotypes': ['hemorrhage', 'over-anticoagulation', ...], 'relevant_paper_count': 12}`
> ```
> PASSED test_drugs_recall
> PASSED test_phenotypes_recall
> FAILED test_relevant_paper_count - Expected 11 relevant papers, got 12
> ========================= 1 failed, 2 passed in 0.04s =========================
> ```

**Partial at 0.33** — the recurring "mental disorders" phenotype miss:

> **Task**: `pmc3571021_cyp2c19_1_cyp2c19_2_c` — reward=0.33
>
> Agent answer: `{'drugs': ['clozapine', 'docetaxel', 'escitalopram', 'thalidomide'], 'phenotypes': ['depression', 'major depressive disorder', 'prostatic neoplasms'], 'relevant_paper_count': 3}`
> ```
> PASSED test_drugs_recall
> FAILED test_phenotypes_recall - Missing phenotypes: {'mental disorders'}. Got: ['depression', 'major depressive disorder', 'prostatic neoplasms']
> FAILED test_relevant_paper_count - Expected 1 relevant papers, got 3
> ========================= 2 failed, 1 passed in 0.04s =========================
> ```

---

## Cross-run failure patterns

| Pattern | Codex (gpt-5) | Claude |
|---------|---------------|--------|
| Total 0.0 failures | 8 | 19 |
| Failure mode | Empty answer (writes `answers.json` with `[]` fields) | Missing file (never creates `answers.json`) |
| Most common partial failure | Paper count mismatch (off by 1-4) | Paper count mismatch (off by 1-4) |
| Recurring phenotype miss | "mental disorders" expected, agent returns specific conditions | Same |
| Drug recall | Very reliable (rarely fails alone) | Very reliable (rarely fails alone) |

### Why phenotypes fail: the string-matching problem

The most common phenotype failure across both runs is the "mental disorders" miss. The agent returns semantically correct but string-mismatched terms:

| Agent returned | Expected |
|---------------|----------|
| `depression`, `major depressive disorder` | `mental disorders` |
| `drug hypersensitivity syndrome` | `drug hypersensitivity` |

The agents understand the medical content but use different granularity than the gold standard. This is a known issue — the on-disk tasks lack term banks that would constrain the vocabulary (see `docs/summary_qa_run_analysis.md` §1).

### Why paper counts fail

Paper count errors are small (typically off by 1-4) and go both directions — agents both over-count and under-count. The ground truth is derived indirectly (annotation PMIDs → PMCID mapping → papers on disk), so some disagreement may reflect gold-standard ambiguity.

## Supporting context

Source: `docs/summary_qa_run_analysis.md`

- Across a smaller claude-code run on 2026-02-17 (5 trials), token usage varied widely by task.
- The largest documented single-task input was **2,618,486 input tokens** (CYP2D6, 5 alleles).

## Pointers

- `docs/summary_qa_results.md` — table of best large/small runs
- `docs/summary_qa_run_analysis.md` — deeper breakdown of the 2026-02-17 claude runs, including token usage examples
- `summary_qa/summary_qa.md` — dataset/task design and scoring
- `run_results/2026-02-17__23-48-08_summary_qa.txt` — full codex run output (100 tasks)
- `jobs/2026-02-17__23-48-08/` — per-task codex job directories with verify outputs
- `jobs/2026-02-17__23-25-36/` — per-task claude job directories with verify outputs
