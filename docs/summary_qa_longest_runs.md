# Summary QA — Longest Runs Snapshot

This document summarizes the longest `summary_qa` runs currently recorded in this repo.

## Longest overall run (full 100-task dataset)

Source: `docs/summary_qa_results.md` ("Large Runs (full 100-task dataset)")

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

Notes:
- Reward definition: fraction of three checks passed (drugs recall, phenotypes recall, relevant paper count exact match). See `summary_qa/summary_qa.md`.
- This is the best-performing large run currently recorded (highest mean reward among the large runs) and also the longest duration listed.

## Longest Claude run (full 100-task dataset)

Source: `docs/summary_qa_results.md` ("Large Runs (full 100-task dataset)")

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

Notes:
- Claude has **more full passes** than codex+gpt-5 in the recorded large runs (31 vs 24), but also more failures (19 vs 8).

## Supporting context

Source: `docs/summary_qa_run_analysis.md`

- Across a smaller claude-code run on 2026-02-17 (5 trials), token usage varied widely by task.
- The largest documented single-task input was **2,618,486 input tokens** (CYP2D6, 5 alleles).

## Pointers

- `docs/summary_qa_results.md` — table of best large/small runs
- `docs/summary_qa_run_analysis.md` — deeper breakdown of the 2026-02-17 claude runs, including token usage examples
- `summary_qa/summary_qa.md` — dataset/task design and scoring
