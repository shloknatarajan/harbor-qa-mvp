# Summary QA Results

Last updated: 2026-02-20

## Task Design

**100 tasks** derived from PharmGKB summary annotations. Each task provides:
- A variant, gene, and phenotype category
- 16 research papers (relevant + distractors) at `/app/papers/`
- Two term banks (`drugs.txt`, `phenotypes.txt`) constraining the answer vocabulary

The agent must produce a JSON with:
1. **drugs** — all drugs associated with the variant (from the term bank)
2. **phenotypes** — all phenotypes associated with the variant (from the term bank)
3. **relevant_paper_count** — exact count of relevant papers

### Evaluation

Three deterministic pytest tests. Reward = fraction passed (0.0, 0.33, 0.67, or 1.0).

| Test | Method | Tolerance |
|------|--------|-----------|
| `test_drugs_recall` | All expected drugs must appear in agent's list | Recall-only; extra drugs OK |
| `test_phenotypes_recall` | All expected phenotypes must appear | Recall-only; extra phenotypes OK |
| `test_relevant_paper_count` | Exact integer match | None |

---

## All Runs

### Full 100-task runs

| Date | Agent | Model | Mean Reward | Pass | Partial | Fail | Errors | Duration | Job |
|------|-------|-------|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 2026-02-17 23:48 | Codex | GPT-5 | **0.63** | 24 | 68 | 8 | 0 | 247m | `2026-02-17__23-48-08` |
| 2026-02-17 23:25 | Claude Code | Sonnet 4.6 | **0.60** | 31 | 44 | 19 | 5 | 242m | `2026-02-17__23-25-36` |
| 2026-02-18 03:55 | Codex | o4-mini | **0.00** | 0 | 0 | 100 | 0 | 78m | `2026-02-18__03-55-41` |

### Small/exploratory runs

| Date | Agent | Model | Trials | Mean Reward | Notes | Job |
|------|-------|-------|:-:|:-:|---|---|
| 2026-02-17 21:20 | Claude Code | Sonnet 4.6 | 1 | 1.00 | Single task, perfect score | `2026-02-17__21-20-46` |
| 2026-02-17 21:35 | Claude Code | Sonnet 4.6 | 5 | 0.53 | 0 pass, 5 partial | `2026-02-17__21-35-09` |
| 2026-02-17 23:14 | Claude Code | Sonnet 4.6 | 1 | 0.67 | Count mismatch | `2026-02-17__23-14-47` |
| 2026-02-17 23:37 | Codex | GPT-5 | 1 | 0.67 | Count mismatch | `2026-02-17__23-37-25` |
| 2026-02-17 23:42 | Codex | o4-mini | 1 | 0.00 | Web search failure | `2026-02-17__23-42-45` |
| 2026-02-18 11:53 | Codex | GPT-5 | 5 | 0.00 | Docker compose failures | `2026-02-18__11-53-25` |
| 2026-02-18 12:48 | Codex | GPT-5 | 5 | 0.00 | 0 tokens consumed; setup issue | `2026-02-18__12-48-51` |

---

## Head-to-Head: Codex (GPT-5) vs. Claude Code

Both agents completed the full 100-task dataset in ~4 hours with single-task concurrency.

### Outcome distribution

| | Codex (GPT-5) | Claude Code |
|---|:-:|:-:|
| **Mean Reward** | **0.63** | **0.60** |
| Pass (1.0) | 24 | **31** |
| Partial (0.33–0.67) | **68** | 44 |
| Fail (0.0) | **8** | 19 |
| Errors | 0 | 5 |

Claude Code achieves more perfect scores (31 vs. 24) but fails completely far more often (19 vs. 8). Codex is more consistent — 68% of tasks earn partial credit vs. 44% for Claude.

### Per-subtask failure rates

| Subtask | Failure Rate | Notes |
|---------|:-:|---|
| Drug recall | < 10% | Reliable for both agents |
| Phenotype recall | ~40–50% | String-matching mismatches dominate |
| Paper count | ~50–60% | Off-by-1-to-4 errors both directions |

### Failure mode comparison

| | Codex (GPT-5) | Claude Code |
|---|---|---|
| Zero-reward behavior | Writes `answers.json` with empty fields (`{"drugs": [], ...}`) | Never creates `answers.json` at all |
| Interpretation | Agent ran but found nothing | Agent timed out or didn't complete |
| Token usage on failures | Low (112K–305K) — barely read papers | N/A (setup errors) |

---

