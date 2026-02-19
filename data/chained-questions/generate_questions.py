"""Generate individual Harbor tasks from variant chain questions.

New structure (5 tasks per chain):
  Q1: Predictor Inventory Per Gene (MCQ) — gene list embedded as context
  Q2: Significance Judgment              — comparison pairs from old Q3 as static context
  Q3: Phenotype Category
  Q4: Allele Frequency Extraction        — study_parameters.tsv + README.pdf provided
  Q5: Evidence Selection                 — comparison pairs as static context

Original Q1 (Gene Inventory) and Q3 (Comparison Extraction) are no longer
graded tasks; their gold-standard data is embedded as context where needed.

Usage:
    python data/chained-questions/generate_questions.py [--max N]
"""

import argparse
import json
import random
import shutil
import sys
from collections import defaultdict
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
README_PDF_SRC = RAW_DIR / "README.pdf"

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
# PGx annotation index (significance + phenotype category by PMID+predictor)
# ---------------------------------------------------------------------------

def _normalize_pmid(raw) -> str:
    """Convert float or string PMID to plain integer string."""
    try:
        return str(int(float(str(raw).strip())))
    except (ValueError, TypeError):
        return str(raw).strip()


def build_pgx_index() -> dict[str, dict[str, list[dict]]]:
    """Return index: pmid → {predictor → [{significance, phenotype_category, annotation_id}]}.

    Reads var_drug_ann.tsv, var_pheno_ann.tsv, and var_fa_ann.tsv.
    """
    index: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for fname in ("var_drug_ann.tsv", "var_pheno_ann.tsv", "var_fa_ann.tsv"):
        fpath = RAW_DIR / fname
        if not fpath.exists():
            continue
        df = pd.read_csv(
            fpath, sep="\t",
            usecols=["Variant Annotation ID", "Variant/Haplotypes", "PMID",
                     "Phenotype Category", "Significance"],
        )
        for _, row in df.iterrows():
            if pd.isna(row["PMID"]) or pd.isna(row["Variant/Haplotypes"]):
                continue
            pmid = _normalize_pmid(row["PMID"])
            pred = str(row["Variant/Haplotypes"]).strip()
            sig_raw = row["Significance"]
            pheno_raw = row["Phenotype Category"]
            entry = {
                "significance": str(sig_raw).strip().lower() if not pd.isna(sig_raw) else "not stated",
                "phenotype_category": str(pheno_raw).strip() if not pd.isna(pheno_raw) else "other",
                "annotation_id": int(row["Variant Annotation ID"]),
            }
            index[pmid][pred].append(entry)
    return {pmid: dict(preds) for pmid, preds in index.items()}


def build_freq_index() -> dict[int, dict]:
    """Return index: annotation_id → {allele_cases, freq_cases, allele_controls, freq_controls}."""
    fpath = RAW_DIR / "study_parameters.tsv"
    if not fpath.exists():
        return {}
    df = pd.read_csv(fpath, sep="\t")
    index: dict[int, dict] = {}
    for _, row in df.iterrows():
        ann_id = int(row["Variant Annotation ID"])
        if ann_id in index:
            continue  # keep first entry per annotation_id
        index[ann_id] = {
            "freq_cases": float(row["Frequency In Cases"]) if not pd.isna(row["Frequency In Cases"]) else None,
            "allele_cases": str(row["Allele Of Frequency In Cases"]).strip()
                            if not pd.isna(row["Allele Of Frequency In Cases"]) else None,
            "freq_controls": float(row["Frequency In Controls"]) if not pd.isna(row["Frequency In Controls"]) else None,
            "allele_controls": str(row["Allele Of Frequency In Controls"]).strip()
                               if not pd.isna(row["Allele Of Frequency In Controls"]) else None,
        }
    return index


# ---------------------------------------------------------------------------
# Gold-standard answer computation for new questions
# ---------------------------------------------------------------------------

