"""Generate the summary_qa Harbor dataset from summary_annotations.jsonl.

For each annotation that has papers available (via PMCID mapping), creates
a Harbor task where the agent is given the relevant papers plus 10 random
distractor papers. The agent must identify the associated drugs, phenotypes,
and relevant paper count for a specific variant.

Scoring is based on recall for drugs and phenotypes, and exact match for
paper count.

Usage:
    python summary_qa/generate_questions.py
"""

import json
import random
import re
import shutil
from pathlib import Path

random.seed(42)

MAX_TASKS = 100
NUM_DISTRACTORS = 10

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent
PAPERS_DIR = PROJECT_ROOT / "data" / "papers"
ANNOTATIONS_FILE = BASE / "summary_annotations.jsonl"

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
COPY term_banks/ /app/term_banks/
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
$HOME/.local/bin/uv run python - <<'PYEOF'
import json, pathlib
ctrf = json.loads(pathlib.Path("/logs/verifier/ctrf.json").read_text())
summary = ctrf["results"]["summary"]
total = summary["tests"]
passed = summary["passed"]
reward = passed / total if total > 0 else 0.0
pathlib.Path("/logs/verifier/reward.txt").write_text(str(reward))
PYEOF
"""


def build_instruction(record: dict, all_pmcids: list[str]) -> str:
    """Build the instruction.md content for a task."""
    variant = record["variant_haplotypes"]
    gene = record["gene"]
    category = record["phenotype_category"]

    lines = [
        "You are a pharmacogenomics researcher. "
        "A collection of research papers is available in `/app/papers/`. "
        "Some of these papers are relevant to the variant of interest, while "
        "many are unrelated distractors.",
        "",
        f"**Variant:** {variant}",
        f"**Gene:** {gene}",
        f"**Phenotype Category:** {category}",
        "",
        "Term banks of known drug and phenotype names are available at:",
        "- `/app/term_banks/drugs.txt` — one drug name per line",
        "- `/app/term_banks/phenotypes.txt` — one phenotype name per line",
        "",
        "Your task is to read through the papers and identify the following "
        f"information about **{variant}** in gene **{gene}**:",
        "",
        "1. **Drugs**: Select all drugs associated with this variant from the drug term bank.",
        "2. **Phenotypes**: Select all phenotypes (diseases/conditions) associated with this variant from the phenotype term bank.",
        f"3. **Relevant paper count**: How many of the papers in `/app/papers/` are relevant to {variant}?",
        "",
        "---",
        "",
        "You must write your answers to `/app/answers.json` (a real file on disk). Printing JSON in chat is not sufficient.",
        "After writing the file, verify it exists and contains valid JSON.",
        "",
        "For example, you may use a shell heredoc to write the file:",
        "```bash",
        "cat > /app/answers.json <<'JSON'",
        "{",
        '  "drugs": ["drug1", "drug2"],',
        '  "phenotypes": ["phenotype1", "phenotype2"],',
        '  "relevant_paper_count": 3',
        "}",
        "JSON",
        "python -c 'import json; json.load(open(\"/app/answers.json\"))'",
        "```",
        "",
        "The JSON object must have the following structure:",
        "",
        "```json",
        "{",
        '  "drugs": ["drug1", "drug2"],',
        '  "phenotypes": ["phenotype1", "phenotype2"],',
        '  "relevant_paper_count": 3',
        "}",
        "```",
        "",
        "Notes:",
        "- Drug and phenotype names should be lowercase.",
        "- Only select terms from the provided term banks. Do not add terms that are not in the banks.",
        f"- The papers directory contains {len(all_pmcids)} papers total. Count only those relevant to {variant}.",
        "- **Do not use web search.** All information you need is in the provided papers and term banks.",
    ]
    return "\n".join(lines)


def build_test_py(record: dict) -> str:
    """Build the test_outputs.py content for a task."""
    expected_drugs = sorted([d.lower() for d in record["drugs"]])
    expected_phenotypes = sorted([p.lower() for p in record["phenotypes"]])
    expected_count = len(record["_available_pmcids"])

    lines = [
        "import json",
        "from pathlib import Path",
        "",
        "import pytest",
        "",
        "",
        f"EXPECTED_DRUGS = {json.dumps(expected_drugs)}",
        f"EXPECTED_PHENOTYPES = {json.dumps(expected_phenotypes)}",
        f"EXPECTED_RELEVANT_PAPER_COUNT = {expected_count}",
        "",
        "",
        "@pytest.fixture(scope='module')",
        "def answers():",
        '    f = Path("/app/answers.json")',
        '    assert f.exists(), "answers.json not found"',
        "    return json.loads(f.read_text())",
        "",
        "",
        "def normalize(items: list[str]) -> set[str]:",
        '    """Normalize a list of strings to lowercase stripped set."""',
        "    return {s.strip().lower() for s in items if s.strip()}",
        "",
        "",
        "def test_drugs_recall(answers):",
        '    """Check that all expected drugs are found (recall)."""',
        '    got = normalize(answers.get("drugs", []))',
        "    expected = set(EXPECTED_DRUGS)",
        "    missing = expected - got",
        "    assert not missing, (",
        '        f"Missing drugs: {missing}. Got: {sorted(got)}"',
        "    )",
        "",
        "",
        "def test_phenotypes_recall(answers):",
        '    """Check that all expected phenotypes are found (recall)."""',
        '    got = normalize(answers.get("phenotypes", []))',
        "    expected = set(EXPECTED_PHENOTYPES)",
        "    missing = expected - got",
        "    assert not missing, (",
        '        f"Missing phenotypes: {missing}. Got: {sorted(got)}"',
        "    )",
        "",
        "",
        "def test_relevant_paper_count(answers):",
        '    """Check the relevant paper count is correct."""',
        '    got = answers.get("relevant_paper_count", -1)',
        "    assert got == EXPECTED_RELEVANT_PAPER_COUNT, (",
        '        f"Expected {EXPECTED_RELEVANT_PAPER_COUNT} relevant papers, got {got}"',
        "    )",
        "",
    ]
    return "\n".join(lines)


def main():
    # Load all annotations
    annotations = []
    with open(ANNOTATIONS_FILE, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            annotations.append(rec)

    # Filter to annotations with at least 1 PMCID that has a paper on disk
    eligible = []
    for rec in annotations:
        available_pmcids = [
            p for p in rec["pmcids"] if (PAPERS_DIR / f"{p}.md").exists()
        ]
        if available_pmcids:
            rec["_available_pmcids"] = available_pmcids
            eligible.append(rec)

    print(f"Total annotations: {len(annotations)}")
    print(f"Eligible (have papers): {len(eligible)}")

    # Also filter to records that have at least 1 drug (otherwise question is trivial)
    eligible = [r for r in eligible if r["drugs"]]
    print(f"Eligible with drugs: {len(eligible)}")

    # Select up to MAX_TASKS, preferring higher scores (more evidence)
    eligible.sort(key=lambda r: float(r["score"]), reverse=True)
    selected = eligible[:MAX_TASKS]

    # Build term banks from ALL annotations (not just selected)
    all_drugs: set[str] = set()
    all_phenotypes: set[str] = set()
    for rec in annotations:
        for d in rec.get("drugs", []):
            all_drugs.add(d.lower())
        for p in rec.get("phenotypes", []):
            all_phenotypes.add(p.lower())
    drug_bank = sorted(all_drugs)
    phenotype_bank = sorted(all_phenotypes)
    print(f"Term banks: {len(drug_bank)} drugs, {len(phenotype_bank)} phenotypes")

    # Collect all available PMCIDs for distractor sampling
    all_available_pmcids = [p.stem for p in PAPERS_DIR.iterdir() if p.suffix == ".md"]

    # Clean existing task dirs
    for d in BASE.iterdir():
        if d.is_dir() and d.name != "__pycache__":
            shutil.rmtree(d)

    total_papers = 0
    for idx, rec in enumerate(selected, 1):
        ann_id = rec["summary_annotation_id"]
        relevant_pmcids = rec["_available_pmcids"]

        # Pick distractors (PMCIDs not in the relevant set)
        relevant_set = set(relevant_pmcids)
        distractor_pool = [p for p in all_available_pmcids if p not in relevant_set]
        distractors = random.sample(
            distractor_pool, min(NUM_DISTRACTORS, len(distractor_pool))
        )

        all_pmcids = relevant_pmcids + distractors
        random.shuffle(all_pmcids)
        total_papers += len(all_pmcids)

        # Build task name: <variant>_<summary_annotation_id>
        variant_slug = re.sub(
            r"[^a-z0-9]+", "_", rec["variant_haplotypes"].lower()
        ).strip("_")
        task_name = f"{variant_slug}_{ann_id}"
        task_dir = BASE / task_name

        # instruction.md
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "instruction.md").write_text(build_instruction(rec, all_pmcids))

        # task.toml
        (task_dir / "task.toml").write_text(TASK_TOML)

        # environment/Dockerfile + papers
        env_dir = task_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        (env_dir / "Dockerfile").write_text(DOCKERFILE)

        papers_dir = env_dir / "papers"
        papers_dir.mkdir(exist_ok=True)
        for pmcid in all_pmcids:
            src = PAPERS_DIR / f"{pmcid}.md"
            if src.exists():
                shutil.copy2(src, papers_dir / f"{pmcid}.md")

        # term_banks/
        term_banks_dir = env_dir / "term_banks"
        term_banks_dir.mkdir(exist_ok=True)
        (term_banks_dir / "drugs.txt").write_text("\n".join(drug_bank) + "\n")
        (term_banks_dir / "phenotypes.txt").write_text("\n".join(phenotype_bank) + "\n")

        # tests/
        tests_dir = task_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test.sh").write_text(TEST_SH)
        (tests_dir / "test_outputs.py").write_text(build_test_py(rec))

        variant = rec["variant_haplotypes"]
        n_drugs = len(rec["drugs"])
        n_pheno = len(rec["phenotypes"])
        n_rel = len(relevant_pmcids)
        print(
            f"  [{idx:3d}/{len(selected)}] {task_name} — {variant} "
            f"({n_drugs} drugs, {n_pheno} phenotypes, {n_rel} relevant + "
            f"{len(distractors)} distractors)"
        )

    print(f"\nGenerated {len(selected)} tasks with {total_papers} total paper copies.")


if __name__ == "__main__":
    main()