## Error Analysis

### Phenotype string-matching (primary failure mode)

The dominant failure across both agents. The agent identifies the correct medical concept but at a different level of granularity than the gold standard:

| Agent Output | Expected Term | Issue |
|-------------|---------------|-------|
| "depression", "major depressive disorder" | "mental disorders" | Too specific |
| "drug hypersensitivity syndrome" | "drug hypersensitivity" | Extra qualifier |
| "cns toxicity", "neuropsychiatric symptoms" | "hiv infectious disease" | Symptoms vs. disease |

This is partially an evaluation artifact: 22 of 100 tasks have empty expected phenotype lists, making the phenotype test vacuously true.

### Paper count errors

Paper count mismatches are typically small (off by 1–4) and go both directions. Examples from the Codex run:

| Task | Agent Count | Expected | Direction |
|------|:-:|:-:|---|
| TPMT alleles | 7 | 11 | Under-count |
| CYP2D6 (5 alleles) | 2 | 1 | Over-count |

The ground truth is derived indirectly (annotation PMIDs → PMCID mapping → papers on disk), so some disagreement may reflect gold-standard ambiguity.

### Resource consumption

Token usage varies dramatically:

| Metric | Min | Median | Max |
|--------|:-:|:-:|:-:|
| Input tokens/task | 112K | ~1.1M | 3.6M |
| Output tokens/task | 42 | ~10K | 41K |
| Duration/task | 1m 27s | ~5m | 10m |

The largest single-task input was **3.6M tokens** (CYP2C9 warfarin variants, Codex) — the agent read most or all 16 papers. The smallest was **112K tokens** — the agent barely read any papers before giving up.

---

## Why o4-mini Scores 0.0

Codex CLI unconditionally registers `web_search_preview` as a tool with the OpenAI API. o4-mini preferentially invokes web search over reading local files — it outputs suggested code blocks but never executes shell commands, so `/app/answers.json` is never written.

| Model | Compatible | Behavior |
|-------|:-:|---|
| GPT-5 | Yes | Correctly prioritizes shell execution over web search |
| o4-mini | No | Prefers web search, never writes output file |
| o3-mini | No | Doesn't support `web_search_preview`, causes API error |

This is a Codex CLI limitation — the `web_search_preview` tool cannot be disabled via flags.

---

## Early Run Analysis (5-trial Claude run, 2026-02-17)

The 5-trial run (`2026-02-17__21-35-09`) provided detailed per-trial breakdowns:

| Task | Reward | Drugs | Phenotypes | Count | Tokens In |
|------|:-:|:-:|:-:|:-:|:-:|
| NAT2\*4/5/6/7/16 | 0.67 | Pass | Pass (vacuous) | 5 vs 3 | 1.6M |
| CYP2D6 (9 alleles) | 0.67 | Pass | Fail: "depression" vs "depressive disorder" | 2 = 2 | 213K |
| CYP2D6 (5 alleles) | 0.33 | Pass | Fail: "depression" vs "major depressive disorder" | 2 vs 1 | 2.6M |
| CYP2B6 (5 alleles) | 0.33 | Pass | Fail: missed "hiv infectious disease" | 5 vs 6 | 678K |
| HLA-B\*58:01 | 0.67 | Pass | Fail: "drug hypersensitivity syndrome" vs "drug hypersensitivity" | 9 = 9 | 119K |

Drug recall passed 5/5. Phenotype recall failed 4/5 (all near-misses). Paper count wrong 3/5.

---

## Known Issues & Recommendations

1. **Term bank deployment gap.** The `generate_questions.py` script was updated to include term banks, but the on-disk tasks were generated from an older version without them. Re-running `python summary_qa/generate_questions.py` would regenerate tasks with term banks, likely improving phenotype matching.

2. **Phenotype matching fragility.** Even with term banks, consider fuzzy matching or normalization (e.g., treating "drug hypersensitivity" and "drug hypersensitivity syndrome" as equivalent).

3. **Paper count ground truth.** The expected count derives from an indirect PMID → PMCID mapping chain, not direct relevance annotation. Some mismatches may be ground-truth noise.

4. **Vacuous phenotype tests.** 22/100 tasks have empty expected phenotype lists. These inflate accuracy since the phenotype test passes for free. Consider excluding or flagging them.

5. **Claude Code file-write failures.** 19 of Claude's 100 failures were due to never creating `answers.json`. Investigating whether these are timeouts, instruction misunderstandings, or execution errors could recover significant score.
