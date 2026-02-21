"""Generate the CONDENSED cpic_evidence_benchmark (evidence versions of zero-context condensed tasks).

Uses the same tasks as cpic_zero_context_condensed (one task per unique
recommendation across ALL Level A single-gene CPIC guidelines), but provides
research paper abstracts so the agent can use evidence rather than parametric
knowledge alone.

Tasks with no evidence papers are excluded (e.g. CFTR/ivacaftor) to ensure
every task actually has evidence context. The zero-context condensed benchmark
should be regenerated after this one to stay aligned.

This enables a direct apples-to-apples comparison:
  - cpic_zero_context_condensed: 70 tasks, no papers
  - cpic_evidence_benchmark_condensed: same 70 tasks, with papers

Papers are sourced from cpic_paper_dataset.jsonl (evidence_pmids per rec_id).
Guideline papers are intentionally excluded — they contain the CPIC
recommendations (i.e. the answers).
Abstracts are fetched from PubMed and cached in data/cpic_abstracts/.

Generate:
    python cpic_evidence_benchmark_condensed/generate_dataset.py

Run:
    python main.py -p cpic_evidence_benchmark_condensed -a claude-code -n 3 -l 5
"""

import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

# Import shared utilities from evidence and zero-context benchmarks
sys.path.insert(0, str(Path(__file__).parent.parent))
from cpic_evidence_benchmark.generate_dataset import (
    build_dockerfile,
    build_instruction,
    build_test_py,
    fetch_abstracts,
    TASK_TOML,
    TEST_SH,
    ABSTRACT_DIR,
    DATA_DIR,
    MARKDOWN_DIR,
)
from cpic_zero_context.generate_dataset import load_data

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent
DATASET_PATH = PROJECT_ROOT / "cpic_reproduction" / "cpic_paper_dataset.jsonl"


def condense(records: list[dict]) -> list[dict]:
    """Keep one task per unique recommendation text."""
    seen: dict[str, dict] = {}
    for rec in records:
        key = rec["recommendation"]
        if key not in seen:
            seen[key] = rec
    return list(seen.values())


def load_paper_dataset() -> dict[str, dict]:
    """Load cpic_paper_dataset.jsonl, keyed by rec_id."""
    paper_by_id: dict[str, dict] = {}
    for line in DATASET_PATH.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        paper_by_id[str(rec["rec_id"])] = rec
    return paper_by_id


def get_papers_for_record(
    paper_rec: dict,
) -> tuple[list[str], list[str]]:
    """Get full-text PMCIDs and abstract-only PMIDs for a paper dataset record.

    Returns (available_full_text_pmcids, abstract_only_pmids).
    Full-text is only available if the markdown file exists in MARKDOWN_DIR.
    """
    pmcids = set(paper_rec.get("evidence_pmcids", []))
    pmids = set(paper_rec.get("evidence_pmids", []))

    # Check which full-text files exist
    available_pmcids = [pmc for pmc in pmcids if (MARKDOWN_DIR / f"{pmc}.md").exists()]

    # Map PMCIDs to PMIDs to find which PMIDs already have full-text
    pmcid_to_pmid: dict[str, str] = {}
    for pmc in available_pmcids:
        md_path = MARKDOWN_DIR / f"{pmc}.md"
        for line in md_path.read_text().splitlines()[:20]:
            if line.startswith("**PMID:**"):
                pmid_val = line.split("**PMID:**")[1].strip()
                pmcid_to_pmid[pmc] = pmid_val
                break

    pmids_with_fulltext = set(pmcid_to_pmid.values())
    abstract_only_pmids = [p for p in pmids if p not in pmids_with_fulltext]

    # NOTE: we intentionally do NOT fall back to guideline_pmids here.
    # Guideline papers contain the CPIC recommendations (i.e. the answers),
    # so including them would leak ground truth to the agent.

    return available_pmcids, abstract_only_pmids


