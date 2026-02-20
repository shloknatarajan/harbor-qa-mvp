You are a clinical pharmacogenomics expert.

**Drug:** tamoxifen
**Gene:** CYP2D6
**Patient Genotype:** CYP2D6 0.75

Based on your knowledge of pharmacogenomics, provide a clinical recommendation for this drug-gene-variant combination.

---

You must write your answers to `/app/answers.json` (a real file on disk). Printing JSON in chat is not sufficient.
After writing the file, verify it exists and contains valid JSON.

For example, you may use a shell heredoc to write the file:
```bash
cat > /app/answers.json <<'JSON'
{
  "recommendation": "Use drug per standard dosing guidelines",
  "classification": "Moderate",
  "implication": "Normal metabolism expected"
}
JSON
python3 -c 'import json; json.load(open("/app/answers.json"))'
```

The JSON object must have the following structure:

```json
{
  "recommendation": "<dosing recommendation text>",
  "classification": "<Strong|Moderate|Optional|No Recommendation>",
  "implication": "<clinical implication of this genotype>"
}
```

Notes:
- **recommendation**: Your clinical dosing recommendation for this drug-gene-variant combination.
- **classification**: The CPIC classification strength of this recommendation, based on the quality and quantity of clinical evidence supporting it:
  - **Strong**: High-quality evidence and/or strong expert consensus that the recommendation should be followed.
  - **Moderate**: Moderate evidence; the recommendation is generally appropriate but evidence is less definitive.
  - **Optional**: Weak or emerging evidence; clinical action is at the prescriber's discretion.
  - **No Recommendation**: Insufficient evidence to make a recommendation for this gene-drug-phenotype combination.
- **implication**: The clinical implication of this specific genotype for this drug's metabolism/response.
- **Do not use web search.** Rely only on your pharmacogenomics knowledge.