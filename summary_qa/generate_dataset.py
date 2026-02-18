"""Generate the summary_qa JSONL dataset from summary_annotations.tsv.

Reads summary_annotations.tsv and summary_ann_evidence.tsv, then produces
a JSONL file where each line has:
- All original columns from summary_annotations.tsv
- pmids: list of PMIDs extracted from the evidence table
- pmcids: list of PMCIDs mapped from PMIDs (using MCQ files as mapping source)
- evidence: list of evidence summaries from summary_ann_evidence.tsv
- Drug(s) and Phenotype(s) converted to lists of strings

Usage:
    python summary_qa/generate_dataset.py
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "summaryAnnotations"
MC_QUESTIONS_DIR = PROJECT_ROOT / "data" / "mc_questions"

ANNOTATIONS_FILE = DATA_DIR / "summary_annotations.tsv"
EVIDENCE_FILE = DATA_DIR / "summary_ann_evidence.tsv"
OUTPUT_FILE = BASE / "summary_annotations.jsonl"

MCQ_FILES = [
    MC_QUESTIONS_DIR / "drug_mcq_options.jsonl",
    MC_QUESTIONS_DIR / "variant_mcq_options.jsonl",
    MC_QUESTIONS_DIR / "phenotype_mcq_options.jsonl",
]


def load_pmid_to_pmcid_mapping() -> dict[str, str]:
    """Build a PMID -> PMCID mapping from MCQ files."""
    mapping: dict[str, str] = {}
    for mcq_file in MCQ_FILES:
        if not mcq_file.exists():
            continue
        with open(mcq_file, encoding="utf-8") as f:
            for line in f:
                q = json.loads(line)
                pmid = q.get("pmid", "")
                pmcid = q.get("pmcid", "")
                if pmid and pmcid:
                    mapping[str(pmid)] = pmcid
    return mapping


def load_evidence(evidence_file: Path) -> dict[str, list[dict]]:
    """Load evidence grouped by Summary Annotation ID."""
    evidence_by_id: dict[str, list[dict]] = defaultdict(list)
    with open(evidence_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            ann_id = row["Summary Annotation ID"]
            evidence_by_id[ann_id].append(row)
    return evidence_by_id


def parse_semicolon_list(value: str) -> list[str]:
    """Split a semicolon-delimited string into a list of stripped strings."""
    if not value or not value.strip():
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def main():
    pmid_to_pmcid = load_pmid_to_pmcid_mapping()
    print(f"Loaded {len(pmid_to_pmcid)} PMID->PMCID mappings")

    evidence_by_id = load_evidence(EVIDENCE_FILE)

    records = []
    with open(ANNOTATIONS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            ann_id = row["Summary Annotation ID"]
            evidence_rows = evidence_by_id.get(ann_id, [])

            # Extract PMIDs from evidence (deduplicated, preserving order)
            seen_pmids: set[str] = set()
            pmids: list[str] = []
            for ev in evidence_rows:
                pmid = ev["PMID"].strip()
                if pmid and pmid not in seen_pmids:
                    seen_pmids.add(pmid)
                    pmids.append(pmid)

            # Map PMIDs to PMCIDs (deduplicated, preserving order)
            seen_pmcids: set[str] = set()
            pmcids: list[str] = []
            for pmid in pmids:
                pmcid = pmid_to_pmcid.get(pmid, "")
                if pmcid and pmcid not in seen_pmcids:
                    seen_pmcids.add(pmcid)
                    pmcids.append(pmcid)

            # Build evidence list
            evidence = [ev["Summary"] for ev in evidence_rows]

            # Build the output record
            record = {
                "summary_annotation_id": ann_id,
                "variant_haplotypes": row["Variant/Haplotypes"],
                "gene": row["Gene"],
                "score": row["Score"],
                "phenotype_category": row["Phenotype Category"],
                "pmid_count": int(row["PMID Count"]),
                "pmids": pmids,
                "pmcids": pmcids,
                "evidence_count": int(row["Evidence Count"]),
                "evidence": evidence,
                "drugs": parse_semicolon_list(row["Drug(s)"]),
                "phenotypes": parse_semicolon_list(row["Phenotype(s)"]),
                "url": row["URL"],
            }
            records.append(record)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with_pmcids = sum(1 for r in records if r["pmcids"])
    print(f"Wrote {len(records)} records to {OUTPUT_FILE}")
    print(f"  {with_pmcids} records have at least 1 PMCID mapping")


if __name__ == "__main__":
    main()
