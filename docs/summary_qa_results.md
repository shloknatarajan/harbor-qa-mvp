# Summary QA Results

Best results from codex and claude-code on the summary_qa dataset.

## Large Runs (full 100-task dataset)

| Date | Agent | Model | Mean Reward | Pass | Partial | Fail | Errors | Duration |
|------|-------|-------|-------------|------|---------|------|--------|----------|
| 2026-02-17 23:48 | codex | gpt-5 | **0.63** | 24 | 68 | 8 | 0 | 247m |
| 2026-02-17 23:25 | claude-code | (default) | **0.60** | 31 | 44 | 19 | 5 | 242m |
| 2026-02-18 03:55 | codex | o4-mini | 0.0 | 0 | 0 | 100 | 0 | 78m |

## Small Runs

| Date | Agent | Model | Mean Reward | Trials | Notes |
|------|-------|-------|-------------|--------|-------|
| 2026-02-17 21:20 | claude-code | (default) | 1.0 | 1 | Perfect score on single trial |
| 2026-02-17 21:35 | claude-code | (default) | 0.53 | 5 | 0 pass, 5 partial |
| 2026-02-17 23:14 | claude-code | (default) | 0.67 | 1 | 1 partial (count mismatch) |
| 2026-02-17 23:37 | codex | gpt-5 | 0.67 | 1 | 1 partial |
| 2026-02-17 23:42 | codex | o4-mini | 0.0 | 1 | Failed |

## Key Findings

**codex + gpt-5** is the best performer at 0.63 mean reward across 100 tasks. It actually reads papers via shell commands (500K-3.5M input tokens per task, 2-9 min agent time).

**claude-code** (default Claude model) is close behind at 0.60, with more full passes (31 vs 24) but also more failures (19 vs 8).

**codex + o4-mini fails completely** (0.0 across 100 tasks). The Codex CLI automatically enables `web_search_preview` as a tool, and o4-mini prefers web search over reading local files. It outputs suggested code blocks but never executes shell commands, so `/app/answers.json` is never written.

**codex + o3-mini also fails** because o3-mini doesn't support `web_search_preview`, and the Codex CLI unconditionally sends it, causing an API error.

## Known Issues

- **Codex web_search_preview**: The Codex CLI always registers `web_search_preview` with the OpenAI API. This cannot be disabled via flags. Models that support it (o4-mini, gpt-4o) tend to use it instead of reading local files. Models that don't support it (o3-mini) error out entirely. Only gpt-5 correctly prioritizes shell execution over web search.
- **Answer extraction**: The `show_results.py` script reports "(no agent answers extracted)" for codex runs even when they succeed, because codex writes answers via shell commands rather than the Write tool. The verifier still works correctly since it reads `/app/answers.json` directly.
