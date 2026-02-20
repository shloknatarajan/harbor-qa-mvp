"""Generate the CONDENSED cpic_evidence_benchmark (one task per unique recommendation).

Same as cpic_evidence_benchmark but keeps only one task per unique
recommendation text across all 5 guidelines. This gives ~29 tasks covering
every distinct clinical scenario without redundancy.

Generate:
    python cpic_evidence_benchmark_condensed/generate_dataset.py

Run:
    python main.py -p cpic_evidence_benchmark_condensed -a claude-code -n 3 -l 5
"""

import sys
from pathlib import Path

# Import everything from the full version
sys.path.insert(0, str(Path(__file__).parent.parent))
from cpic_evidence_benchmark.generate_dataset import (
    load_target_records,
    get_evidence_papers,
    fetch_abstracts,
    build_instruction,
    build_dockerfile,
    build_test_py,
    TASK_TOML,
    TEST_SH,
    MARKDOWN_DIR,
)

import re
import shutil
from collections import Counter

BASE = Path(__file__).parent


def condense(records: list[dict]) -> list[dict]:
    """Keep one task per unique recommendation text."""
    seen: dict[str, dict] = {}
    for rec in records:
        key = rec["recommendation"]
        if key not in seen:
            seen[key] = rec
    return list(seen.values())


def main():
    print("Loading target records...")
    records = load_target_records()
    print(f"Total records (before condensing): {len(records)}")

    condensed = condense(records)
    print(f"After condensing (unique recommendations): {len(condensed)}")

    sel_genes = Counter(r["gene"] for r in condensed)
    sel_drugs = Counter(r["drug"] for r in condensed)
    sel_class = Counter(r["classification"] for r in condensed)
    print(f"  Genes ({len(sel_genes)}): {dict(sel_genes)}")
    print(f"  Unique drugs: {len(sel_drugs)}")
    print(f"  Classifications: {dict(sel_class)}")

    # Collect papers
    paper_cache: dict[str, tuple[list[str], list[str]]] = {}
    abstract_cache: dict[str, str] = {}
    all_abstract_pmids = set()

    for rec in condensed:
        key = (rec["gene"], rec["guideline"])
        if key not in paper_cache:
            full_pmcids, abs_pmids = get_evidence_papers(rec)
            paper_cache[key] = (full_pmcids, abs_pmids)
            all_abstract_pmids.update(abs_pmids)

    print(f"\nNeed abstracts for {len(all_abstract_pmids)} PMIDs")
    if all_abstract_pmids:
        print("Fetching abstracts from PubMed...")
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

        variant_desc = "; ".join(rec["variants"])
        rec_with_desc = {**rec, "variant_description": variant_desc}

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

        (task_dir / "instruction.md").write_text(build_instruction(rec_with_desc))
        (task_dir / "task.toml").write_text(TASK_TOML)
        (env_dir / "Dockerfile").write_text(build_dockerfile(paper_files))
        (tests_dir / "test.sh").write_text(TEST_SH)
        (tests_dir / "test_outputs.py").write_text(build_test_py(rec_with_desc))

        print(
            f"  [{i:3d}/{len(condensed)}] {task_name} — "
            f"{variant_desc[:50]} | {rec['classification']} | {len(paper_files)} papers"
        )

    print(f"\nGenerated {len(condensed)} tasks in {BASE}/")
    print(f"Run: python main.py -p cpic_evidence_benchmark_condensed -a claude-code -n 3 -l 5")


if __name__ == "__main__":
    main()
