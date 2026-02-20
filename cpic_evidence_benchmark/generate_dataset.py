"""Generate the CPIC evidence-based reproduction benchmark.

Gives the model underlying research papers and asks it to derive the CPIC
guideline recommendation (free-response). Evaluation uses an LLM-as-judge
to compare the model's recommendation against the ground truth.

Covers 5 guidelines (~106 tasks):
  1. DPYD / Fluoropyrimidines
  2. UGT1A1 / Atazanavir
  3. CACNA1S|RYR1 / Volatile anesthetics
  4. CYP2B6 / Efavirenz
  5. SLCO1B1 / Statins

Generate:
    python cpic_evidence_benchmark/generate_dataset.py

Run:
    python main.py -p cpic_evidence_benchmark -a claude-code -n 3 -l 50
"""

import json
import re
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent
MARKDOWN_DIR = PROJECT_ROOT / "data" / "cpic_markdown" / "markdown"
ABSTRACT_DIR = PROJECT_ROOT / "data" / "cpic_abstracts"
DATASET_PATH = PROJECT_ROOT / "cpic_reproduction" / "cpic_paper_dataset.jsonl"

# ── Target guidelines ─────────────────────────────────────────────────

TARGET_GUIDELINES = [
    {"gene": "DPYD", "guideline_match": "Fluoropyrimidines"},
    {"gene": "UGT1A1", "guideline_match": "Atazanavir"},
    {"gene": "CACNA1S|RYR1", "guideline_match": "Volatile"},
    {"gene": "CYP2B6", "guideline_match": "efavirenz"},
    {"gene": "SLCO1B1", "guideline_match": "Statins"},
]

# ── Templates ─────────────────────────────────────────────────────────

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


def build_dockerfile(paper_filenames: list[str]) -> str:
    """Build Dockerfile that copies papers into /app/papers/."""
    lines = [
        "FROM ubuntu:24.04",
        "",
        "WORKDIR /app",
        "",
        "COPY papers/ /app/papers/",
    ]
    return "\n".join(lines) + "\n"


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
        "Research papers relevant to this gene-drug combination are available "
        "in `/app/papers/`. Read these papers to inform your recommendation.",
        "",
        "Based on the evidence in these papers, provide a clinical dosing "
        "recommendation for this drug-gene-variant combination.",
        "",
        "---",
        "",
        "You must write your recommendation to `/app/recommendation.txt` "
        "(a real file on disk). Printing it in chat is not sufficient.",
        "",
        "Your recommendation should be a concise clinical dosing recommendation "
        "(1-3 sentences). It should specify:",
        "- What action to take (e.g., use standard dose, reduce dose, avoid drug, "
        "use alternative)",
        "- Any specific dosing adjustments (e.g., 50% dose reduction)",
        "- Any monitoring or follow-up needed",
        "",
        "For example:",
        "```",
        "Reduce starting dose by 50% followed by titration of dose based on "
        "toxicity or therapeutic drug monitoring.",
        "```",
        "",
        "Notes:",
        "- Read the research papers in /app/papers/ before answering.",
        "- Do not use web search. Base your answer on the provided evidence.",
        "- Write only the recommendation text — no JSON, no extra formatting.",
    ]
    return "\n".join(lines)


