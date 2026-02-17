"""Copy paper markdown files from data/papers/ into each question's papers/ directory.

Usage:
    python mvp_pgx/fetch_papers.py

Papers are sourced from data/papers/ (pre-downloaded markdown files).
To add more papers to a question, just append more PMCIDs to the list.
"""

import shutil
import sys
from pathlib import Path

# Map question directories to their PMCIDs.
# Each question can reference multiple papers — just add more PMCIDs to the list.
QUESTIONS = {
    "question-1": ["PMC11730665"],
    "question-2": ["PMC6347826"],
}


def main():
    base = Path(__file__).parent
    papers_source = base.parent / "data" / "papers"

    for question_dir, pmcids in QUESTIONS.items():
        papers_dir = base / question_dir / "papers"
        papers_dir.mkdir(parents=True, exist_ok=True)
        for pmcid in pmcids:
            src = papers_source / f"{pmcid}.md"
            dst = papers_dir / f"{pmcid}.md"
            if not src.exists():
                print(f"ERROR: {src} not found", file=sys.stderr)
                sys.exit(1)
            shutil.copy2(src, dst)
            print(f"Copied {src} -> {dst}")

    print("Done.")


if __name__ == "__main__":
    main()
