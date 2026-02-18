You are a pharmacogenomics researcher. A collection of research papers is available in `/app/papers/`. Some of these papers are relevant to the variant of interest, while many are unrelated distractors.

**Variant:** rs2231142
**Gene:** ABCG2
**Phenotype Category:** Metabolism/PK

Term banks of known drug and phenotype names are available at:
- `/app/term_banks/drugs.txt` — one drug name per line
- `/app/term_banks/phenotypes.txt` — one phenotype name per line

Your task is to read through the papers and identify the following information about **rs2231142** in gene **ABCG2**:

1. **Drugs**: Select all drugs associated with this variant from the drug term bank.
2. **Phenotypes**: Select all phenotypes (diseases/conditions) associated with this variant from the phenotype term bank.
3. **Relevant paper count**: How many of the papers in `/app/papers/` are relevant to rs2231142?

---

Write your answers to `/app/answers.json` as a JSON object with the following structure:

```json
{
  "drugs": ["drug1", "drug2"],
  "phenotypes": ["phenotype1", "phenotype2"],
  "relevant_paper_count": 3
}
```

Notes:
- Drug and phenotype names should be lowercase.
- Only select terms from the provided term banks. Do not add terms that are not in the banks.
- The papers directory contains 13 papers total. Count only those relevant to rs2231142.