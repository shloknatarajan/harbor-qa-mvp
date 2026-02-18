You are a pharmacogenomics researcher. A collection of research papers is available in `/app/papers/`. Some of these papers are relevant to the variant of interest, while many are unrelated distractors.

**Variant:** CYP2C9*1, CYP2C9*2, CYP2C9*3, CYP2C9*5, CYP2C9*6, CYP2C9*8, CYP2C9*11, CYP2C9*13, CYP2C9*14, CYP2C9*16, CYP2C9*29, CYP2C9*31, CYP2C9*33, CYP2C9*37, CYP2C9*39, CYP2C9*42, CYP2C9*43, CYP2C9*45, CYP2C9*50, CYP2C9*52, CYP2C9*55
**Gene:** CYP2C9
**Phenotype Category:** Metabolism/PK

Term banks of known drug and phenotype names are available at:
- `/app/term_banks/drugs.txt` — one drug name per line
- `/app/term_banks/phenotypes.txt` — one phenotype name per line

Your task is to read through the papers and identify the following information about **CYP2C9*1, CYP2C9*2, CYP2C9*3, CYP2C9*5, CYP2C9*6, CYP2C9*8, CYP2C9*11, CYP2C9*13, CYP2C9*14, CYP2C9*16, CYP2C9*29, CYP2C9*31, CYP2C9*33, CYP2C9*37, CYP2C9*39, CYP2C9*42, CYP2C9*43, CYP2C9*45, CYP2C9*50, CYP2C9*52, CYP2C9*55** in gene **CYP2C9**:

1. **Drugs**: Select all drugs associated with this variant from the drug term bank.
2. **Phenotypes**: Select all phenotypes (diseases/conditions) associated with this variant from the phenotype term bank.
3. **Relevant paper count**: How many of the papers in `/app/papers/` are relevant to CYP2C9*1, CYP2C9*2, CYP2C9*3, CYP2C9*5, CYP2C9*6, CYP2C9*8, CYP2C9*11, CYP2C9*13, CYP2C9*14, CYP2C9*16, CYP2C9*29, CYP2C9*31, CYP2C9*33, CYP2C9*37, CYP2C9*39, CYP2C9*42, CYP2C9*43, CYP2C9*45, CYP2C9*50, CYP2C9*52, CYP2C9*55?

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
- The papers directory contains 14 papers total. Count only those relevant to CYP2C9*1, CYP2C9*2, CYP2C9*3, CYP2C9*5, CYP2C9*6, CYP2C9*8, CYP2C9*11, CYP2C9*13, CYP2C9*14, CYP2C9*16, CYP2C9*29, CYP2C9*31, CYP2C9*33, CYP2C9*37, CYP2C9*39, CYP2C9*42, CYP2C9*43, CYP2C9*45, CYP2C9*50, CYP2C9*52, CYP2C9*55.
- **Do not use web search.** All information you need is in the provided papers and term banks.