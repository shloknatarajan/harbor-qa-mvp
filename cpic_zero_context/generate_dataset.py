"""Generate the cpic_reproduction Harbor dataset (zero-context prediction).

Benchmarks whether AI agents can reproduce CPIC pharmacogenomics guidelines
from parametric knowledge alone (no papers provided). For each gene-drug-variant
combination, the agent must predict the clinical recommendation, its
classification strength, and key implications.

Scoring is based on 3 deterministic tests: action category match,
classification match, and key term recall.

Generate:
    python cpic_zero_context/generate_dataset.py

Run:
    python main.py -p cpic_zero_context -a claude-code -n 3 -l 50
"""

import csv
import json
import random
import re
import shutil
from pathlib import Path

random.seed(42)

MAX_TASKS = 100

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent
DATA_DIR = PROJECT_ROOT / "data" / "cpic_data"

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
allow_internet = false
mcp_servers = []

[verifier.env]

[solution.env]
"""

DOCKERFILE = """\
FROM ubuntu:24.04

WORKDIR /app
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

# ── Action category mapping ────────────────────────────────────────────

ACTION_CATEGORIES = {
    "avoid": [
        "contraindicated",
        "not recommended",
        "is not recommended",
        "avoid",
        "do not use",
    ],
    "standard_dosing": [
        "per standard dosing",
        "standard dosing guidelines",
        "at standard doses",
        "standard dose",
        "label-recommended",
    ],
    "dose_reduction": [
        "reduce dose",
        "reduced dose",
        "decrease dose",
        "decreased dose",
        "lower dose",
        "reduce starting dose",
        "50% reduction",
        "50% of standard",
        "dose decrease",
        "dose reduction",
    ],
    "dose_increase": [
        "increase dose",
        "increased dose",
        "higher dose",
        "dose increase",
        "titrate to higher",
    ],
    "alternative": [
        "alternative",
        "consider other",
        "use an alternative",
        "select alternative",
        "consider alternative",
    ],
    "monitor": [
        "monitor",
        "caution",
        "with therapeutic drug monitoring",
    ],
}


def classify_action(recommendation: str) -> str:
    """Map a CPIC recommendation to an action category using keyword matching."""
    rec_lower = recommendation.lower()
    for category, keywords in ACTION_CATEGORIES.items():
        for kw in keywords:
            if kw in rec_lower:
                return category
    return "other"


def extract_key_terms(recommendation: str) -> list[str]:
    """Extract clinically significant phrases from a recommendation."""
    rec_lower = recommendation.lower()
    terms = []
    # Check against all action category keywords
    for keywords in ACTION_CATEGORIES.values():
        for kw in keywords:
            if kw in rec_lower:
                terms.append(kw)
    # Also extract drug-specific phrases
    # Look for specific dosing phrases like "50%", percentage mentions
    pct = re.findall(r"\d+%", recommendation)
    terms.extend(pct)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


# ── Data loading ───────────────────────────────────────────────────────


def load_tsv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_data() -> list[dict]:
    """Load and join CPIC data tables. Returns eligible task records."""
    recommendations = {r["id"]: r for r in load_tsv(DATA_DIR / "recommendation.tsv")}
    pairs = {}
    for p in load_tsv(DATA_DIR / "pair.tsv"):
        pairs[(p["guidelineid"], p["drugid"])] = p
    variant_recs = load_tsv(DATA_DIR / "variant_recommendations_consolidated.tsv")

    eligible = []
    for vr in variant_recs:
        # Single-gene only
        if vr["component_count"] != "1":
            continue

        rec = recommendations.get(vr["rec_id"])
        if not rec:
            continue

        # Join with pair.tsv for CPIC level
        pair_key = (rec["guidelineid"], rec["drugid"])
        pair = pairs.get(pair_key)
        if not pair:
            continue

        # Level A only (strongest evidence)
        if pair.get("cpiclevel") != "A":
            continue

        # Exclude No Result / Indeterminate variants
        variants_str = vr["variants"]
        if any(
            skip in variants_str.lower()
            for skip in ["no result", "indeterminate", "n/a"]
        ):
            continue

        # Parse variant descriptions
        try:
            variants_list = json.loads(vr["variants"])
        except json.JSONDecodeError:
            variants_list = [vr["variants"]]

        # Parse implications from recommendation table
        try:
            implications = json.loads(rec["implications"])
        except json.JSONDecodeError:
            implications = {}

        action = classify_action(vr["recommendation"])

        eligible.append(
            {
                "rec_id": vr["rec_id"],
                "drug": vr["drug"],
                "gene": vr["lookup_genes"],
                "recommendation": vr["recommendation"],
                "classification": rec["classification"],
                "implications": implications,
                "variants": variants_list,
                "variant_description": "; ".join(variants_list),
                "action_category": action,
                "key_terms": extract_key_terms(vr["recommendation"]),
            }
        )

    return eligible