def compute_sig_judgment_answer(
    pmid: str,
    all_predictors: list[str],
    q3_comps: dict[str, list[str]],
    pgx_index: dict,
) -> dict[str, dict[str, str]]:
    """Return {predictor: {comparison: "yes/no/not stated"}} from TSV Significance field."""
    result: dict[str, dict[str, str]] = {}
    pred_data = pgx_index.get(pmid, {})
    for pred in all_predictors:
        entries = pred_data.get(pred, [])
        sig = entries[0]["significance"] if entries else "not stated"
        # Normalise to the three canonical values
        if sig not in ("yes", "no", "not stated"):
            sig = "not stated"
        comps = q3_comps.get(pred, [])
        result[pred] = {comp: sig for comp in comps}
    return result


def compute_pheno_cat_answer(
    pmid: str,
    all_predictors: list[str],
    pgx_index: dict,
) -> dict[str, list[str]]:
    """Return {predictor: [sorted phenotype categories]} from TSV Phenotype Category field."""
    result: dict[str, list[str]] = {}
    pred_data = pgx_index.get(pmid, {})

    def _normalise_cat(c: str) -> str:
        c = c.strip()
        # Canonical capitalisation from the README options list
        mapping = {
            "metabolism/pk": "metabolism/PK",
            "efficacy": "efficacy",
            "toxicity": "toxicity",
            "dosage": "dosage",
            "pd": "PD",
            "other": "other",
        }
        return mapping.get(c.lower(), c)

    for pred in all_predictors:
        entries = pred_data.get(pred, [])
        if not entries:
            result[pred] = ["other"]
        else:
            cats = sorted({_normalise_cat(e["phenotype_category"]) for e in entries})
            result[pred] = cats
    return result


def compute_allele_freq_answer(
    pmid: str,
    all_predictors: list[str],
    pgx_index: dict,
    freq_index: dict,
) -> dict[str, dict | None]:
    """Return {predictor: {allele, freq_cases, freq_controls}} or -1 from study_parameters."""
    result: dict[str, dict | None] = {}
    pred_data = pgx_index.get(pmid, {})
    for pred in all_predictors:
        entries = pred_data.get(pred, [])
        freq_entry = None
        for e in entries:
            fe = freq_index.get(e["annotation_id"], {})
            if fe.get("freq_cases") is not None or fe.get("freq_controls") is not None:
                freq_entry = fe
                break
        if freq_entry:
            allele = freq_entry.get("allele_cases") or freq_entry.get("allele_controls")
            result[pred] = {
                "allele": allele,
                "freq_cases": freq_entry.get("freq_cases"),
                "freq_controls": freq_entry.get("freq_controls"),
            }
        else:
            result[pred] = None
    return result


# ---------------------------------------------------------------------------
# MCQ option generation (Q1) — structured distractor scheme
# ---------------------------------------------------------------------------

def make_q2_options(
    gene_preds: dict[str, list[str]],
    current_pmid: str,
    gene_index: dict[str, dict[str, list[str]]],
    seed: int,
) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
    """Build a shuffled, labeled MCQ option list for Step 1.

    Per gene the pool receives:
      - All correct predictors for that gene (this paper)
      - 1 predictor from a *different gene* in the same paper
        (fallback: different gene, any paper)
      - 2 predictors for *this gene* from different papers
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
# Context builders
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


def _format_comparison_context(q3_comps: dict[str, list[str]]) -> str:
    """Return a static markdown block showing predictor–comparison pairs."""
    if not q3_comps:
        return ""
    lines = [
        "## Predictor–comparison pairs from this paper",
        "",
        "The following predictor–comparison pairs have been identified in this paper:",
        "",
        "```json",
        json.dumps(q3_comps, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Instruction builders — one per new question (1–5)
# ---------------------------------------------------------------------------

def build_instruction_new_q1(
    pmid: str,
    gene_list: list[str],
    options: list[tuple[str, str]],
) -> str:
    """Step 1 of 5: Predictor Inventory Per Gene (MCQ). Gene list embedded."""
    gene_str = ", ".join(sorted(gene_list))
    option_lines = "\n".join(f"- **{lbl})** `{var}`" for lbl, var in options)
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

**Genes studied in this paper (PMID {pmid}):** {gene_str}

---

## Question (Step 1 of 5): Predictor Inventory Per Gene

For each gene listed above, identify the genetic predictors explicitly
evaluated in the paper (e.g., rsID/variant, star allele/haplotype,
diplotype/genotype, or metabolizer/phenotype group).

Below is a list of candidate genetic predictors (rsIDs, star alleles,
haplotypes, etc.). Some of these appear in the paper; others are distractors.

Use `/app/variant_lookup.py` to look up each option and determine which
predictors are actually evaluated in the paper for each gene.

**Options:**

{option_lines}

---

Write your answer to `/app/answer.json` as a **JSON object** mapping each
gene name to a list of the **option labels** (letters) that are evaluated
for that gene in the paper. Example:

```json
{{
  "CYP2D6": ["A", "B"],
  "CYP2C19": ["D"]
}}
```

Only include labels that correspond to predictors genuinely studied for that
gene in this paper. Do not include distractors.
"""


