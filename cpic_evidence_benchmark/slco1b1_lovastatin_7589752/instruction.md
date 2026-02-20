You are a clinical pharmacogenomics expert.

**Drug:** lovastatin
**Gene:** SLCO1B1
**Patient Genotype:** SLCO1B1 Possible Decreased Function

Research papers relevant to this gene-drug combination are available in `/app/papers/`. Read these papers to inform your recommendation.

Based on the evidence in these papers, provide a clinical dosing recommendation for this drug-gene-variant combination.

---

You must write your recommendation to `/app/recommendation.txt` (a real file on disk). Printing it in chat is not sufficient.

Your recommendation should be a concise clinical dosing recommendation (1-3 sentences). It should specify:
- What action to take (e.g., use standard dose, reduce dose, avoid drug, use alternative)
- Any specific dosing adjustments (e.g., 50% dose reduction)
- Any monitoring or follow-up needed

For example:
```
Reduce starting dose by 50% followed by titration of dose based on toxicity or therapeutic drug monitoring.
```

Notes:
- Read the research papers in /app/papers/ before answering.
- Do not use web search. Base your answer on the provided evidence.
- Write only the recommendation text — no JSON, no extra formatting.