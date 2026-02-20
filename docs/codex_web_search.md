# Codex CLI: `web_search_preview` Tool Compatibility

The Codex CLI (`@openai/codex`) automatically enables the `web_search_preview` response tool when calling the OpenAI API. This is built into the CLI and **cannot be disabled** via flags or configuration.

Models that do **not** support `web_search_preview` will fail immediately with:

```
Tool 'web_search_preview' is not supported with <model>.
```

## Supported Models

These models support `web_search_preview` and work with codex:

| Model | Status |
|-------|--------|
| `gpt-4o` | Supported |
| `gpt-4o-mini` | Supported |
| `gpt-4.1` | Supported |
| `gpt-4.1-mini` | Supported |
| `gpt-4.1-nano` | Supported |
| `o3` | Supported |
| `o4-mini` | Supported |
| `gpt-5` | Supported (default codex model) |

## Unsupported Models

These models will **fail** when used with codex:

| Model | Status |
|-------|--------|
| `o3-mini` | Not supported |
| `o1` | Not supported |
| `o1-mini` | Not supported |
| `gpt-4-turbo` | Not supported |
| `gpt-4` | Not supported |

## Workaround

Since the CLI doesn't expose a flag to disable `web_search_preview`, the only options are:

1. Use a supported model (see table above)
2. Add instructions to the task prompt discouraging web search (already done in `generate_questions.py`)
3. Use a different agent (e.g., `claude-code`) that doesn't auto-enable web search