def build_instruction_sig_judgment(
    pmid: str,
    prior_turns: list[dict],
    q3_comps: dict[str, list[str]],
) -> str:
    """Step 2 of 5: Significance Judgment."""
    context = _format_prior_context(prior_turns)
    comp_context = _format_comparison_context(q3_comps)
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

{context}

{comp_context}

---

## Question (Step 2 of 5): Significance Judgment

For each predictor–comparison pair listed above, determine whether
the authors reported a statistically significant association.

**Options:** `"yes"`, `"no"`, `"not stated"`

**Rules:**
- `"yes"` = authors explicitly state significance OR report p < 0.05
- `"no"` = authors explicitly state no significant association OR report p ≥ 0.05
- `"not stated"` = no p-value reported and authors make no claim about significance

---

Write your answer to `/app/answer.json`:

```json
{{
  "rs1799853": {{
    "AA vs AG": "yes",
    "AA vs GG": "no"
  }}
}}
```
"""


def build_instruction_pheno_cat(
    pmid: str,
    prior_turns: list[dict],
) -> str:
    """Step 3 of 5: Phenotype Category."""
    context = _format_prior_context(prior_turns)
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

{context}

---

## Question (Step 3 of 5): Phenotype Category

For each predictor identified in Step 1, classify the **clinical outcome**
that the genetic association targets in this paper. Focus on what disease,
symptom, or patient outcome the predictor is being associated with — not on
any mechanistic assay data (e.g. in vitro binding studies) that may also
appear in the paper.

**Options:** `"efficacy"`, `"toxicity"`, `"dosage"`, `"metabolism/PK"`, `"PD"`, `"other"`

**Rules:**
- `"efficacy"` = treatment response, remission, survival, therapeutic outcome
- `"toxicity"` = adverse drug reactions, side effects, drug-induced injury,
  addiction/dependence, drug abuse liability
- `"dosage"` = dose requirements, dose adjustments
- `"metabolism/PK"` = drug concentration, clearance, half-life, AUC, Cmax,
  concentration-to-dose ratio
- `"PD"` = clinical pharmacodynamic endpoints measured in patients (e.g.
  pain score change, biomarker response in vivo); do NOT use for in vitro
  receptor binding or cell-line assays
- `"other"` = none of the above

If a single paper tests BOTH efficacy and toxicity outcomes for the same
predictor, list each separately.

---

Write your answer to `/app/answer.json`:

```json
{{
  "rs1799853": ["metabolism/PK", "toxicity"],
  "rs717620": ["efficacy"]
}}
```
"""


def build_instruction_allele_freq(
    pmid: str,
    prior_turns: list[dict],
) -> str:
    """Step 4 of 5: Allele Frequency Extraction."""
    context = _format_prior_context(prior_turns)
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

{context}

---

## Question (Step 4 of 5): Allele Frequency Extraction

