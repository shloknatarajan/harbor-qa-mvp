# Harbor PGxQA MVP
Goal: Allow CLI agents to answer PGxQA questions. We specifically also want to create environments that allow the agents to read/analyze across many papers at a time, especially at context sizes that would be too large for single prompted LM calls.

## CLI Agents of Interst
- Codex
- Claude
- Gemini

## Tasks
- [X] Basic running of a harbor cli agent on a local question
- [X] MVP: Figure out how to feed papers + question to the CLI agent
- [ ] Port over one dataset from PGxQA
- [ ] Benchmark the popular cli agents on the dataset

## Links
[BixBench](https://huggingface.co/datasets/futurehouse/BixBench/viewer/default/train?row=0)


## Available Agents
Provided by harbor:
- oracle
- nop
- claude-code
- cline-cli
- terminus
- terminus-1
- terminus-2
- aider
- codex
- cursor-cli
- gemini-cli
- goose
- mini-swe-agent
- swe-agent
- opencode
- openhands
- qwen-coder