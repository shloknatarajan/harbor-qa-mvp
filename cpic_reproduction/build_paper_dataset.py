"""Build a dataset mapping CPIC guidelines to relevant papers, variants, and drugs.

For each CPIC variant-drug recommendation, collects:
- Guideline papers: PMIDs and PMCIDs of the CPIC guideline publications
- Evidence papers: PMIDs and PMCIDs of underlying research
  (allele functional evidence from allele.tsv + population frequency studies)
- Variant(s), Drug(s), Guideline name

PMIDs are converted to PMCIDs using the NCBI ID Converter API.

Usage:
    python cpic_reproduction/build_paper_dataset.py
"""

import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent
DATA_DIR = PROJECT_ROOT / "data" / "cpic_data"
OUTPUT_PATH = BASE / "cpic_paper_dataset.jsonl"
OUTPUT_TSV = BASE / "cpic_paper_dataset.tsv"

NCBI_CONVERTER_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"


# ── Helpers ───────────────────────────────────────────────────────────


def parse_pg_array(s: str) -> list[str]:
    """Parse a PostgreSQL array string like {12345,67890} into a list."""
    if not s or s == "\\N":
        return []
    return [x.strip() for x in s.strip("{}").split(",") if x.strip()]


def load_tsv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def convert_pmids_to_pmcids(pmids: list[str], batch_size: int = 200) -> dict[str, str]:
    """Convert PMIDs to PMCIDs using the NCBI ID Converter API."""
    mapping: dict[str, str] = {}
    pmids = [p for p in pmids if p and p != "\\N"]

    for i in range(0, len(pmids), batch_size):
        batch = pmids[i : i + batch_size]
        try:
            params = urlencode(
                {
                    "ids": ",".join(batch),
                    "format": "json",
                    "tool": "cpic_dataset_builder",
                    "email": "cpic@example.com",
                }
            )
            url = f"{NCBI_CONVERTER_URL}?{params}"
            with urlopen(Request(url), timeout=30) as resp:
                data = json.loads(resp.read().decode())
            for record in data.get("records", []):
                pmid = record.get("pmid", "")
                pmcid = record.get("pmcid", "")
                if pmid and pmcid:
                    mapping[str(pmid)] = pmcid
        except Exception as e:
            print(f"  Warning: NCBI API error for batch {i}: {e}")

        if i + batch_size < len(pmids):
            time.sleep(0.5)

    return mapping


# ── Evidence collection ───────────────────────────────────────────────


