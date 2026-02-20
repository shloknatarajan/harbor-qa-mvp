# Harbor QA Benchmark Results — All Benchmarks

**Last updated:** 2026-02-20

Results across all four PGx benchmarks. For each benchmark, the best/most complete run per agent is reported. Infra failures (billing errors, Docker failures, timeouts from task size) are noted and excluded from adjusted metrics where applicable.

---

## Overall Summary (Best Runs)

| Benchmark | Tasks | Agent | Model | Evaluated | Mean Reward | Pass | Partial | Fail | Notes |
|---|:-:|---|---|:-:|:-:|:-:|:-:|:-:|---|
| CPIC Evidence | 106 | Claude Code | claude-sonnet-4-6 | 15 | **0.747** | 8 | 7 | 0 | 50-task run, 9 infra fails excluded |
| CPIC Zero Context | 100 | Claude Code | claude-sonnet-4-6 | 50 | **0.64** | 18 | 31 | 1 | 50-task subset |
| PGx Drug QA | 100 | Codex | gpt-5 | 98 | **0.845** | 82 | 1 | 15 | 2 infra timeouts excluded |
| PGx Drug QA | 100 | Claude Code | claude-sonnet-4-6 | 30 | **0.883** | 26 | 1 | 3 | Billing cutoff after 30 |
| Summary QA | 100 | Codex | gpt-5 | 100 | **0.63** | 24 | 68 | 8 | |
| Summary QA | 100 | Claude Code | claude-sonnet-4-6 | 100 | **0.60** | 31 | 44 | 19 | 5 errors |

---

## 1. CPIC Evidence Benchmark

**Directory:** `cpic_evidence_benchmark/` — 106 tasks
**Format:** Open-ended (JSON with recommendation, classification, implication)
**Context:** 5-15 research papers provided
**Evaluation:** 1 deterministic + 4 LLM-judge tests (score >= 4/5 to pass)

### Best run (adjusted)

The most representative run is the 50-task attempt (2026-02-20 00:32). After excluding 9 infra failures (exit code 56 — agent setup) and 26 tasks that produced no results, **15 tasks were actually evaluated**:

| Run | Agent | Attempted | Evaluated | Mean Reward | Pass | Partial | Fail | Errors |
|-----|-------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 2026-02-20 00:32 | Claude Code | 50 | 15 | **0.747** | 8 | 7 | 0 | 9 (setup) |

### Small runs (inflated scores — see caveat below)

| Run | Agent | Trials | Mean Reward | Pass | Partial | Fail | Errors | Duration |
|-----|-------|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 2026-02-19 22:58 | Claude Code | 10 | 0.90 | 7 | 3 | 0 | 0 | 14m 48s |
| 2026-02-19 18:33 | Claude Code | 5 | 0.95 | 4 | 1 | 0 | 0 | 9m 55s |
| 2026-02-20 00:53 | Claude Code | 5 | 0.68 | 2 | 3 | 0 | 0 | 7m 37s |

### Caveat: small runs overstate accuracy

The 0.90 and 0.95 scores from small runs are misleading:

1. **Tiny sample sizes**: 5-10 tasks out of 106 total.
2. **Same-guideline clustering**: The 10-task run had 8 CACNA1S/RYR1 volatile anesthetic tasks from a single guideline sharing the same papers. Getting one right means getting them all right — so 7 "passes" is effectively ~1 independent data point.
3. **Easy subset**: CACNA1S tasks are among the easiest. The 50-task run included harder tasks (DPYD fluorouracil, SLCO1B1 statins) that scored 0.2-0.6.

The **0.747** from the 50-task run (15 evaluated) is the most realistic estimate, and even that may shift with a full 106-task run.

### Notes
- No Codex runs attempted on this benchmark yet.
- Main weakness: implication/completeness scoring on edge cases (partial scores from LLM judge).
- Partial scores cluster at 0.4 (2/5 tests passed — typically classification correct + 1 LLM judge pass).

---

## 2. CPIC Zero Context Benchmark

**Directory:** `cpic_zero_context/` — 100 tasks
**Format:** Open-ended (same JSON as Evidence)
**Context:** None (parametric knowledge only)
**Evaluation:** 1 deterministic + 4 LLM-judge tests

### Best run

| Run | Agent | Trials | Mean Reward | Pass | Partial | Fail | Errors | Duration |
|-----|-------|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 2026-02-19 23:51 | Claude Code | 50 | **0.64** | 18 | 31 | 1 | 0 | 14m 55s |

### Other runs

| Run | Agent | Trials | Mean Reward | Notes |
|-----|-------|:-:|:-:|---|
| 2026-02-19 22:45 | Claude Code | 10 | 0.53 | Only 5/10 trials produced results |
| 2026-02-19 22:41 | Claude Code | 10 | 0.0 | All failed — exit code 100 (agent setup) |
| 2026-02-19 22:39 | Claude Code | 10 | 0.0 | All failed — Docker compose errors |
| 2026-02-19 22:38 | Claude Code | 10 | 0.0 | All failed — Docker compose errors |

### Notes
- No Codex runs attempted on this benchmark yet.
- Performance drops significantly from Evidence (0.90) to Zero Context (0.64) — the provided papers matter.
- Strongest areas: G6PD (rasburicase, tafenoquine, primaquine), MT-RNR1 (aminoglycosides), HLA-B abacavir.
- Weakest areas: CYP2C19 (lansoprazole, piroxicam), CYP2D6 atomoxetine, NAT2 hydralazine.
- Dominant error: recommendation classification mismatch (e.g., "Strong" vs "Moderate").

