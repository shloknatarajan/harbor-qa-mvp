# Harbor QA MVP Setup

## Overview

We set up [Harbor](https://harborframework.com/) to run CLI agents against local QA tasks in sandboxed Docker containers. Harbor handles agent installation, execution, and verification automatically.

## Installation

```bash
uv tool install harbor
uv sync
```

Requires Docker Desktop running locally.

## Project Structure

```
harbor-qa-mvp/
├── .env                     # ANTHROPIC_API_KEY (not committed)
├── main.py                  # Entry point: loads .env, runs harbor CLI
├── pyproject.toml           # Dependencies (python-dotenv, ruff)
├── mvp_dataset/             # Local dataset of Harbor tasks
│   ├── question-1/
│   │   ├── instruction.md          # Question + instructions for the agent
│   │   ├── task.toml               # Task config (timeouts, resources)
│   │   ├── environment/
│   │   │   └── Dockerfile          # Sandbox container (ubuntu:24.04)
│   │   └── tests/
│   │       ├── test.sh             # Installs deps, runs pytest, writes reward
│   │       └── test_outputs.py     # Pytest assertions on agent output
│   └── question-2/
│       └── ... (same structure)
├── data/                    # PGxQA dataset (papers + MCQs)
└── jobs/                    # Harbor output (auto-created per run)
```

## How It Works

1. `main.py` loads environment variables from `.env` (notably `ANTHROPIC_API_KEY`)
2. It shells out to `harbor run` with configurable CLI args
3. Harbor spins up a Docker container per task, installs the agent, sends the instruction, and runs verification tests
4. Results are written to `jobs/<timestamp>/result.json`

## Harbor Task Format

Each task directory contains:

| File | Purpose |
|------|---------|
| `instruction.md` | Markdown prompt sent to the agent |
| `task.toml` | Config: timeouts, resource limits, MCP servers |
| `environment/Dockerfile` | Container definition for the sandbox |
| `tests/test.sh` | Runs pytest and writes `reward.txt` (0 or 1) |
| `tests/test_outputs.py` | Pytest assertions that verify the agent's output |

The agent is instructed to write its answer to `/app/answer.txt`, and the test script checks it.

## Usage

```bash
# Run all tasks with defaults (claude-code agent, 1 concurrent)
uv run python main.py

# Pass custom harbor args
uv run python main.py -p mvp_dataset -a claude-code -n 2

# Run a single task
uv run python main.py -p mvp_dataset/question-1 -a claude-code -n 1

# Use a different model
uv run python main.py -p mvp_dataset -a claude-code -m claude-sonnet-4-5-20250929

# Use a different agent (codex, gemini-cli, etc.)
uv run python main.py -p mvp_dataset -a codex
```

## Available Agents

Harbor comes with these pre-integrated agents:

`oracle`, `nop`, `claude-code`, `cline-cli`, `terminus-2`, `aider`, `codex`, `cursor-cli`, `gemini-cli`, `goose`, `mini-swe-agent`, `swe-agent`, `openhands`, `qwen-coder`

## Adding New Tasks

```bash
harbor tasks init <task-name> -p mvp_dataset --no-solution
```

Then fill in `instruction.md` and `tests/test_outputs.py`.