def build_gene_evidence_pmids() -> dict[str, set[str]]:
    """Build gene → set of evidence PMIDs from allele citations + population studies."""
    alleles = load_tsv(DATA_DIR / "allele.tsv")
    gene_to_pmids: dict[str, set[str]] = defaultdict(set)
    allele_gene_map: dict[str, str] = {}

    for a in alleles:
        gene = a["genesymbol"]
        allele_gene_map[a["id"]] = gene
        for pmid in parse_pg_array(a.get("citations", "")):
            gene_to_pmids[gene].add(pmid)

    allele_count = sum(len(v) for v in gene_to_pmids.values())
    print(f"  Allele functional evidence: {allele_count} gene-PMID links")

    populations = {r["id"]: r for r in load_tsv(DATA_DIR / "population.tsv")}
    pub_map = {r["id"]: r for r in load_tsv(DATA_DIR / "publication.tsv")}

    pop_count = 0
    with open(DATA_DIR / "allele_frequency.tsv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            gene = allele_gene_map.get(row["alleleid"])
            if not gene:
                continue
            pop = populations.get(row["population"])
            if not pop:
                continue
            pub_id = pop.get("publicationid", "\\N")
            if pub_id == "\\N":
                continue
            pub = pub_map.get(pub_id)
            if pub and pub["pmid"] != "\\N":
                gene_to_pmids[gene].add(pub["pmid"])
                pop_count += 1

    print(f"  Population frequency evidence: {pop_count} allele-frequency-PMID links")
    total = set()
    for pmids in gene_to_pmids.values():
        total |= pmids
    print(
        f"  Total unique evidence PMIDs: {len(total)} across {len(gene_to_pmids)} genes"
    )

    return dict(gene_to_pmids)


# ── Main ──────────────────────────────────────────────────────────────


def build_dataset():
    print("Loading CPIC data...")

    recommendations = {r["id"]: r for r in load_tsv(DATA_DIR / "recommendation.tsv")}
    variant_recs = load_tsv(DATA_DIR / "variant_recommendations_consolidated.tsv")
    guidelines = {g["id"]: g for g in load_tsv(DATA_DIR / "guideline.tsv")}
    publications = load_tsv(DATA_DIR / "publication.tsv")
    pairs = load_tsv(DATA_DIR / "pair.tsv")

    # Guideline → publications
    guideline_pubs: dict[str, list[dict]] = {}
    for pub in publications:
        gid = pub.get("guidelineid", "\\N")
        if gid and gid != "\\N":
            guideline_pubs.setdefault(gid, []).append(pub)

    # Guideline → pair citations
    pair_by_guideline: dict[str, list[dict]] = {}
    for p in pairs:
        gid = p.get("guidelineid", "\\N")
        if gid and gid != "\\N":
            pair_by_guideline.setdefault(gid, []).append(p)

    # Gene-level evidence
    print(
        "\nBuilding gene-level evidence from allele citations + population studies..."
    )
    gene_evidence_pmids = build_gene_evidence_pmids()

    # ── Collect all PMIDs for conversion ──────────────────────────────

    print("\nCollecting all PMIDs...")
    all_pmids: set[str] = set()

    for pubs in guideline_pubs.values():
        for pub in pubs:
            pmid = pub.get("pmid", "\\N")
            if pmid and pmid != "\\N":
                all_pmids.add(pmid)

    for pair_list in pair_by_guideline.values():
        for p in pair_list:
            for pmid in parse_pg_array(p.get("citations", "")):
                all_pmids.add(pmid)

    for pmids in gene_evidence_pmids.values():
        all_pmids |= pmids

    print(f"  Total unique PMIDs: {len(all_pmids)}")

    # Existing PMCIDs from publication.tsv
    existing_pmid_to_pmcid: dict[str, str] = {}
    for pub in publications:
        pmid = pub.get("pmid", "\\N")
        pmcid = pub.get("pmcid", "\\N")
        if pmid and pmid != "\\N" and pmcid and pmcid != "\\N":
            existing_pmid_to_pmcid[pmid] = pmcid

    pmids_to_convert = [p for p in all_pmids if p not in existing_pmid_to_pmcid]
    print(f"  Already have PMCIDs: {len(existing_pmid_to_pmcid)}")
    print(f"  Needing API conversion: {len(pmids_to_convert)}")

    if pmids_to_convert:
        print("Converting PMIDs to PMCIDs via NCBI API...")
        api_mapping = convert_pmids_to_pmcids(pmids_to_convert)
        print(f"  Successfully converted: {len(api_mapping)}")
    else:
        api_mapping = {}

    pmid_to_pmcid = {**existing_pmid_to_pmcid, **api_mapping}
    print(f"  Total PMID→PMCID mappings: {len(pmid_to_pmcid)}")

    # ── Build dataset rows ────────────────────────────────────────────

    print("\nBuilding dataset rows...")
    rows = []

    for vr in variant_recs:
        rec_id = vr["rec_id"]
        rec = recommendations.get(rec_id)
        if not rec:
            continue

        guideline_id = rec.get("guidelineid", "\\N")
        if not guideline_id or guideline_id == "\\N":
            continue

        guideline = guidelines.get(guideline_id, {})
        guideline_name = guideline.get("name", "Unknown")

        try:
            variants_list = json.loads(vr["variants"])
        except json.JSONDecodeError:
            variants_list = [vr["variants"]]

        drug = vr["drug"]
        gene = vr["lookup_genes"]

        # Guideline PMIDs/PMCIDs
        guideline_pmids_set: set[str] = set()
        for pub in guideline_pubs.get(guideline_id, []):
            pmid = pub.get("pmid", "\\N")
            if pmid and pmid != "\\N":
                guideline_pmids_set.add(pmid)
        for p in pair_by_guideline.get(guideline_id, []):
            for pmid in parse_pg_array(p.get("citations", "")):
                guideline_pmids_set.add(pmid)

        guideline_pmcids_set = {
            pmid_to_pmcid[p] for p in guideline_pmids_set if p in pmid_to_pmcid
        }

        # Evidence PMIDs/PMCIDs (by gene)
        evidence_pmids_set: set[str] = set()
        for g in gene.split("|"):
            evidence_pmids_set |= gene_evidence_pmids.get(g, set())

        evidence_pmcids_set = {
            pmid_to_pmcid[p] for p in evidence_pmids_set if p in pmid_to_pmcid
        }

        row = {
            "rec_id": rec_id,
            "drug": drug,
            "gene": gene,
            "variants": variants_list,
            "guideline": guideline_name,
            "guideline_id": guideline_id,
            "recommendation": vr["recommendation"],
            "classification": rec.get("classification", ""),
            "guideline_pmids": sorted(guideline_pmids_set),
            "guideline_pmcids": sorted(guideline_pmcids_set),
            "evidence_pmids": sorted(evidence_pmids_set),
            "evidence_pmcids": sorted(evidence_pmcids_set),
        }
        rows.append(row)

    # ── Summary stats ─────────────────────────────────────────────────

    print(f"\nDataset summary:")
    print(f"  Total rows: {len(rows)}")
    print(f"  Unique drugs: {len(set(r['drug'] for r in rows))}")
    print(f"  Unique genes: {len(set(r['gene'] for r in rows))}")
    print(f"  Unique guidelines: {len(set(r['guideline'] for r in rows))}")

    all_gl_pmids = set()
    all_gl_pmcids = set()
    all_ev_pmids = set()
    all_ev_pmcids = set()
    for r in rows:
        all_gl_pmids.update(r["guideline_pmids"])
        all_gl_pmcids.update(r["guideline_pmcids"])
        all_ev_pmids.update(r["evidence_pmids"])
        all_ev_pmcids.update(r["evidence_pmcids"])

    print(
        f"\n  Guideline papers: {len(all_gl_pmids)} PMIDs, {len(all_gl_pmcids)} PMCIDs "
        f"({len(all_gl_pmcids)}/{len(all_gl_pmids)} = {len(all_gl_pmcids) / len(all_gl_pmids) * 100:.0f}% converted)"
    )
    print(
        f"  Evidence papers:  {len(all_ev_pmids)} PMIDs, {len(all_ev_pmcids)} PMCIDs "
        f"({len(all_ev_pmcids)}/{len(all_ev_pmids)} = {len(all_ev_pmcids) / len(all_ev_pmids) * 100:.0f}% converted)"
    )

    ev_pmid_counts = [len(r["evidence_pmids"]) for r in rows]
    ev_pmcid_counts = [len(r["evidence_pmcids"]) for r in rows]
    print(
        f"\n  Evidence PMIDs per row:  min={min(ev_pmid_counts)}, "
        f"max={max(ev_pmid_counts)}, median={sorted(ev_pmid_counts)[len(ev_pmid_counts) // 2]}"
    )
    print(
        f"  Evidence PMCIDs per row: min={min(ev_pmcid_counts)}, "
        f"max={max(ev_pmcid_counts)}, median={sorted(ev_pmcid_counts)[len(ev_pmcid_counts) // 2]}"
    )

    # Check overlap with existing papers
    papers_dir = PROJECT_ROOT / "data" / "papers"
    if papers_dir.exists():
        existing_pmcids = {f.stem for f in papers_dir.glob("PMC*.md")}
        all_pmcids = all_gl_pmcids | all_ev_pmcids
        overlap = all_pmcids & existing_pmcids
        print(f"\n  PMCIDs already in data/papers/: {len(overlap)} / {len(all_pmcids)}")

    # ── Write outputs ─────────────────────────────────────────────────

    with open(OUTPUT_PATH, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"\nWrote JSONL: {OUTPUT_PATH}")

    with open(OUTPUT_TSV, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(
            [
                "rec_id",
                "drug",
                "gene",
                "variants",
                "guideline",
                "guideline_id",
                "recommendation",
                "classification",
                "guideline_pmids",
                "guideline_pmcids",
                "evidence_pmids",
                "evidence_pmcids",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["rec_id"],
                    row["drug"],
                    row["gene"],
                    json.dumps(row["variants"]),
                    row["guideline"],
                    row["guideline_id"],
                    row["recommendation"],
                    row["classification"],
                    json.dumps(row["guideline_pmids"]),
                    json.dumps(row["guideline_pmcids"]),
                    json.dumps(row["evidence_pmids"]),
                    json.dumps(row["evidence_pmcids"]),
                ]
            )
    print(f"Wrote TSV:   {OUTPUT_TSV}")


if __name__ == "__main__":
    build_dataset()
