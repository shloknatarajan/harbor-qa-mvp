You are a clinical pharmacogenomics expert.

**Drug:** efavirenz
**Gene:** CYP2B6
**Patient Genotype:** CYP2B6 Poor Metabolizer

Based on your knowledge of pharmacogenomics, provide a clinical recommendation for this drug-gene-variant combination.

---

You must write your answers to `/app/answers.json` (a real file on disk). Printing JSON in chat is not sufficient.
After writing the file, verify it exists and contains valid JSON.

For example, you may use a shell heredoc to write the file:
```bash
cat > /app/answers.json <<'JSON'
{
  "recommendation": "Use drug per standard dosing guidelines",
  "classification": "Strong",
  "implication": "Normal metabolism expected"
}
JSON
python3 -c 'import json; json.load(open("/app/answers.json"))'
```

The JSON object must have the following structure:

```json
{
  "recommendation": "<dosing recommendation text>",
  "classification": "<Strong|Moderate|Optional>",
  "implication": "<clinical implication of this genotype>"
}
```

Notes:
- **recommendation**: Your clinical dosing recommendation for this drug-gene-variant combination.
- **classification**: The strength of this recommendation (Strong, Moderate, or Optional).
- **implication**: The clinical implication of this specific genotype for this drug's metabolism/response.
- **Do not use web search.** Rely only on your pharmacogenomics knowledge.