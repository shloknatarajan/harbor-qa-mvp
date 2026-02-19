"""Generate individual Harbor tasks from variant chain questions.

For each chain produced by variant_chains.py, creates 4 separate Harbor tasks
(one per turn/question). Each subsequent task includes the prior question(s)
and gold-standard answer(s) as context so the model can build on previous
answers.

Step 2 (Predictor Inventory) is a multiple-choice question whose options are
assembled using a structured distractor scheme.  For each gene in the paper,
the option pool contains:

  1. The correct predictor(s) for that gene in this paper
  2. One predictor from a *different gene* in the same paper
     (fallback: different gene, any paper)
  3. Two predictors for *this gene* from different papers
     (fallback: any gene, any other paper)

The model uses /app/variant_lookup.py to look up each option and identify
which ones genuinely appear for each gene.

Usage:
    python data/chained-questions/generate_questions.py [--max N]
"""

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

import pandas as pd
import re

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent   # data/chained-questions/
DATA_DIR = BASE.parent                   # data/
PROJECT_ROOT = DATA_DIR.parent           # harbor-qa-mvp/
PAPERS_DIR = DATA_DIR / "papers"
VARIANT_LOOKUP_SRC = BASE / "variant_lookup.py"
RAW_DIR = DATA_DIR / "raw" / "variantAnnotations"

# Chains JSONL produced (or to be produced) by variant_chains.py
CHAINS_FILE = DATA_DIR / "chained_questions" / "variant_allele_chains.jsonl"

# Add chained-questions to sys.path so we can import variant_chains
sys.path.insert(0, str(BASE))

# ---------------------------------------------------------------------------
# Harbor task boilerplate
# ---------------------------------------------------------------------------

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

# Install Python + dependencies required by variant_lookup.py
RUN apt-get update -qq && \\
    apt-get install -y -qq python3 python3-pip curl && \\
    pip3 install --quiet --break-system-packages pydantic requests loguru pandas

COPY papers/ /app/papers/
COPY variant_lookup.py /app/variant_lookup.py
"""

# test.sh runs inside the Docker container after the agent has finished.
# Install variant_lookup.py dependencies so test_outputs.py can import it.
TEST_SH = """\
#!/bin/bash

pip3 install --quiet --break-system-packages pydantic requests loguru pandas

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
source $HOME/.local/bin/env

uvx \\
  --with pytest==8.4.1 \\
  --with pytest-json-ctrf==0.3.5 \\
  --with pydantic \\
  --with requests \\
  --with loguru \\
  --with pandas \\
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

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

# ---------------------------------------------------------------------------
# Shared instruction preamble
# ---------------------------------------------------------------------------

VARIANT_LOOKUP_USAGE = """\
A helper script `/app/variant_lookup.py` is available to look up variant
identifiers (star alleles, haplotypes, rsIDs) and retrieve their canonical
RSID or PharmGKB record. Use it like this:

```python
import sys
sys.path.insert(0, '/app')
from variant_lookup import VariantLookup

vl = VariantLookup()
results = vl.search("CYP2C9*2")   # works for star alleles, rsIDs, names
if results:
    print(results[0])  #This returns information you can leverage to see
    # what each variant looks like in this system
```
"""

# ---------------------------------------------------------------------------
# Gene-predictor index (cross-paper lookup for structured distractors)
# ---------------------------------------------------------------------------

def build_gene_predictor_index() -> dict[str, dict[str, list[str]]]:
    """Return a cross-paper index: gene → {pmid_str → [predictor, ...]}.

    Reads both var_drug_ann.tsv and var_pheno_ann.tsv.  PMIDs are stored as
    plain integer strings (e.g. "12345") to avoid float-formatting issues.
    """
    from collections import defaultdict

    index: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for fname in ("var_drug_ann.tsv", "var_pheno_ann.tsv"):
        fpath = RAW_DIR / fname
        if not fpath.exists():
            continue
        df = pd.read_csv(
            fpath, sep="\t",
            usecols=["Gene", "PMID", "Variant/Haplotypes"],
        )
        for _, row in df.iterrows():
            if pd.isna(row["Gene"]) or pd.isna(row["PMID"]) or pd.isna(row["Variant/Haplotypes"]):
                continue
            gene = str(row["Gene"]).strip()
            pmid = str(int(float(row["PMID"])))
            pred = str(row["Variant/Haplotypes"]).strip()
            if gene and pmid and pred and pred not in index[gene][pmid]:
                index[gene][pmid].append(pred)
    return {g: dict(pmids) for g, pmids in index.items()}