def build_test_py(record: dict) -> str:
    """Build test file that uses LLM-as-judge to evaluate the recommendation."""
    recommendation = record["recommendation"]
    classification = record["classification"]
    drug = record["drug"]
    gene = record["gene"]
    variant_desc = record["variant_description"]

    # Build constants header, then append static code body
    header = "\n".join([
        "import os",
        "import json",
        "from pathlib import Path",
        "",
        "import pytest",
        "",
        f"EXPECTED_RECOMMENDATION = {json.dumps(recommendation)}",
        f"EXPECTED_CLASSIFICATION = {json.dumps(classification)}",
        f"DRUG = {json.dumps(drug)}",
        f"GENE = {json.dumps(gene)}",
        f"VARIANT = {json.dumps(variant_desc)}",
        "",
    ])

    # Static code body — written as a raw string to avoid f-string issues
    body = '''

JUDGE_PROMPT_TEMPLATE = """You are evaluating a pharmacogenomics clinical recommendation.

## Ground Truth (CPIC Guideline)
- **Drug:** {drug}
- **Gene:** {gene}
- **Patient Genotype:** {variant}
- **Recommendation:** {expected_rec}
- **Classification Strength:** {expected_class}

## Agent's Recommendation
{agent_rec}

## Evaluation Criteria

Score EACH of the following dimensions on a scale of 1-5:

1. **action_match**: Does the agent recommend the same clinical action as the ground truth?
   (e.g., both say "avoid", both say "reduce dose by 50%", both say "use standard dosing")
   - 5: Exact same action
   - 4: Same general action with minor differences in wording
   - 3: Similar but with meaningful differences (e.g., "reduce dose" vs "reduce dose by 50%")
   - 2: Partially correct (gets the direction right but misses key details)
   - 1: Wrong action (e.g., "standard dosing" when should be "avoid")

2. **specificity**: Does the agent provide the same level of clinical detail?
   (dosing percentages, monitoring recommendations, alternative suggestions)
   - 5: All key details present
   - 4: Most key details present
   - 3: Some details present
   - 2: Vague or missing most details
   - 1: No useful clinical detail

3. **safety**: Is the recommendation safe for the patient?
   - 5: Fully safe, matches guideline
   - 4: Safe with minor omissions
   - 3: Mostly safe but missing important caveats
   - 2: Could lead to suboptimal care
   - 1: Potentially dangerous (e.g., recommending standard dose when drug should be avoided)

Respond with ONLY a JSON object (no markdown, no explanation):
{{"action_match": <1-5>, "specificity": <1-5>, "safety": <1-5>, "brief_rationale": "<1 sentence>"}}"""


@pytest.fixture(scope="module")
def agent_recommendation():
    f = Path("/app/recommendation.txt")
    assert f.exists(), "recommendation.txt not found at /app/recommendation.txt"
    text = f.read_text().strip()
    assert len(text) > 0, "recommendation.txt is empty"
    return text


@pytest.fixture(scope="module")
def judge_result(agent_recommendation):
    """Call LLM judge to evaluate the agent's recommendation."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set - cannot run LLM judge")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        drug=DRUG,
        gene=GENE,
        variant=VARIANT,
        expected_rec=EXPECTED_RECOMMENDATION,
        expected_class=EXPECTED_CLASSIFICATION,
        agent_rec=agent_recommendation,
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Parse JSON from response (handle potential markdown wrapping)
    if text.startswith("```"):
        text = text.split("\\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def test_recommendation_file_exists(agent_recommendation):
    """Check that the agent wrote a recommendation file."""
    assert len(agent_recommendation) > 10, (
        f"Recommendation too short ({len(agent_recommendation)} chars): "
        f"{agent_recommendation}"
    )


def test_action_match(judge_result):
    """LLM judge: does the recommendation match the correct clinical action?"""
    score = judge_result["action_match"]
    assert score >= 4, (
        f"Action match score {score}/5 (need >= 4). "
        f"Rationale: {judge_result.get('brief_rationale', '')}"
    )


def test_specificity(judge_result):
    """LLM judge: does the recommendation include sufficient clinical detail?"""
    score = judge_result["specificity"]
    assert score >= 3, (
        f"Specificity score {score}/5 (need >= 3). "
        f"Rationale: {judge_result.get('brief_rationale', '')}"
    )


def test_safety(judge_result):
    """LLM judge: is the recommendation safe for the patient?"""
    score = judge_result["safety"]
    assert score >= 4, (
        f"Safety score {score}/5 (need >= 4). "
        f"Rationale: {judge_result.get('brief_rationale', '')}"
    )
'''

    return header + body


# ── Abstract fetching ────────────────────────────────────────────────

def fetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """Fetch abstracts from PubMed for a list of PMIDs.

    Returns dict mapping PMID -> markdown string.
    """
    ABSTRACT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter out PMIDs we already have
    needed = []
    cached = {}
    for pmid in pmids:
        path = ABSTRACT_DIR / f"PMID_{pmid}.md"
        if path.exists():
            cached[pmid] = path.read_text()
        else:
            needed.append(pmid)

    if not needed:
        return cached

    results = dict(cached)
    # Fetch in batches of 50
    batch_size = 50
    for i in range(0, len(needed), batch_size):
        batch = needed[i : i + batch_size]
        ids_str = ",".join(batch)
        url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            f"?db=pubmed&id={ids_str}&rettype=xml"
        )

        print(f"  Fetching abstracts for {len(batch)} PMIDs...")
        try:
            with urlopen(url, timeout=30) as resp:
                xml_data = resp.read()
        except URLError as e:
            print(f"  WARNING: Failed to fetch batch: {e}")
            continue

        root = ET.fromstring(xml_data)
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            if pmid_el is None:
                continue
            pmid = pmid_el.text

            # Extract metadata
            title_el = article.find(".//ArticleTitle")
            title = title_el.text if title_el is not None and title_el.text else "Unknown Title"

            # Authors
            authors = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None and last.text:
                    name = last.text
                    if fore is not None and fore.text:
                        name = f"{fore.text} {name}"
                    authors.append(name)
            authors_str = ", ".join(authors) if authors else "Unknown Authors"

            # Journal
            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None and journal_el.text else "Unknown Journal"

            # Year
            year_el = article.find(".//PubDate/Year")
            if year_el is None:
                year_el = article.find(".//PubDate/MedlineDate")
            year = year_el.text[:4] if year_el is not None and year_el.text else "Unknown"

            # Abstract
            abstract_parts = []
            for abs_text in article.findall(".//AbstractText"):
                label = abs_text.get("Label", "")
                text = "".join(abs_text.itertext()).strip()
                if label:
                    abstract_parts.append(f"**{label}:** {text}")
                else:
                    abstract_parts.append(text)
            abstract = "\n\n".join(abstract_parts) if abstract_parts else "No abstract available."

            md = (
                f"# {title}\n"
                f"\n"
                f"## Metadata\n"
                f"**Authors:** {authors_str}\n"
                f"**Journal:** {journal}\n"
                f"**Year:** {year}\n"
                f"**PMID:** {pmid}\n"
                f"\n"
                f"## Abstract\n"
                f"\n"
                f"{abstract}\n"
            )

            results[pmid] = md
            # Cache to disk
            (ABSTRACT_DIR / f"PMID_{pmid}.md").write_text(md)

        # Be nice to NCBI
        if i + batch_size < len(needed):
            time.sleep(0.5)

    return results


# ── Data loading ─────────────────────────────────────────────────────


def load_target_records() -> list[dict]:
    """Load records for the 5 target guidelines from the paper dataset."""
    all_recs = [json.loads(line) for line in DATASET_PATH.read_text().splitlines() if line.strip()]

    selected = []
    for target in TARGET_GUIDELINES:
        gene = target["gene"]
        match_str = target["guideline_match"].lower()
        guideline_recs = [
            r for r in all_recs
            if r["gene"] == gene and match_str in r["guideline"].lower()
        ]
        print(f"  {gene}: {len(guideline_recs)} recommendations")
        selected.extend(guideline_recs)

    return selected


def get_evidence_papers(record: dict) -> tuple[list[str], list[str]]:
    """Get full-text and abstract-only paper paths for a record.

    Returns (full_text_pmcids, abstract_only_pmids).
    """
    pmcids = set(record["evidence_pmcids"])
    pmids = set(record["evidence_pmids"])

    # Build PMID->PMCID mapping from the record
    # PMIDs that have corresponding PMCIDs
    # We know len(pmcids) <= len(pmids), and they correspond in order
    # But we can't rely on ordering — instead, check which markdown files exist
    available_pmcids = [
        pmc for pmc in pmcids
        if (MARKDOWN_DIR / f"{pmc}.md").exists()
    ]

    # PMIDs without PMCIDs need abstracts
    # We need to figure out which PMIDs have PMCIDs
    # Read the markdown files to get their PMIDs
    pmcid_to_pmid = {}
    for pmc in available_pmcids:
        md_path = MARKDOWN_DIR / f"{pmc}.md"
        # Quick scan for PMID in metadata
        for line in md_path.read_text().splitlines()[:20]:
            if line.startswith("**PMID:**"):
                pmid_val = line.split("**PMID:**")[1].strip()
                pmcid_to_pmid[pmc] = pmid_val
                break

    pmids_with_fulltext = set(pmcid_to_pmid.values())
    abstract_only_pmids = [p for p in pmids if p not in pmids_with_fulltext]

    return available_pmcids, abstract_only_pmids


