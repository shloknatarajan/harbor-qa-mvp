# Paper Download Pipeline

## Problem

The CPIC evidence dataset (`cpic_reproduction/cpic_paper_dataset.jsonl`) contains 1,753 evidence PMIDs, but only 25% (439) have PMCIDs via the NCBI ID Converter. Many evidence papers — especially older population frequency studies — are not in PMC Open Access, so they can't be downloaded directly from PMC.

This pipeline recovers additional full-text papers by checking multiple open access sources.

## Pipeline Overview

```
PMID
 ├──→ PubMed E-utilities ──→ DOI + metadata
 │
 ├──→ NCBI ID Converter ──→ PMCID? ──→ PMC OA (already done in build_paper_dataset.py)
 │
 ├──→ Unpaywall (via DOI) ──→ OA full text URL (PDF/HTML)
 │
 └──→ Europe PMC ──→ full text XML/PDF (broader coverage than NCBI PMC)
```

## Step 1: PMID → DOI via PubMed E-utilities

Most PMIDs have a DOI. Fetch it in bulk using the NCBI E-utilities API.

**API:** `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi`

```python
import urllib.request, json

def get_dois_for_pmids(pmids: list[str], batch_size: int = 200) -> dict[str, str]:
    """Fetch DOIs for a list of PMIDs from PubMed. Returns PMID → DOI mapping."""
    mapping = {}
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i+batch_size]
        ids_str = ",".join(batch)
        url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            f"?db=pubmed&id={ids_str}&retmode=json"
        )
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        for pmid in batch:
            info = data.get("result", {}).get(pmid, {})
            for aid in info.get("articleids", []):
                if aid["idtype"] == "doi":
                    mapping[pmid] = aid["value"]
                    break
        time.sleep(0.34)  # NCBI rate limit: 3 requests/sec without API key
    return mapping
```

**Rate limits:**
- Without API key: 3 requests/second
- With API key (free, register at NCBI): 10 requests/second
- Set `&api_key=YOUR_KEY` in the URL to use a key

## Step 2: DOI → Unpaywall

Unpaywall is a free index of ~30M legal open access copies of scholarly articles. Given a DOI, it returns the best available OA URL.

**API:** `https://api.unpaywall.org/v2/{doi}?email={your_email}`

```python
def check_unpaywall(doi: str, email: str) -> dict | None:
    """Check Unpaywall for an open access copy. Returns OA location or None."""
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if data.get("is_oa"):
            best = data.get("best_oa_location", {})
            return {
                "url": best.get("url"),
                "pdf_url": best.get("url_for_pdf"),
                "host_type": best.get("host_type"),     # "publisher", "repository"
                "version": best.get("version"),          # "publishedVersion", "acceptedVersion"
                "license": best.get("license"),
            }
    except Exception:
        pass
    return None
```

**Important:**
- Requires a **real email address** (rejects `test@example.com`)
- Rate limit: 100,000 requests/day
- Returns multiple `oa_locations` — `best_oa_location` is the highest quality
- `host_type` can be `"publisher"` (gold OA) or `"repository"` (green OA, e.g. author manuscript in PMC or institutional repo)
- `version` indicates quality: `"publishedVersion"` > `"acceptedVersion"` > `"submittedVersion"`

**Response fields of interest:**
```json
{
  "is_oa": true,
  "best_oa_location": {
    "url": "https://europepmc.org/articles/pmc1234567",
    "url_for_pdf": "https://europepmc.org/articles/pmc1234567?pdf=render",
    "host_type": "repository",
    "version": "publishedVersion",
    "license": "cc-by"
  },
  "oa_locations": [ ... ]
}
```

## Step 3: Europe PMC (fallback)

Europe PMC often has articles that NCBI PMC doesn't, including author manuscripts and papers from European funders.

**API:** `https://www.ebi.ac.uk/europepmc/webservices/rest/search`

```python
def check_europe_pmc(pmid: str) -> dict | None:
    """Check Europe PMC for full text availability."""
    url = (
        f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        f"?query=EXT_ID:{pmid}&resultType=core&format=json"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("resultList", {}).get("result", [])
        if results:
            r = results[0]
            full_text_urls = r.get("fullTextUrlList", {}).get("fullTextUrl", [])
            for ft in full_text_urls:
                if ft.get("documentStyle") in ("pdf", "html"):
                    return {
                        "url": ft.get("url"),
                        "format": ft.get("documentStyle"),
                        "availability": ft.get("availabilityCode"),  # "OA", "F" (free)
                    }
    except Exception:
        pass
    return None
```

**Rate limits:** 15 requests/second (no key needed)

## Step 4: Download Full Text

Once an OA URL is found, download the content. For PDFs, convert to text. For HTML, convert to markdown.

```python
def download_paper(url: str, output_path: Path) -> bool:
    """Download a paper from a URL. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CPICDatasetBuilder/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
        output_path.write_bytes(content)
        return True
    except Exception:
        return False
```

For PDF → text conversion, options include:
- `pymupdf` (fitz) — fast, good quality
- `pdfplumber` — good for tables
- `marker` — ML-based, best quality but slower

## Recommended Execution Order

```
1. Load evidence_pmids from cpic_paper_dataset.jsonl
2. Filter to PMIDs without PMCIDs (the ~1,300 missing ones)
3. Batch fetch DOIs from PubMed (Step 1)
4. For each DOI, check Unpaywall (Step 2)
5. For remaining PMIDs without OA, check Europe PMC (Step 3)
6. Download available full texts (Step 4)
7. Convert PDFs to markdown/text
8. Update the dataset with new availability info
```

## Expected Recovery Rates

Based on typical Unpaywall coverage of biomedical literature:
- Unpaywall covers ~30-40% of all DOIs as open access
- Europe PMC adds another 5-10% on top
- Combined with the existing 25% PMCID coverage, we might reach **50-60% total** full-text availability

## Current Evidence Availability (Top Candidates)

Ranked by evidence-only paper availability (excluding guideline papers):

| # | Gene | Guideline | Ev PMIDs | Ev PMCIDs | Missing | Rate |
|---|---|---|---|---|---|---|
| 1 | DPYD | Fluoropyrimidines | 9 | 7 | 2 | 77.8% |
| 2 | UGT1A1 | Atazanavir | 22 | 11 | 11 | 50.0% |
| 3 | CACNA1S\|RYR1 | Volatile anesthetics | 10 | 5 | 5 | 50.0% |
| 4 | CYP2B6 | Efavirenz | 88 | 39 | 49 | 44.3% |
| 5 | SLCO1B1 | Statins | 62 | 25 | 37 | 40.3% |

### DPYD Example

DPYD is missing 2 papers:
- PMID 18452418 — DOI `10.1111/j.1365-2710.2008.00898.x` (2008 paper in J Clin Pharm Ther)
- PMID 25410891 — DOI `10.2217/pgs.14.126` (2014 paper in Pharmacogenomics)

Both are behind paywalls and not in PMC. Running these through Unpaywall would determine if author/repository copies exist.

## API Keys and Registration

| Service | Key Required | Registration |
|---|---|---|
| PubMed E-utilities | Optional (faster with key) | https://www.ncbi.nlm.nih.gov/account/ |
| NCBI ID Converter | No | — |
| Unpaywall | No (just email) | — |
| Europe PMC | No | — |