# ---------------------------------------------------------------------------
# MCQ option generation (Step 2) — structured distractor scheme
# ---------------------------------------------------------------------------

def make_q2_options(
    gene_preds: dict[str, list[str]],
    current_pmid: str,
    gene_index: dict[str, dict[str, list[str]]],
    seed: int,
) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
    """Build a shuffled, labeled MCQ option list for Step 2.

    Per gene the pool receives:
      - All correct predictors for that gene (this paper)
      - 1 predictor from a different gene in the same paper
        (fallback: different gene, any paper)
      - 2 predictors for this gene from other papers
        (fallback: any gene, any other paper)

    Returns:
        options         — [(label, variant), ...] shuffled, capped at 26
        correct_by_gene — {gene: [label, ...]} for the verifier
    """
    rng = random.Random(seed)
    all_correct: set[str] = {p for preds in gene_preds.values() for p in preds}

    seen: list[str] = []  # ordered, deduplicated option values

    def _add(v: str) -> bool:
        if v and v not in seen:
            seen.append(v)
            return True
        return False

    # 1. All correct predictors
    for preds in gene_preds.values():
        for p in sorted(preds):
            _add(p)

    # Per-gene distractors
    for gene in sorted(gene_preds):
        # --- cross-gene same-paper ---
        same_paper_pool = sorted(
            p for g, preds in gene_preds.items() if g != gene for p in preds
        )
        if same_paper_pool:
            _add(rng.choice(same_paper_pool))
        else:
            # fallback: different gene, any paper
            fallback = sorted({
                p
                for g, pmids in gene_index.items() if g != gene
                for preds in pmids.values()
                for p in preds
                if p not in all_correct
            })
            if fallback:
                _add(rng.choice(fallback))

        # --- cross-paper same-gene (×2) ---
        same_gene_pool = sorted({
            p
            for pmid, preds in gene_index.get(gene, {}).items()
            if pmid != current_pmid
            for p in preds
            if p not in all_correct
        })
        chosen = rng.sample(same_gene_pool, min(2, len(same_gene_pool)))
        added = sum(_add(p) for p in chosen)

        # fallback for shortfall
        needed = 2 - added
        if needed > 0:
            global_fallback = sorted({
                p
                for _, pmids in gene_index.items()
                for pmid, preds in pmids.items() if pmid != current_pmid
                for p in preds
                if p not in all_correct and p not in seen
            })
            for p in rng.sample(global_fallback, min(needed, len(global_fallback))):
                _add(p)

    # Cap at 26 (A–Z) and shuffle
    pool = seen[:26]
    rng.shuffle(pool)
    labels = [chr(ord("A") + i) for i in range(len(pool))]
    options = list(zip(labels, pool))
    var_to_label = {v: lbl for lbl, v in options}

    correct_by_gene: dict[str, list[str]] = {
        gene: sorted(var_to_label[p] for p in preds if p in var_to_label)
        for gene, preds in gene_preds.items()
    }
    return options, correct_by_gene


# ---------------------------------------------------------------------------
# Context builders (prior Q+A shown in subsequent tasks)
# ---------------------------------------------------------------------------