For each predictor identified in Step 1, extract the allele frequencies
reported in the paper for cases and controls.

For each predictor, provide:
- `"allele"`: which allele the frequency refers to
- `"freq_cases"`: frequency in cases (as a decimal, e.g. 0.25 not 25%)
- `"freq_controls"`: frequency in controls (as a decimal)

If frequencies are reported only as genotype counts, calculate the allele
frequency and show your work. If frequencies are not reported for a
given predictor, return `-1`.

---

Write your answer to `/app/answer.json`:

```json
{{
  "rs2273697": {{
    "allele": "A",
    "freq_cases": 0.18,
    "freq_controls": 0.12
  }},
  "rs1799752": -1
}}
```
"""


def build_instruction_new_q5(
    pmid: str,
    prior_turns: list[dict],
    q3_comps: dict[str, list[str]],
) -> str:
    """Step 5 of 5: Evidence Selection (smallest p-value comparison)."""
    context = _format_prior_context(prior_turns)
    comp_context = _format_comparison_context(q3_comps)
    return f"""\
You are a pharmacogenomics researcher analyzing a scientific paper.

The paper (PMID {pmid}) is available in `/app/papers/` — read it to answer
the question below.

{VARIANT_LOOKUP_USAGE}

{context}

{comp_context}

---

## Question (Step 5 of 5): Evidence Selection

Among the predictor–comparison pairs listed above, which has the smallest
p-value reported for the **association between the predictor and the clinical
or pharmacological outcome** (e.g. case vs control, responder vs
non-responder, high-dose vs low-dose group)? If multiple comparisons are
tied for the smallest p-value, list all tied comparisons.

**Important:** Use only the p-value for the direct predictor–outcome
association test. Do not use p-values from incidental analyses such as
allele frequency differences across ethnic groups 
or other population-level comparisons.

If multiple p-values are reported for the same predictor–comparison pair
(e.g. subgroup analyses), use the smallest among them.

If multiple pairs are tied, list all tied entries.
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
# Test (verifier) builders — one per question
# ---------------------------------------------------------------------------

_TEST_HEADER = '''\
"""Verifier for variant-chain Harbor task."""
import json
import sys
from pathlib import Path

import pytest
'''


def build_test_q2_mcq(correct_by_gene: dict[str, list[str]]) -> str:
    """Verifier for Step 1 (Predictor Inventory) MCQ."""
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


def build_test_sig_judgment(expected: dict[str, dict[str, str]]) -> str:
    """Verifier for Step 2 (Significance Judgment)."""
    expected_repr = json.dumps(
        {p: {c: s for c, s in sorted(cs.items())} for p, cs in sorted(expected.items())},
        indent=2,
    )
    lines = [_TEST_HEADER]
    lines.append(f"EXPECTED = {expected_repr}\n\n")
    lines.append("""\
import re as _re

def _normalize_sig(s: str) -> str:
    return s.strip().lower()

def _find_sig_for_comparison(answer_pred: dict, expected_comp: str) -> str | None:
    \"\"\"Find significance in model answer, tolerating analysis-type suffixes.\"\"\"
    # Exact match
    if expected_comp in answer_pred:
        return _normalize_sig(answer_pred[expected_comp])
    # Case-insensitive exact match
    for k, v in answer_pred.items():
        if k.lower() == expected_comp.lower():
            return _normalize_sig(v)
    # Strip parenthetical suffix from model key (e.g. "AA vs AG (univariate)")
    for k, v in answer_pred.items():
        base_k = _re.sub(r'\\s*\\(.*?\\)\\s*$', '', k).strip()
        if base_k.lower() == expected_comp.lower():
            return _normalize_sig(v)
    return None

""")
    lines.append("@pytest.fixture(scope='module')\n")
    lines.append("def answer():\n")
    lines.append("    f = Path('/app/answer.json')\n")
    lines.append("    assert f.exists(), 'answer.json not found at /app/answer.json'\n")
    lines.append("    data = json.loads(f.read_text())\n")
    lines.append("    assert isinstance(data, dict), 'Expected a JSON object'\n")
    lines.append("    return data\n\n\n")
    for predictor, comparisons in sorted(expected.items()):
        safe_pred = re.sub(r'[^a-zA-Z0-9]+', '_', predictor).strip('_')
        pred_repr = json.dumps(predictor)
        for comp, sig in sorted(comparisons.items()):
            safe_comp = re.sub(r'[^a-zA-Z0-9]+', '_', comp).strip('_')
            fn_name = f"test_sig_{safe_pred}_{safe_comp}"[:80]
            comp_repr = json.dumps(comp)
            sig_repr = json.dumps(sig.lower())
            lines.append(f"def {fn_name}(answer):\n")
            lines.append(f"    pred_data = answer.get({pred_repr}, {{}})\n")
            lines.append(f"    got_sig = _find_sig_for_comparison(pred_data, {comp_repr})\n")
            lines.append(f"    assert got_sig == {sig_repr}, (\n")
            lines.append(
                f"        f'Expected significance {sig_repr} for predictor {pred_repr} '\n"
                f"        f'comparison {comp_repr}. Got: {{got_sig!r}} from {{pred_data}}'\n"
            )
            lines.append("    )\n\n\n")
    return "".join(lines)


