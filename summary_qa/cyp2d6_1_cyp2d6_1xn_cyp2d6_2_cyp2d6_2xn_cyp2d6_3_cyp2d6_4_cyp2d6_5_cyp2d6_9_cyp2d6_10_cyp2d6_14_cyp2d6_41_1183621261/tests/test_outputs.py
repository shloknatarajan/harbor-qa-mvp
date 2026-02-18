import json
from pathlib import Path

import pytest


EXPECTED_DRUGS = ["paroxetine"]
EXPECTED_PHENOTYPES = []
EXPECTED_RELEVANT_PAPER_COUNT = 2


@pytest.fixture(scope="module")
def answers():
    f = Path("/app/answers.json")
    assert f.exists(), "answers.json not found"
    return json.loads(f.read_text())


def normalize(items: list[str]) -> set[str]:
    """Normalize a list of strings to lowercase stripped set."""
    return {s.strip().lower() for s in items if s.strip()}


def test_drugs_recall(answers):
    """Check that all expected drugs are found (recall)."""
    got = normalize(answers.get("drugs", []))
    expected = set(EXPECTED_DRUGS)
    missing = expected - got
    assert not missing, f"Missing drugs: {missing}. Got: {sorted(got)}"


def test_phenotypes_recall(answers):
    """Check that all expected phenotypes are found (recall)."""
    got = normalize(answers.get("phenotypes", []))
    expected = set(EXPECTED_PHENOTYPES)
    missing = expected - got
    assert not missing, f"Missing phenotypes: {missing}. Got: {sorted(got)}"


def test_relevant_paper_count(answers):
    """Check the relevant paper count is correct."""
    got = answers.get("relevant_paper_count", -1)
    assert got == EXPECTED_RELEVANT_PAPER_COUNT, (
        f"Expected {EXPECTED_RELEVANT_PAPER_COUNT} relevant papers, got {got}"
    )
