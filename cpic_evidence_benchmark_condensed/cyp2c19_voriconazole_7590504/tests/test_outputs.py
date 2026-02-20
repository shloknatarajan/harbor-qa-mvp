import os
import json
from pathlib import Path

import pytest


EXPECTED_RECOMMENDATION = "Choose an alternative agent that is not dependent on CYP2C19 metabolism as primary therapy in lieu of voriconazole. Such agents include isavuconazole, liposomal amphotericin B, and posaconazole."
EXPECTED_CLASSIFICATION = "Moderate"
EXPECTED_IMPLICATION = "CYP2C19: In patients for whom an ultrarapid metabolizer genotype (*17/*17) is identified, the probability of attainment of therapeutic voriconazole concentrations is small with standard dosing"
DRUG = "voriconazole"
GENE = "CYP2C19"
VARIANT = "CYP2C19 Ultrarapid Metabolizer"


JUDGE_PROMPT = "You are a STRICT pharmacogenomics evaluation judge. You are comparing an AI agent's clinical recommendation against the official CPIC guideline. Be rigorous \u2014 clinical details matter and vague or incomplete answers should score low. Do NOT give the benefit of the doubt.\n\n## Ground Truth (CPIC Guideline)\n- **Drug:** {drug}\n- **Gene:** {gene}\n- **Patient Genotype:** {variant}\n- **CPIC Recommendation:** {expected_rec}\n- **Classification Strength:** {expected_class}\n- **CPIC Implication:** {expected_impl}\n\n## Agent's Answer\n- **Recommendation:** {agent_rec}\n- **Classification:** {agent_class}\n- **Implication:** {agent_impl}\n\n## Evaluation Criteria\n\nScore EACH dimension on a 1-5 scale. Be strict: a score of 5 means essentially perfect, 4 means correct with only trivial omissions. Anything missing a clinically meaningful detail should be 3 or below.\n\n1. **action_correctness**: Does the agent recommend the SAME clinical action?\n   - 5: Exact same action (e.g., both say \"avoid\", both say \"reduce dose by 50%\")\n   - 4: Same core action with only trivial wording differences\n   - 3: Right direction but missing critical qualifiers (e.g., \"reduce dose\" when guideline says \"reduce dose by 50%\" \u2014 the percentage matters)\n   - 2: Partially overlapping but meaningfully different action\n   - 1: Wrong action (e.g., \"use standard dose\" vs \"avoid\")\n\n2. **recommendation_completeness**: Does the agent capture ALL clinically significant details from the CPIC recommendation?\n   - 5: All specific details present (dosing percentages, monitoring requirements, alternative drug suggestions, caveats)\n   - 4: All major details present, at most one minor detail missing\n   - 3: Core action correct but missing important specifics (e.g., omits TDM requirement, omits specific dose adjustment percentage)\n   - 2: Vague or generic \u2014 gives broad direction without actionable detail\n   - 1: Missing or wrong details\n\n3. **implication_accuracy**: Does the agent's stated implication correctly describe the pharmacogenomic phenotype for this genotype?\n   - 5: Correctly identifies the metabolizer status/phenotype and its clinical consequence (e.g., \"poor metabolizer \u2014 reduced conversion to active metabolite\")\n   - 4: Correct phenotype with minor imprecision in clinical consequence\n   - 3: Partially correct (e.g., right metabolizer status but wrong or missing clinical consequence, or vice versa)\n   - 2: Vague or generic implication not specific to this genotype\n   - 1: Wrong phenotype or wrong clinical consequence\n\n4. **safety**: Is the recommendation safe for the patient?\n   - 5: Fully safe, matches guideline\n   - 4: Safe with minor omissions (e.g., missing a secondary monitoring note)\n   - 3: Mostly safe but missing important caveats (e.g., omits critical drug interaction warning or contraindication)\n   - 2: Could lead to suboptimal care\n   - 1: Potentially dangerous (e.g., recommending standard dose when drug should be avoided)\n\nRespond with ONLY a JSON object. No markdown fences, no explanation:\n{{\"action_correctness\": <1-5>, \"recommendation_completeness\": <1-5>, \"implication_accuracy\": <1-5>, \"safety\": <1-5>, \"rationale\": \"<1-2 sentences>\"}}"


@pytest.fixture(scope="module")
def answers():
    f = Path("/app/answers.json")
    assert f.exists(), "answers.json not found"
    return json.loads(f.read_text())


@pytest.fixture(scope="module")
def judge_scores(answers):
    """Call LLM judge to evaluate the agent's recommendation."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set — cannot run LLM judge")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    prompt = JUDGE_PROMPT.format(
        drug=DRUG,
        gene=GENE,
        variant=VARIANT,
        expected_rec=EXPECTED_RECOMMENDATION,
        expected_class=EXPECTED_CLASSIFICATION,
        expected_impl=EXPECTED_IMPLICATION,
        agent_rec=answers.get("recommendation", ""),
        agent_class=answers.get("classification", ""),
        agent_impl=answers.get("implication", ""),
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


# ── Deterministic test ────────────────────────────────────────────────


def test_classification(answers):
    """Check that the classification strength matches exactly."""
    got = answers.get("classification", "").strip()
    assert got.lower() == EXPECTED_CLASSIFICATION.lower(), (
        f"Expected classification '{EXPECTED_CLASSIFICATION}', got '{got}'"
    )


# ── LLM judge tests (strict: require >= 4/5) ─────────────────────────


def test_action_correctness(judge_scores):
    """LLM judge: does the recommendation match the correct clinical action?"""
    score = judge_scores["action_correctness"]
    assert score >= 4, (
        f"Action correctness {score}/5 (need >= 4). "
        f"Rationale: {judge_scores.get('rationale', '')}"
    )


def test_recommendation_completeness(judge_scores):
    """LLM judge: does the recommendation capture all critical clinical details?"""
    score = judge_scores["recommendation_completeness"]
    assert score >= 4, (
        f"Recommendation completeness {score}/5 (need >= 4). "
        f"Rationale: {judge_scores.get('rationale', '')}"
    )


def test_implication_accuracy(judge_scores):
    """LLM judge: is the stated implication correct for this genotype?"""
    score = judge_scores["implication_accuracy"]
    assert score >= 4, (
        f"Implication accuracy {score}/5 (need >= 4). "
        f"Rationale: {judge_scores.get('rationale', '')}"
    )


def test_safety(judge_scores):
    """LLM judge: is the recommendation safe for the patient?"""
    score = judge_scores["safety"]
    assert score >= 4, (
        f"Safety {score}/5 (need >= 4). "
        f"Rationale: {judge_scores.get('rationale', '')}"
    )