def build_test_pheno_cat(expected: dict[str, list[str]]) -> str:
    """Verifier for Step 3 (Phenotype Category)."""
    expected_repr = json.dumps(
        {p: sorted(cs) for p, cs in sorted(expected.items())}, indent=2
    )
    lines = [_TEST_HEADER]
    lines.append(f"EXPECTED = {expected_repr}\n\n")
    lines.append("""\
# Canonical lowercase keys for comparison
_PHENO_ALIASES = {
    "metabolism/pk": ["metabolism/pk", "metabolism/pharmacokinetics", "pk"],
    "pd": ["pd", "pharmacodynamic", "pharmacodynamics"],
    "efficacy": ["efficacy"],
    "toxicity": ["toxicity"],
    "dosage": ["dosage"],
    "other": ["other"],
}

def _normalise_cat(c: str) -> str:
    c = c.strip().lower()
    for canonical, alts in _PHENO_ALIASES.items():
        if c in alts:
            return canonical
    return c

""")
    lines.append("@pytest.fixture(scope='module')\n")
    lines.append("def answer():\n")
    lines.append("    f = Path('/app/answer.json')\n")
    lines.append("    assert f.exists(), 'answer.json not found at /app/answer.json'\n")
    lines.append("    data = json.loads(f.read_text())\n")
    lines.append("    assert isinstance(data, dict), 'Expected a JSON object'\n")
    lines.append("    return {k: [_normalise_cat(c) for c in v] for k, v in data.items()}\n\n\n")
    for predictor, categories in sorted(expected.items()):
        safe_pred = re.sub(r'[^a-zA-Z0-9]+', '_', predictor).strip('_')
        pred_repr = json.dumps(predictor)
        # normalise expected cats to lowercase for comparison
        expected_cats_norm = sorted([c.lower().replace("metabolism/pk", "metabolism/pk") for c in categories])
        # use the _normalise_cat mapping
        norm_map = {
            "metabolism/PK": "metabolism/pk",
            "PD": "pd",
            "efficacy": "efficacy",
            "toxicity": "toxicity",
            "dosage": "dosage",
            "other": "other",
        }
        normalised = sorted([norm_map.get(c, c.lower()) for c in categories])
        cats_repr = json.dumps(normalised)
        lines.append(f"def test_pheno_cat_{safe_pred}(answer):\n")
        lines.append(f"    got = sorted(answer.get({pred_repr}, []))\n")
        lines.append(f"    for cat in {cats_repr}:\n")
        lines.append(f"        assert cat in got, (\n")
        lines.append(
            f"            f'Expected category {{cat!r}} for predictor {pred_repr}. Got: {{got}}'\n"
        )
        lines.append("        )\n\n\n")
    return "".join(lines)