def _format_prior_context(prior_turns: list[dict]) -> str:
    """Return a markdown block showing all previous Q+A pairs."""
    if not prior_turns:
        return ""
    lines = ["---", "", "## Prior context (from earlier steps in this chain)", ""]
    for t in prior_turns:
        lines.append(f"### Step {t['turn']}: {t['step'].replace('_', ' ').title()}")
        lines.append("")
        lines.append(f"**Question:** {t['question']}")
        lines.append("")
        lines.append("**Gold-standard answer:**")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(t["answer"], indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Instruction builders (one per turn)
# ---------------------------------------------------------------------------

def build_instruction_q1(pmid: str, question: str) -> str:
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

---

## Question (Step 1 of 4): Gene Inventory

{question}

---

Write your answer to `/app/answer.json` as a **JSON array of gene name
strings**, sorted alphabetically. Example:

```json
["CYP2C19", "CYP2C9"]
```
"""


def build_instruction_q2(
    pmid: str,
    question: str,
    prior_turns: list[dict],
    options: list[tuple[str, str]],
) -> str:
    """Build the Step 2 instruction with labeled MCQ options."""
    context = _format_prior_context(prior_turns)
    option_lines = "\n".join(f"- **{lbl})** `{var}`" for lbl, var in options)
    # labels = [lbl for lbl, _ in options]
    # example_gene = "CYP2C9"
    # example_labels = json.dumps(labels[:2]) if len(labels) >= 2 else json.dumps(labels[:1])
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

{context}

---

## Question (Step 2 of 4): Predictor Inventory Per Gene

{question}

Below is a list of candidate genetic predictors (rsIDs, star alleles,
haplotypes, etc.). Some of these appear in the paper; others are distractors.

Use `/app/variant_lookup.py` to look up each option and determine which
predictors are actually evaluated in the paper for each gene from Step 1.

**Options:**

{option_lines}

---

Write your answer to `/app/answer.json` as a **JSON object** mapping each
gene name to a list of the **option labels** (letters) that are evaluated
for that gene in the paper. Example:

```json
{{
  "CYP2D6": ["A", "B"]
  "CYP2C19": ["D"]
}}
```

Only include labels that correspond to predictors genuinely studied for that
gene in this paper. Do not include distractors.
"""


def build_instruction_q3(
    pmid: str,
    question: str,
    prior_turns: list[dict],
) -> str:
    context = _format_prior_context(prior_turns)
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

{context}

---

## Question (Step 3 of 4): Comparison Extraction

{question}

For each predictor from Step 2, extract the explicit A-vs-B comparisons
tested in the paper. Format each comparison as `"LHS vs RHS"` where items on
each side are sorted and joined with ` + `. Use `/app/variant_lookup.py` to
normalize any variant names within comparisons to their canonical RSID.

### Formatting rules

1. **Expand group labels into constituent genotypes.** If the paper uses
   shorthand like "carriers", "*3 carriers", "variant allele carriers", or
   "non-carriers", decompose them into every individual genotype they
   represent. For example:
   - "*3 carriers" → `*1/*3 + *3/*3`
   - "non-carriers" (of *3) → `*1/*1`
   - "T allele carriers" → `CT + TT`

2. **Each side of `vs` is a sorted, `+`-joined list of genotypes** — never
   a group label or prose description.

3. **SNP comparisons use allele pairs** (e.g. `T vs C`), not experimental
   group descriptions (e.g. "homozygous mutant vs WT").

4. **Sort genotypes lexicographically within each side. The LHS should be the 
subject allele(s)/genotype(s) (the "Alleles" field) and the RHS should be the 
comparator allele(s)/genotype(s) (the "Comparison Allele(s) or Genotype(s)" field)
, matching the order as presented in the paper.

5. **Always express comparisons using nucleotide alleles only (e.g. A, T, C, G). 
Do not use amino acid names, protein change notation (e.g. Lys, Gln, Arg, Pro), 
or any other representation. Use variant_lookup.py to find the canonical 
nucleotide alleles for each variant if the paper does not report them directly.

---

Write your answer to `/app/answer.json` as a **JSON object** mapping each
predictor identifier (string) to a sorted list of comparison strings. Example:
```json
{{
  "rs1799853": ["*1/*1 vs *1/*3 + *3/*3"],
  "rs4244285": ["*1 vs *17"],
  "rs118192161": ["C vs T"]
}}
```
"""


def build_instruction_q4(
    pmid: str,
    question: str,
    prior_turns: list[dict],
) -> str:
    context = _format_prior_context(prior_turns)
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

{context}

---

## Question (Step 4 of 4): Evidence Selection

{question}

Identify which predictor–comparison pair from Step 3 has the smallest
reported p-value. If multiple pairs are tied, list all tied entries.
Use `/app/variant_lookup.py` to normalize any variant names to their
canonical RSID.

---

Write your answer to `/app/answer.json` as a **JSON string** in the format:

```
"<predictor> (<comparison>)"
```

or, if tied:

```
"<predictor1> (<comp1>), <predictor2> (<comp2>)"
```

Example:

```json
"rs1799853 (rs1799853 vs rs1057910)"
```
"""


# ---------------------------------------------------------------------------
# Test (verifier) builders — one per turn
# ---------------------------------------------------------------------------

_TEST_HEADER = '''\
"""Verifier for variant-chain Harbor task."""
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# RSID normalizer (best-effort; falls back to identity)
# ---------------------------------------------------------------------------

def _make_normalizer():
    try:
        sys.path.insert(0, "/app")
        from variant_lookup import VariantLookup
        vl = VariantLookup()

        def normalize(v: str) -> str:
            v = v.strip()
            results = vl.search(v)
            return results[0].name.strip() if results else v

        return normalize
    except Exception:
        return str.strip


_normalize = _make_normalizer()

'''


def build_test_q1(expected_genes: list[str]) -> str:
    lines = [_TEST_HEADER]
    genes_repr = json.dumps(sorted(expected_genes))
    lines.append(f"EXPECTED_GENES = {genes_repr}\n\n\n")
    lines.append("@pytest.fixture(scope='module')\n")
    lines.append("def answer():\n")
    lines.append("    f = Path('/app/answer.json')\n")
    lines.append("    assert f.exists(), 'answer.json not found at /app/answer.json'\n")
    lines.append("    data = json.loads(f.read_text())\n")
    lines.append("    assert isinstance(data, list), 'Expected a JSON array of gene names'\n")
    lines.append("    return [str(g).strip().upper() for g in data]\n\n\n")
    lines.append("@pytest.fixture(scope='module')\n")
    lines.append("def answer_upper(answer):\n")
    lines.append("    return {g.upper() for g in answer}\n\n\n")
    for gene in sorted(expected_genes):
        safe = gene.replace("-", "_").replace(" ", "_")
        gene_upper = json.dumps(gene.upper())
        msg = json.dumps(f"Gene {gene!r} missing from answer")
        lines.append(f"def test_gene_{safe}(answer_upper):\n")
        lines.append(
            f"    assert {gene_upper} in answer_upper, "
            f"{msg}\n\n\n"
        )
    return "".join(lines)


def build_test_q2_mcq(correct_by_gene: dict[str, list[str]]) -> str:
    """Verifier for Step 2 MCQ: checks the model selected the right option labels."""
    correct_repr = json.dumps(
        {g: sorted(ls) for g, ls in sorted(correct_by_gene.items())}, indent=2
    )
    lines = [_TEST_HEADER]
    lines.append(f"CORRECT_BY_GENE = {correct_repr}\n\n\n")
    lines.append("@pytest.fixture(scope='module')\n")
    lines.append("def answer():\n")
    lines.append("    f = Path('/app/answer.json')\n")
    lines.append("    assert f.exists(), 'answer.json not found at /app/answer.json'\n")
    lines.append("    data = json.loads(f.read_text())\n")
    lines.append("    assert isinstance(data, dict), 'Expected a JSON object (gene -> [labels])'\n")
    lines.append("    # Normalise: uppercase labels, uppercase gene keys\n")
    lines.append("    return {k.upper(): sorted([str(v).upper() for v in vs]) for k, vs in data.items()}\n\n\n")
    for gene, labels in sorted(correct_by_gene.items()):
        safe_gene = re.sub(r'[^a-zA-Z0-9]+', '_', gene).strip('_')
        gene_repr = json.dumps(gene.upper())
        correct_set = json.dumps(sorted([l.upper() for l in labels]))
        msg = f"Expected exactly {correct_set} for gene '{gene}'. Got: {{got}}"
        lines.append(f"def test_{safe_gene}(answer):\n")
        lines.append(f"    got = sorted(answer.get({gene_repr}, []))\n")
        lines.append(f"    assert got == {correct_set}, (\n")
        lines.append(f"        f{json.dumps(msg)}\n")
        lines.append("    )\n\n\n")
    return "".join(lines)


def build_test_q3(expected: dict[str, list[str]]) -> str:
    import re
    expected_repr = json.dumps(
        {p: sorted(cs) for p, cs in sorted(expected.items())}, indent=2
    )
    lines = [_TEST_HEADER]
    lines.append(f"EXPECTED = {expected_repr}\n\n")
    lines.append("""
import re

def _is_nucleotide_comparison(comp: str) -> bool:
    tokens = [t for t in re.findall(r'[A-Za-z]+', comp) if t.lower() != 'vs']
    return bool(tokens) and all(set(t.upper()) <= {'A', 'T', 'C', 'G'} for t in tokens)

def _complement(comp: str) -> str:
    return comp.translate(str.maketrans('ATCGatcg', 'TAGCtagc'))

def _comparison_matches(expected: str, got: str) -> bool:
    if expected == got:
        return True
    if _is_nucleotide_comparison(expected) and _complement(expected) == got:
        return True
    return False

def _any_comparison_matches(expected: str, raw_comps: list) -> bool:
    return any(_comparison_matches(expected, got) for got in raw_comps)


""")
    lines.append("@pytest.fixture(scope='module')\n")
    lines.append("def answer():\n")
    lines.append("    f = Path('/app/answer.json')\n")
    lines.append("    assert f.exists(), 'answer.json not found at /app/answer.json'\n")
    lines.append("    data = json.loads(f.read_text())\n")
    lines.append("    assert isinstance(data, dict), 'Expected a JSON object (predictor -> [comparisons])'\n")
    lines.append("    return data\n\n\n")
    for predictor, comparisons in sorted(expected.items()):
        safe_pred = re.sub(r'[^a-zA-Z0-9]+', '_', predictor).strip('_')
        for comp in sorted(comparisons):
            pred_json = json.dumps(predictor)
            comp_json = json.dumps(comp)
            safe_comp = re.sub(r'[^a-zA-Z0-9]+', '_', comp).strip('_')
            lines.append(f"def test_{safe_pred}_{safe_comp}(answer):\n")
            lines.append(f"    raw_comps = answer.get({pred_json}, [])\n")
            lines.append(f"    assert _any_comparison_matches({comp_json}, raw_comps), (\n")
            lines.append(
                f"        f'Comparison {comp_json} (or its strand complement) "
                f"missing for predictor {pred_json}. Got: {{raw_comps}}'\n"
            )
            lines.append("    )\n\n\n")
    return "".join(lines)


def build_test_q4(expected_answer: str) -> str:
    lines = [_TEST_HEADER]
    lines.append(f"EXPECTED = {json.dumps(expected_answer)}\n\n\n")
    lines.append("@pytest.fixture(scope='module')\n")
    lines.append("def answer():\n")
    lines.append("    f = Path('/app/answer.json')\n")
    lines.append("    assert f.exists(), 'answer.json not found at /app/answer.json'\n")
    lines.append("    data = json.loads(f.read_text())\n")
    lines.append("    if isinstance(data, list):\n")
    lines.append("        return ', '.join(str(x) for x in data)\n")
    lines.append("    return str(data).strip()\n\n\n")
    lines.append("def test_evidence_selection(answer):\n")
    lines.append("    def norm_tokens(s):\n")
    lines.append("        tokens = s.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()\n")
    lines.append("        return ' '.join(_normalize(t) if not t.lower().startswith('vs') else t\n")
    lines.append("                        for t in tokens)\n")
    lines.append("    assert answer == EXPECTED or norm_tokens(answer) == norm_tokens(EXPECTED), (\n")
    lines.append("        f'Expected: {EXPECTED!r}\\nGot: {answer!r}'\n")
    lines.append("    )\n")
    return "".join(lines)


# ---------------------------------------------------------------------------
# Task directory builder
# ---------------------------------------------------------------------------

def build_task(
    task_dir: Path,
    chain: dict,
    turn_idx: int,
    gene_index: dict[str, dict[str, list[str]]],
) -> None:
    """Write all files for one Harbor task (one turn of a chain)."""
    turns = chain["turns"]
    current_turn = turns[turn_idx]
    prior_turns = turns[:turn_idx]
    pmid = chain["pmid"]
    pmc_id = chain["pmc_id"]
    turn_num = current_turn["turn"]

    # Build instruction and test code for this turn
    if turn_num == 1:
        instruction = build_instruction_q1(pmid, current_turn["question"])
        test_py = build_test_q1(current_turn["answer"])

    elif turn_num == 2:
        gene_preds: dict[str, list[str]] = current_turn["answer"]
        seed = int(chain["chain_id"].split("_")[-1])
        options, correct_by_gene = make_q2_options(gene_preds, pmid, gene_index, seed)
        instruction = build_instruction_q2(
            pmid, current_turn["question"], prior_turns, options
        )
        test_py = build_test_q2_mcq(correct_by_gene)

    elif turn_num == 3:
        instruction = build_instruction_q3(
            pmid, current_turn["question"], prior_turns
        )
        raw_answer = current_turn["answer"]
        q3_expected = raw_answer if isinstance(raw_answer, dict) else {}
        test_py = build_test_q3(q3_expected)

    else:  # turn_num == 4
        instruction = build_instruction_q4(
            pmid, current_turn["question"], prior_turns
        )
        raw_answer = current_turn["answer"]
        q4_expected = raw_answer if isinstance(raw_answer, str) else ""
        test_py = build_test_q4(q4_expected)

    # Write task directory structure
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "instruction.md").write_text(instruction)
    (task_dir / "task.toml").write_text(TASK_TOML)

    env_dir = task_dir / "environment"
    env_dir.mkdir(exist_ok=True)
    (env_dir / "Dockerfile").write_text(DOCKERFILE)

    papers_dir = env_dir / "papers"
    papers_dir.mkdir(exist_ok=True)
    paper_src = PAPERS_DIR / f"{pmc_id}.md"
    if paper_src.exists():
        shutil.copy2(paper_src, papers_dir / f"{pmc_id}.md")

    if VARIANT_LOOKUP_SRC.exists():
        shutil.copy2(VARIANT_LOOKUP_SRC, env_dir / "variant_lookup.py")

    tests_dir = task_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test.sh").write_text(TEST_SH)
    (tests_dir / "test_outputs.py").write_text(test_py)


