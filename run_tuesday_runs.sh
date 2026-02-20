#!/usr/bin/env bash
set -euo pipefail

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi
echo "==> (1/2) summary_qa | codex | model=gpt-5 | n=2"
python main.py -p summary_qa -a codex -m gpt-5 -n 2

echo "==> (2/2) summary_qa | codex | model=o4-mini | n=2"
python main.py -p summary_qa -a codex -m o4-mini -n 2

echo "All runs finished."
