"""Generate the CONDENSED cpic_zero_context benchmark (one task per unique recommendation).

Same as cpic_zero_context but keeps only one task per unique recommendation
text. This removes redundancy where multiple variants or drugs map to the
same clinical recommendation.

Tasks with no evidence papers in cpic_paper_dataset.jsonl are excluded to
keep this benchmark aligned with cpic_evidence_benchmark_condensed (which
uses the same task set but provides papers).

Generate:
    python cpic_zero_context_condensed/generate_dataset.py

Run:
    python main.py -p cpic_zero_context_condensed -a claude-code -n 3 -l 5
"""

import json
import sys
from pathlib import Path

# Import everything from the full version
sys.path.insert(0, str(Path(__file__).parent.parent))
from cpic_zero_context.generate_dataset import (
    load_data,
    build_instruction,
    build_test_py,
    TASK_TOML,
    DOCKERFILE,
    TEST_SH,
)

import re
import shutil
from collections import Counter

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


def has_evidence_papers(rec_id: str, paper_by_id: dict[str, dict]) -> bool:
    """Check if a rec_id has any evidence papers (not guideline papers)."""
    paper_rec = paper_by_id.get(rec_id)
    if not paper_rec:
        return False
    return bool(paper_rec.get("evidence_pmids") or paper_rec.get("evidence_pmcids"))


def main():
    eligible = load_data()
    print(f"Eligible records (before condensing): {len(eligible)}")

    condensed = condense(eligible)
    print(f"After condensing (unique recommendations): {len(condensed)}")

    # Exclude tasks with no evidence papers to stay aligned with evidence benchmark
    paper_by_id = load_paper_dataset()
    excluded = [r for r in condensed if not has_evidence_papers(str(r["rec_id"]), paper_by_id)]
    condensed = [r for r in condensed if has_evidence_papers(str(r["rec_id"]), paper_by_id)]
    if excluded:
        for r in excluded:
            print(f"  Excluding {r['gene']}/{r['drug']} (rec_id={r['rec_id']}) — no evidence papers")
        print(f"  Excluded {len(excluded)} tasks")
    print(f"Tasks after filtering: {len(condensed)}")

    sel_genes = Counter(r["gene"] for r in condensed)
    sel_drugs = Counter(r["drug"] for r in condensed)
    sel_class = Counter(r["classification"] for r in condensed)
    print(f"  Genes ({len(sel_genes)}): {dict(sel_genes)}")
    print(f"  Unique drugs: {len(sel_drugs)}")
    print(f"  Classifications: {dict(sel_class)}")

    # Clean existing task dirs
    for d in BASE.iterdir():
        if d.is_dir() and d.name != "__pycache__":
            shutil.rmtree(d)

    for i, rec in enumerate(condensed, 1):
        gene_slug = re.sub(r"[^a-z0-9]+", "_", rec["gene"].lower()).strip("_")
        drug_slug = re.sub(r"[^a-z0-9]+", "_", rec["drug"].lower()).strip("_")
        task_name = f"{gene_slug}_{drug_slug}_{rec['rec_id']}"
        task_dir = BASE / task_name

        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "instruction.md").write_text(build_instruction(rec))
        (task_dir / "task.toml").write_text(TASK_TOML)

        env_dir = task_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        (env_dir / "Dockerfile").write_text(DOCKERFILE)

        tests_dir = task_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test.sh").write_text(TEST_SH)
        (tests_dir / "test_outputs.py").write_text(build_test_py(rec))

        variant = rec["variant_description"]
        cls = rec["classification"]
        print(
            f"  [{i:3d}/{len(condensed)}] {task_name} — "
            f"{variant[:50]} | {cls}"
        )

    print(f"\nGenerated {len(condensed)} tasks in {BASE}/")
    print(f"Run: python main.py -p cpic_zero_context_condensed -a claude-code -n 3 -l 5")


if __name__ == "__main__":
    main()
