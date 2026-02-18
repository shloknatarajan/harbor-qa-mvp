# Summary QA Run Analysis — 2026-02-17

## Run Overview

Two summary_qa runs were executed on 2026-02-17 using the `claude-code` agent:

| Job | Trials | Errors | Mean Reward | Duration |
|-----|--------|--------|-------------|----------|
| `21-20-46` | 1 (of 5 requested) | 0 | **1.0** | ~6 min |
| `21-35-09` | 5 | 0 | **0.533** | 20m 28s |

The `21-35-09` run is the most recent and most representative (5 trials). All analysis below focuses on it.

## Trial-by-Trial Breakdown

| Task | Reward | Drugs | Phenotypes | Count | Notes |
|------|--------|-------|------------|-------|-------|
| NAT2\*4/5/6/7/16 | 0.67 | 1/1 | 0/0 (vacuous) | 5 vs 3 | Count off by +2; extra drugs listed |
| CYP2D6 (9 alleles) | 0.67 | 1/1 | 0/1 | 2 = 2 | "depression" vs expected "depressive disorder" |
| CYP2D6 (5 alleles) | 0.33 | 1/1 | 0/1 | 2 vs 1 | "depression" vs "major depressive disorder"; count off |
| CYP2B6 (5 alleles) | 0.33 | 1/1 | 0/1 | 5 vs 6 | "hiv infectious disease" not found; count off |
| HLA-B\*58:01 | 0.67 | 1/1 | 4/5 | 9 = 9 | Only missed "drug hypersensitivity" (returned "drug hypersensitivity syndrome" instead) |

**Pattern**: Drug recall passes consistently (5/5), but phenotype matching and paper counts are unreliable.

## Key Findings

### 1. Code vs. On-Disk Task Divergence (Term Banks)

`generate_questions.py` has been updated to include term banks:
- The instruction template now tells agents to "Select all drugs/phenotypes from the drug/phenotype term bank"
- The Dockerfile template now includes `COPY term_banks/ /app/term_banks/`
- The script generates `term_banks/drugs.txt` and `term_banks/phenotypes.txt` per task

**However, the tasks on disk were generated from an older version of the script.** All 100 task directories:
- Have instructions that say "List every distinct drug and phenotype you find" (open-ended)
- Have Dockerfiles that only `COPY papers/` (no term banks)
- Have no `environment/term_banks/` directory

**Impact**: The agent is being asked to freely identify drugs/phenotypes from papers, then evaluated by exact string recall against a specific expected set. Without term banks constraining the vocabulary, the agent returns semantically correct but string-mismatched answers (e.g., "depression" vs "depressive disorder").

**Fix**: Re-run `python summary_qa/generate_questions.py` to regenerate all 100 task directories with the current script, which includes term bank files and updated instructions.

### 2. Phenotype String Matching is the Primary Failure Mode

In 4 out of 5 trials, the phenotype test failed. The mismatches are near-misses:

| Agent Answer | Expected Answer |
|-------------|-----------------|
| `depression` | `depressive disorder` |
| `depression` | `major depressive disorder` |
| `drug hypersensitivity syndrome` | `drug hypersensitivity` |
| (various CNS symptoms) | `hiv infectious disease` |

The first three are clearly the same concept with slight naming differences. The term bank approach should fix most of these by constraining the answer vocabulary. The fourth case (HIV) is a different issue — the agent listed symptoms rather than the underlying disease category.

### 3. Paper Count Is Frequently Wrong

3 out of 5 trials got the paper count wrong. Errors were small (off by 1-2), suggesting the agent is doing genuine analysis but making borderline relevance calls differently than the gold standard.

Note: "relevant paper count" equals `len(record["pmcids"])` — the number of PMCIDs mapped from the annotation's evidence PMIDs. This is an indirect measure (annotation evidence -> PMIDs -> PMCID mapping -> papers on disk) rather than a direct "is this paper about this variant" assessment.

### 4. Drug Recall is Reliable

All 5 trials passed the drug recall test. However, the agent consistently returns many extra drugs beyond the expected set (e.g., 19 extra drugs in one CYP2D6 trial). This is acceptable under recall-only scoring, but note:
- With term banks, the agent would be constrained to known drug names
- The current open-ended instruction encourages over-listing

### 5. Token Usage Varies Wildly

| Task | Input Tokens | Output Tokens |
|------|-------------|---------------|
| NAT2 | 1,593,804 | 235 |
| CYP2D6 (9 alleles) | 212,621 | 42 |
| CYP2D6 (5 alleles) | 2,618,486 | 185 |
| CYP2B6 | 677,935 | 214 |
| HLA-B | 118,526 | 43 |

The CYP2D6 5-allele task consumed 2.6M input tokens — likely because it read many/all papers in full. The output is always tiny (42-235 tokens), which is expected since the final answer is a small JSON.

### 6. 22% of Tasks Have Vacuously True Phenotype Tests

22 out of 100 tasks have `EXPECTED_PHENOTYPES = []`. The phenotype recall test always passes for these (nothing to miss). This inflates the effective drug+phenotype accuracy since 1 of 3 tests is free. Consider whether empty-phenotype tasks should be included or scored differently.

### 7. Task Infrastructure is Sound

No errors in either run. The Docker environment, pytest-based verification, and reward calculation all work correctly. The `show_results.py` reporting accurately extracts and displays agent answers vs expected values.

## Recommendations

1. **Regenerate tasks** — Run `python summary_qa/generate_questions.py` to get term banks and updated instructions into the task directories. This is the single most impactful fix.
2. **Re-run after regeneration** — The 0.533 mean reward should improve significantly once the agent can select from constrained term banks rather than free-text.
3. **Consider fuzzy phenotype matching** — Even with term banks, exact string matching may be fragile. Consider normalizing terms (e.g., treating "drug hypersensitivity" and "drug hypersensitivity syndrome" as equivalent) or using a similarity threshold.
4. **Review paper count ground truth** — The expected count is derived from PMID->PMCID mapping, not from direct paper-variant relevance assessment. Some mismatch may reflect ground truth ambiguity rather than agent error.
5. **Scale up trials** — 5 trials on a 100-task dataset gives limited statistical power. Run with `-l 20` or more for a better signal.