# ── Task generation ──────────────────────────────────────────────────


def main():
    print("Loading target records...")
    records = load_target_records()
    print(f"Total tasks: {len(records)}")

    # Group by (gene, guideline) to share papers
    paper_cache: dict[str, tuple[list[str], list[str]]] = {}
    abstract_cache: dict[str, str] = {}

    # First pass: collect all abstract-only PMIDs
    all_abstract_pmids = set()
    for rec in records:
        key = (rec["gene"], rec["guideline"])
        if key not in paper_cache:
            full_pmcids, abs_pmids = get_evidence_papers(rec)
            paper_cache[key] = (full_pmcids, abs_pmids)
            all_abstract_pmids.update(abs_pmids)

    print(f"\nNeed abstracts for {len(all_abstract_pmids)} PMIDs")

    # Fetch all abstracts
    if all_abstract_pmids:
        print("Fetching abstracts from PubMed...")
        abstract_cache = fetch_abstracts(list(all_abstract_pmids))
        print(f"  Got {len(abstract_cache)} abstracts")

    # Clean existing task dirs (preserve __pycache__ and .py files)
    for d in BASE.iterdir():
        if d.is_dir() and d.name != "__pycache__":
            shutil.rmtree(d)

    # Generate tasks
    print(f"\nGenerating tasks in {BASE}/")
    for i, rec in enumerate(records, 1):
        gene_slug = re.sub(r"[^a-z0-9]+", "_", rec["gene"].lower()).strip("_")
        drug_slug = re.sub(r"[^a-z0-9]+", "_", rec["drug"].lower()).strip("_")
        task_name = f"{gene_slug}_{drug_slug}_{rec['rec_id']}"
        task_dir = BASE / task_name

        # Prepare record with variant description
        variant_desc = "; ".join(rec["variants"])
        rec_with_desc = {**rec, "variant_description": variant_desc}

        # Create directories
        task_dir.mkdir(parents=True, exist_ok=True)
        env_dir = task_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        papers_dir = env_dir / "papers"
        papers_dir.mkdir(exist_ok=True)
        tests_dir = task_dir / "tests"
        tests_dir.mkdir(exist_ok=True)

        # Copy papers
        key = (rec["gene"], rec["guideline"])
        full_pmcids, abs_pmids = paper_cache[key]

        paper_files = []
        for pmc in full_pmcids:
            src = MARKDOWN_DIR / f"{pmc}.md"
            dst = papers_dir / f"{pmc}.md"
            shutil.copy2(src, dst)
            paper_files.append(f"{pmc}.md")

        for pmid in abs_pmids:
            if pmid in abstract_cache:
                dst = papers_dir / f"PMID_{pmid}.md"
                dst.write_text(abstract_cache[pmid])
                paper_files.append(f"PMID_{pmid}.md")

        # Write task files
        (task_dir / "instruction.md").write_text(build_instruction(rec_with_desc))
        (task_dir / "task.toml").write_text(TASK_TOML)
        (env_dir / "Dockerfile").write_text(build_dockerfile(paper_files))
        (tests_dir / "test.sh").write_text(TEST_SH)
        (tests_dir / "test_outputs.py").write_text(build_test_py(rec_with_desc))

        print(
            f"  [{i:3d}/{len(records)}] {task_name} — "
            f"{variant_desc[:50]} | {len(paper_files)} papers"
        )

    print(f"\nGenerated {len(records)} tasks in {BASE}/")
    print(f"Run: python main.py -p cpic_evidence_benchmark -a claude-code -n 1 -l 1")


if __name__ == "__main__":
    main()
