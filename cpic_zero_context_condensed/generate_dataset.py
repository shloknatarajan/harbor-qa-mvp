"""Generate the CONDENSED cpic_zero_context benchmark (one task per unique recommendation).

Same as cpic_zero_context but keeps only one task per unique recommendation
text. This removes redundancy where multiple variants or drugs map to the
same clinical recommendation.

Generate:
    python cpic_zero_context_condensed/generate_dataset.py

Run:
    python main.py -p cpic_zero_context_condensed -a claude-code -n 3 -l 5
"""

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


def condense(records: list[dict]) -> list[dict]:
    """Keep one task per unique recommendation text."""
    seen: dict[str, dict] = {}
    for rec in records:
        key = rec["recommendation"]
        if key not in seen:
            seen[key] = rec
    return list(seen.values())


def main():
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
