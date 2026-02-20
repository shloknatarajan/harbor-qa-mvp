import os
import json
from pathlib import Path

import pytest

EXPECTED_RECOMMENDATION = "Halogenated volatile anesthetics or the depolarizing muscle relaxant succinylcholine are relatively contraindicated in persons with malignant hyperthermia susceptibility (MHS). They should not be used, except in extraordinary circumstances where the benefits outweigh the risks. In general, alternative anesthetics are widely available and effective in patients with MHS."
EXPECTED_CLASSIFICATION = "Strong"
DRUG = "desflurane"
GENE = "CACNA1S|RYR1"
VARIANT = "RYR1 Malignant Hyperthermia Susceptibility; CACNA1S Uncertain Susceptibility"


JUDGE_PROMPT_TEMPLATE = """You are evaluating a pharmacogenomics clinical recommendation.

## Ground Truth (CPIC Guideline)
- **Drug:** {drug}
- **Gene:** {gene}
- **Patient Genotype:** {variant}
- **Recommendation:** {expected_rec}
- **Classification Strength:** {expected_class}

## Agent's Recommendation
{agent_rec}

## Evaluation Criteria

Score EACH of the following dimensions on a scale of 1-5:

1. **action_match**: Does the agent recommend the same clinical action as the ground truth?
   (e.g., both say "avoid", both say "reduce dose by 50%", both say "use standard dosing")
   - 5: Exact same action
   - 4: Same general action with minor differences in wording
   - 3: Similar but with meaningful differences (e.g., "reduce dose" vs "reduce dose by 50%")
   - 2: Partially correct (gets the direction right but misses key details)
   - 1: Wrong action (e.g., "standard dosing" when should be "avoid")

2. **specificity**: Does the agent provide the same level of clinical detail?
   (dosing percentages, monitoring recommendations, alternative suggestions)
   - 5: All key details present
   - 4: Most key details present
   - 3: Some details present
   - 2: Vague or missing most details
   - 1: No useful clinical detail

3. **safety**: Is the recommendation safe for the patient?
   - 5: Fully safe, matches guideline
   - 4: Safe with minor omissions
   - 3: Mostly safe but missing important caveats
   - 2: Could lead to suboptimal care
   - 1: Potentially dangerous (e.g., recommending standard dose when drug should be avoided)

Respond with ONLY a JSON object (no markdown, no explanation):
{{"action_match": <1-5>, "specificity": <1-5>, "safety": <1-5>, "brief_rationale": "<1 sentence>"}}"""


@pytest.fixture(scope="module")
def agent_recommendation():
    f = Path("/app/recommendation.txt")
    assert f.exists(), "recommendation.txt not found at /app/recommendation.txt"
    text = f.read_text().strip()
    assert len(text) > 0, "recommendation.txt is empty"
    return text


@pytest.fixture(scope="module")
def judge_result(agent_recommendation):
    """Call LLM judge to evaluate the agent's recommendation."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set - cannot run LLM judge")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        drug=DRUG,
        gene=GENE,
        variant=VARIANT,
        expected_rec=EXPECTED_RECOMMENDATION,
        expected_class=EXPECTED_CLASSIFICATION,
        agent_rec=agent_recommendation,
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Parse JSON from response (handle potential markdown wrapping)
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def test_recommendation_file_exists(agent_recommendation):
    """Check that the agent wrote a recommendation file."""
    assert len(agent_recommendation) > 10, (
        f"Recommendation too short ({len(agent_recommendation)} chars): "
        f"{agent_recommendation}"
    )


def test_action_match(judge_result):
    """LLM judge: does the recommendation match the correct clinical action?"""
    score = judge_result["action_match"]
    assert score >= 4, (
        f"Action match score {score}/5 (need >= 4). "
        f"Rationale: {judge_result.get('brief_rationale', '')}"
    )


def test_specificity(judge_result):
    """LLM judge: does the recommendation include sufficient clinical detail?"""
    score = judge_result["specificity"]
    assert score >= 3, (
        f"Specificity score {score}/5 (need >= 3). "
        f"Rationale: {judge_result.get('brief_rationale', '')}"
    )


def test_safety(judge_result):
    """LLM judge: is the recommendation safe for the patient?"""
    score = judge_result["safety"]
    assert score >= 4, (
        f"Safety score {score}/5 (need >= 4). "
        f"Rationale: {judge_result.get('brief_rationale', '')}"
    )
