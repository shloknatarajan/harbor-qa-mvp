"""Generate the pgx_drug_qa Harbor dataset from drug_mcq_options.jsonl.

Groups questions by PMCID, selects 100 PMCIDs (that have papers available),
and creates one Harbor task per PMCID. Each task presents ALL questions for
that PMCID and scores based on the percentage answered correctly.

Usage:
    python pgx_drug_qa/generate_dataset.py
"""

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

MAX_PMCIDS = 100

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent
PAPERS_DIR = PROJECT_ROOT / "data" / "papers"
QUESTIONS_FILE = PROJECT_ROOT / "data" / "mc_questions" / "drug_mcq_options.jsonl"

TASK_TOML = """\
version = "1.0"

[metadata]

[verifier]
timeout_sec = 600.0

[agent]
timeout_sec = 600.0

[environment]
build_timeout_sec = 600.0
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
allow_internet = true
mcp_servers = []

[verifier.env]

[solution.env]
"""

DOCKERFILE = """\
FROM ubuntu:24.04

WORKDIR /app

COPY papers/ /app/papers/
"""

TEST_SH = """\
#!/bin/bash

apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh

source $HOME/.local/bin/env

uvx \\
  --with pytest==8.4.1 \\
  --with pytest-json-ctrf==0.3.5 \\
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

# Write the fraction of passed tests as the reward
python3 - <<'PYEOF'
import json, pathlib
ctrf = json.loads(pathlib.Path("/logs/verifier/ctrf.json").read_text())
summary = ctrf["results"]["summary"]
total = summary["tests"]
passed = summary["passed"]
reward = passed / total if total > 0 else 0.0
pathlib.Path("/logs/verifier/reward.txt").write_text(str(reward))
PYEOF
"""


def build_instruction(pmcid: str, questions: list[dict]) -> str:
    lines = [
        "You are answering pharmacogenomics multiple-choice questions. "
        "One or more research papers are available in `/app/papers/` — read them to find the answers.",
        "",
        f"There are **{len(questions)} questions** below. For each question, determine the correct answer letter.",
        "",
    ]

    for i, q in enumerate(questions, 1):
        lines.append(f"## Question {i}")
        lines.append("")
        lines.append(q["blanked_sentence"])
        lines.append("")
        lines.append("Which drug correctly fills in the blank?")
        lines.append("")
        lines.append(f"- a) {q['option_a']}")
        lines.append(f"- b) {q['option_b']}")
        lines.append(f"- c) {q['option_c']}")
        lines.append(f"- d) {q['option_d']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"Write your answers to `/app/answers.json` as a JSON object mapping "
        f'question numbers (as strings) to answer letters. For example:'
    )
    lines.append("")
    lines.append("```json")
    example = {str(i): "a" for i in range(1, min(4, len(questions) + 1))}
    lines.append(json.dumps(example, indent=2))
    lines.append("```")
    lines.append("")
    lines.append(
        f"You must answer all {len(questions)} questions (keys \"1\" through \"{len(questions)}\")."
    )
    lines.append("")

    return "\n".join(lines)


def build_test_py(questions: list[dict]) -> str:
    lines = [
        "import json",
        "from pathlib import Path",
        "",
        "import pytest",
        "",
        "",
        "EXPECTED = {",
    ]
    for i, q in enumerate(questions, 1):
        lines.append(f'    "{i}": "{q["correct_answer"]}",')
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("@pytest.fixture(scope='module')")
    lines.append("def answers():")
    lines.append('    f = Path("/app/answers.json")')
    lines.append('    assert f.exists(), "answers.json not found"')
    lines.append("    return json.loads(f.read_text())")
    lines.append("")
    lines.append("")

    for i, q in enumerate(questions, 1):
        lines.append(f"def test_question_{i}(answers):")
        lines.append(f'    got = answers.get("{i}", "").strip().lower()')
        lines.append(
            f'    assert got == "{q["correct_answer"]}", '
            f'f"Q{i}: expected \'{q["correct_answer"]}\', got \'{{got}}\'"'
        )
        lines.append("")
        lines.append("")

    return "\n".join(lines)


def main():
    # Load all questions grouped by PMCID
    by_pmcid: dict[str, list[dict]] = defaultdict(list)
    with open(QUESTIONS_FILE) as f:
        for line in f:
            q = json.loads(line)
            by_pmcid[q["pmcid"]].append(q)

    # Filter to PMCIDs that have a paper file available
    available = []
    for pmcid in sorted(by_pmcid.keys()):
        paper = PAPERS_DIR / f"{pmcid}.md"
        if paper.exists():
            available.append(pmcid)

    print(f"PMCIDs with questions: {len(by_pmcid)}")
    print(f"PMCIDs with papers available: {len(available)}")

    if len(available) < MAX_PMCIDS:
        print(f"WARNING: only {len(available)} PMCIDs available, need {MAX_PMCIDS}")

    selected = available[:MAX_PMCIDS]

    # Clean existing task dirs
    for d in BASE.iterdir():
        if d.is_dir() and d.name.lower().startswith("pmc"):
            shutil.rmtree(d)

    total_questions = 0
    for idx, pmcid in enumerate(selected, 1):
        questions = by_pmcid[pmcid]
        total_questions += len(questions)
        task_name = pmcid.lower()
        task_dir = BASE / task_name

        # instruction.md
        (task_dir).mkdir(parents=True, exist_ok=True)
        (task_dir / "instruction.md").write_text(build_instruction(pmcid, questions))

        # task.toml
        (task_dir / "task.toml").write_text(TASK_TOML)

        # environment/Dockerfile + papers
        env_dir = task_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        (env_dir / "Dockerfile").write_text(DOCKERFILE)

        papers_dir = env_dir / "papers"
        papers_dir.mkdir(exist_ok=True)
        src = PAPERS_DIR / f"{pmcid}.md"
        shutil.copy2(src, papers_dir / f"{pmcid}.md")

        # tests/
        tests_dir = task_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test.sh").write_text(TEST_SH)
        (tests_dir / "test_outputs.py").write_text(build_test_py(questions))

        print(f"  [{idx:3d}/{MAX_PMCIDS}] {task_name} ({pmcid}) — {len(questions)} questions")

    print(f"\nGenerated {len(selected)} tasks with {total_questions} total questions.")


if __name__ == "__main__":
    main()
