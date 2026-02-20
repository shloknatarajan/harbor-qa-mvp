You are a pharmacogenomics researcher. A collection of research papers is available in `/app/papers/`. Some of these papers are relevant to the variant of interest, while many are unrelated distractors.

**Variant:** CYP2D6*1, CYP2D6*1xN, CYP2D6*2, CYP2D6*2xN, CYP2D6*3, CYP2D6*4, CYP2D6*5, CYP2D6*6, CYP2D6*10, CYP2D6*17
**Gene:** CYP2D6
**Phenotype Category:** Metabolism/PK

Term banks of known drug and phenotype names are available at:
- `/app/term_banks/drugs.txt` — one drug name per line
- `/app/term_banks/phenotypes.txt` — one phenotype name per line

Your task is to read through the papers and identify the following information about **CYP2D6*1, CYP2D6*1xN, CYP2D6*2, CYP2D6*2xN, CYP2D6*3, CYP2D6*4, CYP2D6*5, CYP2D6*6, CYP2D6*10, CYP2D6*17** in gene **CYP2D6**:

1. **Drugs**: Select all drugs associated with this variant from the drug term bank.
2. **Phenotypes**: Select all phenotypes (diseases/conditions) associated with this variant from the phenotype term bank.
3. **Relevant paper count**: How many of the papers in `/app/papers/` are relevant to CYP2D6*1, CYP2D6*1xN, CYP2D6*2, CYP2D6*2xN, CYP2D6*3, CYP2D6*4, CYP2D6*5, CYP2D6*6, CYP2D6*10, CYP2D6*17?

---

You must write your answers to `/app/answers.json` (a real file on disk). Printing JSON in chat is not sufficient.
After writing the file, verify it exists and contains valid JSON.

For example, you may use a shell heredoc to write the file:
```bash
cat > /app/answers.json <<'JSON'
{
  "drugs": ["drug1", "drug2"],
  "phenotypes": ["phenotype1", "phenotype2"],
  "relevant_paper_count": 3
}
JSON
python -c 'import json; json.load(open("/app/answers.json"))'
```

The JSON object must have the following structure:

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
- The papers directory contains 12 papers total. Count only those relevant to CYP2D6*1, CYP2D6*1xN, CYP2D6*2, CYP2D6*2xN, CYP2D6*3, CYP2D6*4, CYP2D6*5, CYP2D6*6, CYP2D6*10, CYP2D6*17.
- **Do not use web search.** All information you need is in the provided papers and term banks.