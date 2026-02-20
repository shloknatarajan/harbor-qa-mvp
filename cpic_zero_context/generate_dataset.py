"""Generate the cpic_reproduction Harbor dataset (zero-context prediction).

Benchmarks whether AI agents can reproduce CPIC pharmacogenomics guidelines
from parametric knowledge alone (no papers provided). For each gene-drug-variant
combination, the agent must predict the clinical recommendation, its
classification strength, and key implications.

Scoring uses a hybrid approach:
  - Classification strength: deterministic exact match
  - Action correctness, recommendation completeness, implication accuracy:
    strict LLM-as-judge evaluation (Claude Sonnet, threshold >= 4/5)

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
allow_internet = true
mcp_servers = []

[verifier.env]
ANTHROPIC_API_KEY = "${ANTHROPIC_API_KEY}"

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
  --with anthropic==0.52.0 \\
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

# ── LLM Judge prompt ──────────────────────────────────────────────────

JUDGE_PROMPT_TEMPLATE = """\
You are a STRICT pharmacogenomics evaluation judge. You are comparing an AI \
agent's clinical recommendation against the official CPIC guideline. \
Be rigorous — clinical details matter and vague or incomplete answers should \
score low. Do NOT give the benefit of the doubt.

## Ground Truth (CPIC Guideline)
- **Drug:** {drug}
- **Gene:** {gene}
- **Patient Genotype:** {variant}
- **CPIC Recommendation:** {expected_rec}
- **Classification Strength:** {expected_class}
- **CPIC Implication:** {expected_impl}

## Agent's Answer
- **Recommendation:** {agent_rec}
- **Classification:** {agent_class}
- **Implication:** {agent_impl}

## Evaluation Criteria

Score EACH dimension on a 1-5 scale. Be strict: a score of 5 means \
essentially perfect, 4 means correct with only trivial omissions. \
Anything missing a clinically meaningful detail should be 3 or below.

1. **action_correctness**: Does the agent recommend the SAME clinical action?
   - 5: Exact same action (e.g., both say "avoid", both say "reduce dose by 50%")
   - 4: Same core action with only trivial wording differences
   - 3: Right direction but missing critical qualifiers (e.g., "reduce dose" \
when guideline says "reduce dose by 50%" — the percentage matters)
   - 2: Partially overlapping but meaningfully different action
   - 1: Wrong action (e.g., "use standard dose" vs "avoid")

2. **recommendation_completeness**: Does the agent capture ALL clinically \
significant details from the CPIC recommendation?
   - 5: All specific details present (dosing percentages, monitoring \
requirements, alternative drug suggestions, caveats)
   - 4: All major details present, at most one minor detail missing
   - 3: Core action correct but missing important specifics (e.g., omits TDM \
requirement, omits specific dose adjustment percentage)
   - 2: Vague or generic — gives broad direction without actionable detail
   - 1: Missing or wrong details

3. **implication_accuracy**: Does the agent's stated implication correctly \
describe the pharmacogenomic phenotype for this genotype?
   - 5: Correctly identifies the metabolizer status/phenotype and its clinical \
consequence (e.g., "poor metabolizer — reduced conversion to active metabolite")
   - 4: Correct phenotype with minor imprecision in clinical consequence
   - 3: Partially correct (e.g., right metabolizer status but wrong or missing \
clinical consequence, or vice versa)
   - 2: Vague or generic implication not specific to this genotype
   - 1: Wrong phenotype or wrong clinical consequence

4. **safety**: Is the recommendation safe for the patient?
   - 5: Fully safe, matches guideline
   - 4: Safe with minor omissions (e.g., missing a secondary monitoring note)
   - 3: Mostly safe but missing important caveats (e.g., omits critical \
drug interaction warning or contraindication)
   - 2: Could lead to suboptimal care
   - 1: Potentially dangerous (e.g., recommending standard dose when drug \
should be avoided)