def build_test_allele_freq(expected: dict[str, dict | None]) -> str:
    """Verifier for Step 4 (Allele Frequency Extraction)."""
    serializable = {
        p: e if e is not None else -1
        for p, e in sorted(expected.items())
    }
    expected_repr = json.dumps(serializable, indent=2)
    lines = [_TEST_HEADER]
    lines.append(f"EXPECTED = {expected_repr}\n\n")
    lines.append("""\
_TOLERANCE = 0.01  # 1 percentage-point tolerance for frequency values

def _close(a, b) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= _TOLERANCE
    except (TypeError, ValueError):
        return False
""")
    lines.append("@pytest.fixture(scope='module')\n")
    lines.append("def answer():\n")
    lines.append("    f = Path('/app/answer.json')\n")
    lines.append("    assert f.exists(), 'answer.json not found at /app/answer.json'\n")
    lines.append("    data = json.loads(f.read_text())\n")
    lines.append("    assert isinstance(data, dict), 'Expected a JSON object'\n")
    lines.append("    return data\n\n\n")
    for predictor, freq_data in sorted(expected.items()):
        safe_pred = re.sub(r'[^a-zA-Z0-9]+', '_', predictor).strip('_')
        pred_repr = json.dumps(predictor)
        if freq_data is None:
            lines.append(f"def test_allele_freq_{safe_pred}(answer):\n")
            lines.append(f"    got = answer.get({pred_repr})\n")
            lines.append(f"    assert got == -1, (\n")
            lines.append(
                f"        f'Expected -1 for predictor {pred_repr}. Got: {{got}}'\n"
            )
            lines.append("    )\n\n\n")
        else:
            allele = freq_data.get("allele")
            fc = freq_data.get("freq_cases")
            fctrl = freq_data.get("freq_controls")
            lines.append(f"def test_allele_freq_{safe_pred}(answer):\n")
            lines.append(f"    got = answer.get({pred_repr})\n")
            lines.append(
                f"    assert got is not None, "
                f"'Expected non-None for predictor {pred_repr}'\n"
            )
            lines.append(
                f"    assert isinstance(got, dict), "
                f"'Expected dict for predictor {pred_repr}'\n"
            )
            if allele is not None:
                lines.append(
                    f"    assert got.get('allele', '').upper() == {json.dumps(str(allele).upper())}, (\n"
                    f"        f'Wrong allele for {pred_repr}. Got {{got.get(\"allele\")!r}}'\n"
                    f"    )\n"
                )
            if fc is not None:
                lines.append(
                    f"    assert _close(got.get('freq_cases'), {repr(fc)}), (\n"
                    f"        f'Wrong freq_cases for {pred_repr}. Expected {fc}, got {{got.get(\"freq_cases\")}}'\n"
                    f"    )\n"
                )
            if fctrl is not None:
                lines.append(
                    f"    assert _close(got.get('freq_controls'), {repr(fctrl)}), (\n"
                    f"        f'Wrong freq_controls for {pred_repr}. Expected {fctrl}, got {{got.get(\"freq_controls\")}}'\n"
                    f"    )\n"
                )
            lines.append("\n\n")
    return "".join(lines)


