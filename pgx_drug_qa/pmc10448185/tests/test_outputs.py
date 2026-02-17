import json
from pathlib import Path

import pytest


EXPECTED = {
    "1": "b",
    "2": "b",
}


@pytest.fixture(scope="module")
def answers():
    f = Path("/app/answers.json")
    assert f.exists(), "answers.json not found"
    return json.loads(f.read_text())


def test_question_1(answers):
    got = answers.get("1", "").strip().lower()
    assert got == "b", f"Q1: expected 'b', got '{got}'"


def test_question_2(answers):
    got = answers.get("2", "").strip().lower()
    assert got == "b", f"Q2: expected 'b', got '{got}'"