# ---------------------------------------------------------------------------
# Chain loading
# ---------------------------------------------------------------------------

def load_chains() -> list[dict]:
    """Load chains from the pre-generated JSONL, or generate them on the fly."""
    if CHAINS_FILE.exists():
        print(f"Loading chains from {CHAINS_FILE}")
        chains = []
        with open(CHAINS_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    chains.append(json.loads(line))
        return chains

    print(f"Chains file not found at {CHAINS_FILE}; generating from raw data…")
    from variant_chains import generate_chains
    chains, skip_paper, skip_pval, skip_valid = generate_chains()
    print(
        f"  Generated {len(chains)} chains "
        f"(skipped: {skip_paper} no-paper, {skip_pval} no-pval, "
        f"{skip_valid} validation)"
    )
    CHAINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHAINS_FILE, "w") as f:
        for c in chains:
            f.write(json.dumps(c) + "\n")
    print(f"  Cached to {CHAINS_FILE}")
    return chains


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max", type=int, default=None, metavar="N",
        help="Maximum number of chains to process (default: all)"
    )
    args = parser.parse_args()

    chains = load_chains()
    if args.max is not None:
        chains = chains[: args.max]

    print("Building gene-predictor index for structured distractors…")
    gene_index = build_gene_predictor_index()
    print(f"  {len(gene_index)} genes indexed across all papers")

    # Remove any existing task dirs that match our naming pattern
    for d in BASE.iterdir():
        if d.is_dir() and "_q" in d.name:
            shutil.rmtree(d)

    total_tasks = 0
    for chain in chains:
        chain_id = chain["chain_id"]
        pmc_id = chain["pmc_id"]
        num_turns = chain["num_turns"]

        paper_src = PAPERS_DIR / f"{pmc_id}.md"
        if not paper_src.exists():
            continue

        for turn_idx in range(num_turns):
            turn_num = chain["turns"][turn_idx]["turn"]
            task_name = f"{chain_id}_q{turn_num}"
            task_dir = BASE / task_name
            build_task(task_dir, chain, turn_idx, gene_index)
            total_tasks += 1

        print(f"  {chain_id} ({pmc_id}) — {num_turns} tasks")

    print(f"\nGenerated {total_tasks} Harbor tasks in {BASE}/")


if __name__ == "__main__":
    main()