---

## 3. PGx Drug QA Benchmark

**Directory:** `pgx_drug_qa/` — 100 tasks
**Format:** Multiple-choice (a/b/c/d)
**Context:** 1 research paper provided
**Evaluation:** Deterministic exact match per question

### Best runs

| Run | Agent | Model | Evaluated | Mean Reward | Mean Reward (adj) | Pass | Partial | Fail | Duration |
|-----|-------|-------|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 2026-02-20 02:47 | Codex | gpt-5 | 100 | 0.828 | **0.845** | 82 | 1 | 15 | 244m |
| 2026-02-20 02:40 | Claude Code | claude-sonnet-4-6 | 30* | **0.883** | **0.883** | 26 | 1 | 3 | — |

\* Claude Code run cut short after 30 tasks due to Anthropic API credit exhaustion.

### Head-to-head (30 overlapping tasks)

| Agent | Mean Reward | Pass | Fail | Partial |
|-------|:-:|:-:|:-:|:-:|
| Codex (gpt-5) | **0.917** | 27 | 2 | 1 |
| Claude Code | **0.883** | 26 | 3 | 1 |

### Disagreements

| Task | Claude Code | Codex | Notes |
|------|:-:|:-:|---|
| `pmc10318569` | 0.0 | 1.0 | Claude fixated on morphine-3-glucuronide |
| `pmc10520058` | 1.0 | 0.0 | Claude got edoxaban right; Codex failed all 10 |
| `pmc10537526` | 1.0 | 0.0 | Claude got tramadol right; Codex missed |
| `pmc10374328` | 0.5 | 0.0 | Claude got 1/2; Codex got 0/2 |
| `pmc10565537` | 1.0 | 0.83 | Claude perfect; Codex missed 1/6 |

Both failed: `pmc10159199` (Platinum compounds), `pmc10541540` (ethambutol/isoniazid multi-drug).

### Infra failures
- Codex: 2 timeouts — `pmc10154044` (98 questions, 600s limit) and `pmc10399933` (20 questions, 600s limit)
- Claude Code: 70 tasks failed due to billing credit exhaustion

### Failure patterns
- Multi-drug combinations are hardest
- Drug class vs. specific drug confusion
- Single-drug fixation (Claude Code)

See [pgx_drug_qa_results.md](pgx_drug_qa_results.md) for full per-task breakdown.

---

## 4. Summary QA Benchmark

**Directory:** `summary_qa/` — 100 tasks
**Format:** Extraction (drugs, phenotypes, paper count)
**Context:** 16 papers + term banks
**Evaluation:** 3 deterministic tests (drug recall, phenotype recall, paper count exact match)

### Best runs

| Run | Agent | Model | Trials | Errors | Mean Reward | Pass | Partial | Fail | Duration |
|-----|-------|-------|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 2026-02-17 23:48 | Codex | gpt-5 | 100 | 0 | **0.63** | 24 | 68 | 8 | 247m |
| 2026-02-17 23:25 | Claude Code | claude-sonnet-4-6 | 100 | 5 | **0.60** | 31 | 44 | 19 | 242m |

### Other runs

| Run | Agent | Model | Trials | Mean Reward | Notes |
|-----|-------|-------|:-:|:-:|---|
| 2026-02-18 03:55 | Codex | o4-mini | 100 | 0.0 | Complete failure — o4-mini uses web search instead of shell |
| 2026-02-18 12:48 | Codex | (no model) | 5 | 0.0 | Agent produced nothing (0 tokens) |

### Notes
- Codex (gpt-5) and Claude Code are very close: 0.63 vs 0.60.
- Codex has fewer outright failures (8 vs 19) but more partial scores (68 vs 44).
- Claude Code has more full passes (31 vs 24) but is less consistent.
- Codex + o4-mini is completely non-functional — it uses web search instead of reading local files and never writes `answers.json`.

See [summary_qa_results.md](summary_qa_results.md) for detailed analysis.

---

## Cross-Benchmark Observations

1. **Context matters**: Claude Code scores 0.747 on CPIC Evidence (with papers) vs 0.64 on Zero Context (without) — papers help but the gap is smaller than the inflated small-run numbers suggested.

2. **MCQ is easiest**: PGx Drug QA (multiple-choice) has the highest scores for both agents (0.83-0.88), while extraction tasks (Summary QA) and open-ended generation (CPIC) are harder.

3. **Agent comparison** (where both ran):
   - **PGx Drug QA**: Codex 0.845 vs Claude Code 0.883 (30-task sample) — close, slight Claude edge
   - **Summary QA**: Codex 0.63 vs Claude Code 0.60 — close, slight Codex edge
   - No Codex runs on CPIC benchmarks yet

4. **Codex + o4-mini does not work** for these benchmarks — it prefers web search over reading local files.

5. **Infra reliability** is a recurring issue: Docker compose failures, agent setup errors (exit codes 56, 100), API credit exhaustion, and timeouts on large tasks.

## Incomplete / TODO

- [ ] Full 100-task Claude Code run on PGx Drug QA (needs API credits)
- [ ] Codex runs on CPIC Evidence and CPIC Zero Context
- [ ] Full 100-task runs on CPIC Evidence and CPIC Zero Context (currently 10 and 50 max)
- [ ] Retry CPIC Evidence 50-task run without agent setup failures