def main():
    # Load records from the same source as zero-context condensed
    print("Loading zero-context eligible records...")
    eligible = load_data()
    print(f"Eligible records (before condensing): {len(eligible)}")

    condensed = condense(eligible)
    print(f"After condensing (unique recommendations): {len(condensed)}")

    sel_genes = Counter(r["gene"] for r in condensed)
    sel_drugs = Counter(r["drug"] for r in condensed)
    sel_class = Counter(r["classification"] for r in condensed)
    print(f"  Genes ({len(sel_genes)}): {dict(sel_genes)}")
    print(f"  Unique drugs: {len(sel_drugs)}")
    print(f"  Classifications: {dict(sel_class)}")

    # Load paper dataset to get evidence PMIDs for each task
    print("\nLoading paper dataset...")
    paper_by_id = load_paper_dataset()
    print(f"  Paper dataset: {len(paper_by_id)} records")

    # Match condensed tasks to paper dataset and collect all PMIDs
    paper_cache: dict[str, tuple[list[str], list[str]]] = {}
    all_abstract_pmids: set[str] = set()
    matched = 0
    unmatched = 0

    for rec in condensed:
        rid = str(rec["rec_id"])
        paper_rec = paper_by_id.get(rid)
        if paper_rec:
            full_pmcids, abs_pmids = get_papers_for_record(paper_rec)
            paper_cache[rid] = (full_pmcids, abs_pmids)
            all_abstract_pmids.update(abs_pmids)
            matched += 1
        else:
            paper_cache[rid] = ([], [])
            unmatched += 1

    print(f"  Matched: {matched}/{len(condensed)}")
    if unmatched:
        print(f"  WARNING: {unmatched} tasks have no paper dataset entry")

    # Exclude tasks with no evidence papers (e.g. CFTR/ivacaftor).
    # Guideline papers are NOT used as fallback since they contain the answers.
    excluded = []
    filtered = []
    for rec in condensed:
        rid = str(rec["rec_id"])
        full_pmcids, abs_pmids = paper_cache.get(rid, ([], []))
        if full_pmcids or abs_pmids:
            filtered.append(rec)
        else:
            excluded.append(rec)
            print(f"  Excluding {rec['gene']}/{rec['drug']} (rec_id={rid}) — no evidence papers")

    if excluded:
        print(f"  Excluded {len(excluded)} tasks with no evidence papers")
    condensed = filtered
    print(f"  Tasks after filtering: {len(condensed)}")

    # Fetch abstracts
    print(f"\nNeed abstracts for {len(all_abstract_pmids)} unique PMIDs")
    abstract_cache: dict[str, str] = {}
    if all_abstract_pmids:
        print("Fetching abstracts from PubMed (cached where possible)...")
        abstract_cache = fetch_abstracts(list(all_abstract_pmids))
        print(f"  Got {len(abstract_cache)} abstracts")

    # Clean existing task dirs
    for d in BASE.iterdir():
        if d.is_dir() and d.name != "__pycache__":
            shutil.rmtree(d)

    # Generate tasks
    print(f"\nGenerating tasks in {BASE}/")
    for i, rec in enumerate(condensed, 1):
        gene_slug = re.sub(r"[^a-z0-9]+", "_", rec["gene"].lower()).strip("_")
        drug_slug = re.sub(r"[^a-z0-9]+", "_", rec["drug"].lower()).strip("_")
        task_name = f"{gene_slug}_{drug_slug}_{rec['rec_id']}"
        task_dir = BASE / task_name

        # The zero-context records already have variant_description
        rec_with_desc = {**rec}
        if "variant_description" not in rec_with_desc:
            rec_with_desc["variant_description"] = "; ".join(rec["variants"])

        # Create directories
        task_dir.mkdir(parents=True, exist_ok=True)
        env_dir = task_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        papers_dir = env_dir / "papers"
        papers_dir.mkdir(exist_ok=True)
        tests_dir = task_dir / "tests"
        tests_dir.mkdir(exist_ok=True)

        # Copy papers
        rid = str(rec["rec_id"])
        full_pmcids, abs_pmids = paper_cache.get(rid, ([], []))

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

        # Write task files — uses evidence instruction (mentions /app/papers/)
        (task_dir / "instruction.md").write_text(build_instruction(rec_with_desc))
        (task_dir / "task.toml").write_text(TASK_TOML)
        (env_dir / "Dockerfile").write_text(build_dockerfile(paper_files))
        (tests_dir / "test.sh").write_text(TEST_SH)
        (tests_dir / "test_outputs.py").write_text(build_test_py(rec_with_desc))

        print(
            f"  [{i:3d}/{len(condensed)}] {task_name} — "
            f"{rec_with_desc['variant_description'][:50]} | "
            f"{rec['classification']} | {len(paper_files)} papers"
        )

    print(f"\nGenerated {len(condensed)} tasks in {BASE}/")
    print(
        f"Run: python main.py -p cpic_evidence_benchmark_condensed "
        f"-a claude-code -n 3 -l 5"
    )


if __name__ == "__main__":
    main()