Respond with ONLY a JSON object. No markdown fences, no explanation:
{{"action_correctness": <1-5>, "recommendation_completeness": <1-5>, \
"implication_accuracy": <1-5>, "safety": <1-5>, "rationale": "<1-2 sentences>"}}\
"""


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

        # Build a flat implication string from the implications dict
        impl_parts = []
        for gene_name, impl_text in implications.items():
            if impl_text and impl_text.strip():
                impl_parts.append(f"{gene_name}: {impl_text}")
        implication_str = "; ".join(impl_parts) if impl_parts else ""

        eligible.append(
            {
                "rec_id": vr["rec_id"],
                "drug": vr["drug"],
                "gene": vr["lookup_genes"],
                "recommendation": vr["recommendation"],
                "classification": rec["classification"],
                "implication": implication_str,
                "variants": variants_list,
                "variant_description": "; ".join(variants_list),
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
        '  "classification": "Moderate",',
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
        '  "classification": "<Strong|Moderate|Optional|No Recommendation>",',
        '  "implication": "<clinical implication of this genotype>"',
        "}",
        "```",
        "",
        "Notes:",
        "- **recommendation**: Your clinical dosing recommendation for this "
        "drug-gene-variant combination.",
        "- **classification**: The CPIC classification strength of this "
        "recommendation, based on the quality and quantity of clinical "
        "evidence supporting it:",
        "  - **Strong**: High-quality evidence and/or strong expert consensus "
        "that the recommendation should be followed.",
        "  - **Moderate**: Moderate evidence; the recommendation is generally "
        "appropriate but evidence is less definitive.",
        "  - **Optional**: Weak or emerging evidence; clinical action is "
        "at the prescriber's discretion.",
        "  - **No Recommendation**: Insufficient evidence to make a "
        "recommendation for this gene-drug-phenotype combination.",
        "- **implication**: The clinical implication of this specific genotype "
        "for this drug's metabolism/response.",
        "- **Do not use web search.** Rely only on your pharmacogenomics knowledge.",
    ]
    return "\n".join(lines)


def build_test_py(record: dict) -> str:
    """Build a pytest test file using LLM-as-judge + deterministic classification."""
    classification = record["classification"]
    recommendation = record["recommendation"]
    implication = record["implication"]
    drug = record["drug"]
    gene = record["gene"]
    variant_desc = record["variant_description"]

    return f'''\
import os
import json
from pathlib import Path

import pytest


EXPECTED_RECOMMENDATION = {json.dumps(recommendation)}
EXPECTED_CLASSIFICATION = {json.dumps(classification)}
EXPECTED_IMPLICATION = {json.dumps(implication)}
DRUG = {json.dumps(drug)}
GENE = {json.dumps(gene)}
VARIANT = {json.dumps(variant_desc)}


JUDGE_PROMPT = {json.dumps(JUDGE_PROMPT_TEMPLATE)}


@pytest.fixture(scope="module")
def answers():
    f = Path("/app/answers.json")
    assert f.exists(), "answers.json not found"
    return json.loads(f.read_text())


@pytest.fixture(scope="module")
def judge_scores(answers):
    """Call LLM judge to evaluate the agent\'s recommendation."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set — cannot run LLM judge")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    prompt = JUDGE_PROMPT.format(
        drug=DRUG,
        gene=GENE,
        variant=VARIANT,
        expected_rec=EXPECTED_RECOMMENDATION,
        expected_class=EXPECTED_CLASSIFICATION,
        expected_impl=EXPECTED_IMPLICATION,
        agent_rec=answers.get("recommendation", ""),
        agent_class=answers.get("classification", ""),
        agent_impl=answers.get("implication", ""),
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{{"role": "user", "content": prompt}}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


# ── Deterministic test ────────────────────────────────────────────────


def test_classification(answers):
    """Check that the classification strength matches exactly."""
    got = answers.get("classification", "").strip()
    assert got.lower() == EXPECTED_CLASSIFICATION.lower(), (
        f"Expected classification \'{{EXPECTED_CLASSIFICATION}}\', got \'{{got}}\'"
    )


# ── LLM judge tests (strict: require >= 4/5) ─────────────────────────


def test_action_correctness(judge_scores):
    """LLM judge: does the recommendation match the correct clinical action?"""
    score = judge_scores["action_correctness"]
    assert score >= 4, (
        f"Action correctness {{score}}/5 (need >= 4). "
        f"Rationale: {{judge_scores.get(\'rationale\', \'\')}}"
    )


def test_recommendation_completeness(judge_scores):
    """LLM judge: does the recommendation capture all critical clinical details?"""
    score = judge_scores["recommendation_completeness"]
    assert score >= 4, (
        f"Recommendation completeness {{score}}/5 (need >= 4). "
        f"Rationale: {{judge_scores.get(\'rationale\', \'\')}}"
    )


def test_implication_accuracy(judge_scores):
    """LLM judge: is the stated implication correct for this genotype?"""
    score = judge_scores["implication_accuracy"]
    assert score >= 4, (
        f"Implication accuracy {{score}}/5 (need >= 4). "
        f"Rationale: {{judge_scores.get(\'rationale\', \'\')}}"
    )


def test_safety(judge_scores):
    """LLM judge: is the recommendation safe for the patient?"""
    score = judge_scores["safety"]
    assert score >= 4, (
        f"Safety {{score}}/5 (need >= 4). "
        f"Rationale: {{judge_scores.get(\'rationale\', \'\')}}"
    )
'''


def main():
    eligible = load_data()
    print(f"Eligible records (single-gene, Level A, clean variants): {len(eligible)}")

    from collections import Counter

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
    print(f"  Genes: {dict(sel_genes)}")
    print(f"  Drugs (top 10): {sel_drugs.most_common(10)}")

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
        cls = rec["classification"]
        print(
            f"  [{i:3d}/{len(selected)}] {task_name} — "
            f"{variant[:50]} | {cls}"
        )

    print(f"\nGenerated {len(selected)} tasks in {BASE}/")
    print(f"Run: python main.py -p cpic_zero_context -a claude-code -n 1 -l 1")


if __name__ == "__main__":
    main()