# ── Task generation ────────────────────────────────────────────────────


def build_instruction(record: dict) -> str:
    drug = record["drug"]
    gene = record["gene"]
    variant_desc = record["variant_description"]

    lines = [
        "You are a clinical pharmacogenomics expert.",
        "",
        f"**Drug:** {drug}",
        f"**Gene:** {gene}",
        f"**Patient Genotype:** {variant_desc}",
        "",
        "Based on your knowledge of pharmacogenomics, provide a clinical "
        "recommendation for this drug-gene-variant combination.",
        "",
        "---",
        "",
        "You must write your answers to `/app/answers.json` "
        "(a real file on disk). Printing JSON in chat is not sufficient.",
        "After writing the file, verify it exists and contains valid JSON.",
        "",
        "For example, you may use a shell heredoc to write the file:",
        "```bash",
        "cat > /app/answers.json <<'JSON'",
        "{",
        '  "recommendation": "Use drug per standard dosing guidelines",',
        '  "classification": "Strong",',
        '  "implication": "Normal metabolism expected"',
        "}",
        "JSON",
        "python3 -c 'import json; json.load(open(\"/app/answers.json\"))'",
        "```",
        "",
        "The JSON object must have the following structure:",
        "",
        "```json",
        "{",
        '  "recommendation": "<dosing recommendation text>",',
        '  "classification": "<Strong|Moderate|Optional>",',
        '  "implication": "<clinical implication of this genotype>"',
        "}",
        "```",
        "",
        "Notes:",
        "- **recommendation**: Your clinical dosing recommendation for this "
        "drug-gene-variant combination.",
        "- **classification**: The strength of this recommendation "
        "(Strong, Moderate, or Optional).",
        "- **implication**: The clinical implication of this specific genotype "
        "for this drug's metabolism/response.",
        "- **Do not use web search.** Rely only on your pharmacogenomics knowledge.",
    ]
    return "\n".join(lines)


def build_test_py(record: dict) -> str:
    action = record["action_category"]
    classification = record["classification"]
    key_terms = record["key_terms"]
    recommendation = record["recommendation"]

    lines = [
        "import json",
        "import re",
        "from pathlib import Path",
        "",
        "import pytest",
        "",
        "",
        f"EXPECTED_ACTION_CATEGORY = {json.dumps(action)}",
        f"EXPECTED_CLASSIFICATION = {json.dumps(classification)}",
        f"EXPECTED_KEY_TERMS = {json.dumps(key_terms)}",
        f"EXPECTED_RECOMMENDATION = {json.dumps(recommendation)}",
        "",
        "",
        "# Action category keyword mapping",
        "ACTION_KEYWORDS = {",
        '    "avoid": ["contraindicated", "not recommended", "avoid", "do not use"],',
        '    "standard_dosing": ["per standard dosing", "standard dosing", '
        '"at standard doses", "standard dose", "label-recommended"],',
        '    "dose_reduction": ["reduce dose", "reduced dose", "decrease dose", '
        '"decreased dose", "lower dose", "dose decrease", "dose reduction", '
        '"50% reduction", "50% of standard"],',
        '    "dose_increase": ["increase dose", "increased dose", "higher dose", '
        '"dose increase"],',
        '    "alternative": ["alternative", "consider other", "select alternative"],',
        '    "monitor": ["monitor", "caution", "therapeutic drug monitoring"],',
        "}",
        "",
        "",
        "def classify_recommendation(text: str) -> str:",
        '    """Classify a recommendation into an action category."""',
        "    text_lower = text.lower()",
        "    for category, keywords in ACTION_KEYWORDS.items():",
        "        for kw in keywords:",
        "            if kw in text_lower:",
        "                return category",
        '    return "other"',
        "",
        "",
        "@pytest.fixture(scope='module')",
        "def answers():",
        '    f = Path("/app/answers.json")',
        '    assert f.exists(), "answers.json not found"',
        "    return json.loads(f.read_text())",
        "",
        "",
        "def test_action_category(answers):",
        '    """Check that the recommendation maps to the correct action category."""',
        '    rec_text = answers.get("recommendation", "")',
        "    got_category = classify_recommendation(rec_text)",
        "    assert got_category == EXPECTED_ACTION_CATEGORY, (",
        '        f"Expected action category \'{EXPECTED_ACTION_CATEGORY}\', '
        "got '{got_category}' \"",
        '        f"from recommendation: {rec_text}"',
        "    )",
        "",
        "",
        "def test_classification(answers):",
        '    """Check that the classification strength matches."""',
        '    got = answers.get("classification", "").strip()',
        "    assert got.lower() == EXPECTED_CLASSIFICATION.lower(), (",
        '        f"Expected classification \'{EXPECTED_CLASSIFICATION}\', got \'{got}\'"',
        "    )",
        "",
        "",
        "def test_key_terms(answers):",
        '    """Check that at least one key term from CPIC rec appears in output."""',
        "    if not EXPECTED_KEY_TERMS:",
        "        pytest.skip('No key terms defined for this recommendation')",
        "    # Combine all text fields from the agent's answer",
        '    all_text = " ".join([',
        '        answers.get("recommendation", ""),',
        '        answers.get("implication", ""),',
        "    ]).lower()",
        "    found = [t for t in EXPECTED_KEY_TERMS if t.lower() in all_text]",
        "    assert found, (",
        '        f"None of the expected key terms found in agent output. "',
        '        f"Expected one of: {EXPECTED_KEY_TERMS}"',
        "    )",
        "",
    ]
    return "\n".join(lines)


