import json
import re
from pathlib import Path

import pytest


EXPECTED_ACTION_CATEGORY = "standard_dosing"
EXPECTED_CLASSIFICATION = "Strong"
EXPECTED_KEY_TERMS = ["per standard dosing", "standard dosing guidelines"]
EXPECTED_RECOMMENDATION = "Use allopurinol per standard dosing guidelines"


# Action category keyword mapping
ACTION_KEYWORDS = {
    "avoid": ["contraindicated", "not recommended", "avoid", "do not use"],
    "standard_dosing": [
        "per standard dosing",
        "standard dosing",
        "at standard doses",
        "standard dose",
        "label-recommended",
    ],
    "dose_reduction": [
        "reduce dose",
        "reduced dose",
        "decrease dose",
        "decreased dose",
        "lower dose",
        "dose decrease",
        "dose reduction",
        "50% reduction",
        "50% of standard",
    ],
    "dose_increase": [
        "increase dose",
        "increased dose",
        "higher dose",
        "dose increase",
    ],
    "alternative": ["alternative", "consider other", "select alternative"],
    "monitor": ["monitor", "caution", "therapeutic drug monitoring"],
}


def classify_recommendation(text: str) -> str:
    """Classify a recommendation into an action category."""
    text_lower = text.lower()
    for category, keywords in ACTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return "other"


@pytest.fixture(scope="module")
def answers():
    f = Path("/app/answers.json")
    assert f.exists(), "answers.json not found"
    return json.loads(f.read_text())


def test_action_category(answers):
    """Check that the recommendation maps to the correct action category."""
    rec_text = answers.get("recommendation", "")
    got_category = classify_recommendation(rec_text)
    assert got_category == EXPECTED_ACTION_CATEGORY, (
        f"Expected action category '{EXPECTED_ACTION_CATEGORY}', got '{got_category}' "
        f"from recommendation: {rec_text}"
    )


def test_classification(answers):
    """Check that the classification strength matches."""
    got = answers.get("classification", "").strip()
    assert got.lower() == EXPECTED_CLASSIFICATION.lower(), (
        f"Expected classification '{EXPECTED_CLASSIFICATION}', got '{got}'"
    )


def test_key_terms(answers):
    """Check that at least one key term from CPIC rec appears in output."""
    if not EXPECTED_KEY_TERMS:
        pytest.skip("No key terms defined for this recommendation")
    # Combine all text fields from the agent's answer
    all_text = " ".join(
        [
            answers.get("recommendation", ""),
            answers.get("implication", ""),
        ]
    ).lower()
    found = [t for t in EXPECTED_KEY_TERMS if t.lower() in all_text]
    assert found, (
        f"None of the expected key terms found in agent output. "
        f"Expected one of: {EXPECTED_KEY_TERMS}"
    )
