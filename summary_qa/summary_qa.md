# Summary QA

## New table/dataset

`generate_dataset.py` reads `summary_annotations.tsv` and `summary_ann_evidence.tsv` and produces `summary_annotations.jsonl` with:
- `pmids`: list of PMIDs extracted from evidence (deduplicated, preserving order)
- `pmcids`: list of PMCIDs mapped from PMIDs (using the MCQ files in `data/mc_questions/` as the PMID->PMCID mapping source)
- `evidence`: list of evidence summary strings from `summary_ann_evidence.tsv`
- `drugs` and `phenotypes` converted from semicolon-delimited strings to lists

5,190 total records; 2,561 have at least one PMCID mapping to a paper on disk.

## Harbor QA Set

`generate_questions.py` creates 100 Harbor tasks from `summary_annotations.jsonl`.

**Task design:** Given a set of papers (relevant papers + 10 random distractors), identify the associated drugs, phenotypes, and relevant paper count for a specific variant.

**Selection:** Top 100 annotations by score (higher score = more evidence), filtered to those with at least one drug and at least one paper available on disk.

**Folder naming:** `pmc<first_pmcid>_<variant_slug>_summary` (annotation ID appended on collision).

**Each task directory contains:**
- `instruction.md` — prompt with variant, gene, phenotype category, and output format
- `task.toml` — Harbor config
- `environment/Dockerfile` + `environment/papers/` — relevant + distractor papers
- `tests/test_outputs.py` — recall check for drugs and phenotypes, exact match for relevant paper count
- `tests/test.sh` — test runner with reward calculation (fraction of passed tests)

**Evaluation:**
- Drugs: recall (all expected drugs must appear)
- Phenotypes: recall (all expected phenotypes must appear)
- Relevant paper count: exact match
- Reward: fraction of the 3 tests that pass