def main():
    eligible = load_data()
    print(f"Eligible records (single-gene, Level A, clean variants): {len(eligible)}")

    # Show action category distribution
    from collections import Counter

    action_dist = Counter(r["action_category"] for r in eligible)
    print(f"Action categories: {dict(action_dist)}")

    # Sample up to MAX_TASKS, stratified across genes and drugs
    # Shuffle and take diverse sample
    random.shuffle(eligible)

    # Group by (gene, drug) to ensure diversity
    by_gene_drug: dict[tuple[str, str], list[dict]] = {}
    for rec in eligible:
        key = (rec["gene"], rec["drug"])
        by_gene_drug.setdefault(key, []).append(rec)

    selected: list[dict] = []
    # Round-robin across gene-drug pairs
    keys = sorted(by_gene_drug.keys())
    random.shuffle(keys)
    idx = 0
    while len(selected) < MAX_TASKS and idx < len(eligible):
        for key in keys:
            if len(selected) >= MAX_TASKS:
                break
            recs = by_gene_drug[key]
            # Take next unused record from this group
            for rec in recs:
                if rec not in selected:
                    selected.append(rec)
                    break
        idx += 1

    print(f"Selected {len(selected)} tasks")

    # Show selected distribution
    sel_genes = Counter(r["gene"] for r in selected)
    sel_drugs = Counter(r["drug"] for r in selected)
    sel_actions = Counter(r["action_category"] for r in selected)
    print(f"  Genes: {dict(sel_genes)}")
    print(f"  Drugs (top 10): {sel_drugs.most_common(10)}")
    print(f"  Actions: {dict(sel_actions)}")

    # Clean existing task dirs (preserve __pycache__ and .py files)
    for d in BASE.iterdir():
        if d.is_dir() and d.name != "__pycache__":
            shutil.rmtree(d)

    for i, rec in enumerate(selected, 1):
        gene_slug = re.sub(r"[^a-z0-9]+", "_", rec["gene"].lower()).strip("_")
        drug_slug = re.sub(r"[^a-z0-9]+", "_", rec["drug"].lower()).strip("_")
        task_name = f"{gene_slug}_{drug_slug}_{rec['rec_id']}"
        task_dir = BASE / task_name

        # instruction.md
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "instruction.md").write_text(build_instruction(rec))

        # task.toml
        (task_dir / "task.toml").write_text(TASK_TOML)

        # environment/
        env_dir = task_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        (env_dir / "Dockerfile").write_text(DOCKERFILE)

        # tests/
        tests_dir = task_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test.sh").write_text(TEST_SH)
        (tests_dir / "test_outputs.py").write_text(build_test_py(rec))

        variant = rec["variant_description"]
        action = rec["action_category"]
        cls = rec["classification"]
        print(
            f"  [{i:3d}/{len(selected)}] {task_name} — "
            f"{variant[:50]} | {action} | {cls}"
        )

    print(f"\nGenerated {len(selected)} tasks in {BASE}/")
    print(f"Run: python main.py -p cpic_zero_context -a claude-code -n 1 -l 1")


if __name__ == "__main__":
    main()