def build_test_q4(expected_answer: str) -> str:
    """Verifier for Step 5 (Evidence Selection)."""
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
    lines.append("        return ' '.join(t.strip() if not t.lower().startswith('vs') else t\n")
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
    new_task_num: int,
    gene_index: dict[str, dict[str, list[str]]],
    pgx_index: dict,
    freq_index: dict,
) -> None:
    """Write all files for one Harbor task (one turn of the 5-question chain)."""
    turns = chain["turns"]
    pmid = chain["pmid"]
    pmc_id = chain["pmc_id"]

    # Extract gold-standard data from JSONL turns
    q1_gene_ans: list[str] = turns[0]["answer"]           # gene list
    q2_pred_ans: dict[str, list[str]] = turns[1]["answer"] # {gene: [predictors]}
    q3_comp_ans: dict[str, list[str]] = turns[2]["answer"] # {predictor: [comparisons]}
    q4_evid_ans: str = turns[3]["answer"]                  # "predictor (comparison)"

    # Flatten predictor list across all genes
    all_predictors: list[str] = [p for preds in q2_pred_ans.values() for p in preds]

    # Shared Q1 prior-context block used by Q2–Q5
    q1_prior_turn = {
        "turn": 1,
        "step": "predictor_inventory_per_gene",
        "question": (
            "For each gene studied in this paper, list the genetic predictors "
            "explicitly evaluated (e.g., rsID/variant, star allele/haplotype, "
            "diplotype/genotype, or metabolizer/phenotype group)."
        ),
        "answer": q2_pred_ans,
    }

    if new_task_num == 1:
        # Predictor Inventory Per Gene (MCQ)
        gene_preds = q2_pred_ans
        seed = int(chain["chain_id"].split("_")[-1])
        options, correct_by_gene = make_q2_options(gene_preds, pmid, gene_index, seed)
        instruction = build_instruction_new_q1(pmid, q1_gene_ans, options)
        test_py = build_test_q2_mcq(correct_by_gene)

    elif new_task_num == 2:
        # Significance Judgment
        sig_answer = compute_sig_judgment_answer(pmid, all_predictors, q3_comp_ans, pgx_index)
        instruction = build_instruction_sig_judgment(pmid, [q1_prior_turn], q3_comp_ans)
        test_py = build_test_sig_judgment(sig_answer)

    elif new_task_num == 3:
        # Phenotype Category
        pheno_answer = compute_pheno_cat_answer(pmid, all_predictors, pgx_index)
        instruction = build_instruction_pheno_cat(pmid, [q1_prior_turn])
        test_py = build_test_pheno_cat(pheno_answer)

    elif new_task_num == 4:
        # Allele Frequency Extraction
        freq_answer = compute_allele_freq_answer(pmid, all_predictors, pgx_index, freq_index)
        instruction = build_instruction_allele_freq(pmid, [q1_prior_turn])
        test_py = build_test_allele_freq(freq_answer)

    else:  # new_task_num == 5
        # Evidence Selection
        q5_expected = q4_evid_ans if isinstance(q4_evid_ans, str) else ""
        instruction = build_instruction_new_q5(pmid, [q1_prior_turn], q3_comp_ans)
        test_py = build_test_q4(q5_expected)

    # Write task directory structure
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "instruction.md").write_text(instruction)
    (task_dir / "task.toml").write_text(TASK_TOML)

    env_dir = task_dir / "environment"
    env_dir.mkdir(exist_ok=True)

    (env_dir / "Dockerfile").write_text(DOCKERFILE)

    # Always copy the paper and variant_lookup.py
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

    print("Building PGx annotation index (significance + phenotype)…")
    pgx_index = build_pgx_index()
    print(f"  {len(pgx_index)} PMIDs indexed")

    print("Building allele frequency index from study_parameters.tsv…")
    freq_index = build_freq_index()
    print(f"  {len(freq_index)} study parameter entries indexed")

    # Remove any existing task dirs that match our naming pattern
    for d in BASE.iterdir():
        if d.is_dir() and "_q" in d.name:
            shutil.rmtree(d)

    total_tasks = 0
    for chain in chains:
        chain_id = chain["chain_id"]
        pmc_id = chain["pmc_id"]

        paper_src = PAPERS_DIR / f"{pmc_id}.md"
        if not paper_src.exists():
            continue

        for new_task_num in range(1, 6):  # Q1 through Q5
            task_name = f"{chain_id}_q{new_task_num}"
            task_dir = BASE / task_name
            build_task(task_dir, chain, new_task_num, gene_index, pgx_index, freq_index)
            total_tasks += 1

        print(f"  {chain_id} ({pmc_id}) — 5 tasks")

    print(f"\nGenerated {total_tasks} Harbor tasks in {BASE}/")


if __name__ == "__main__":
    main()
