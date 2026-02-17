import json
from pathlib import Path

import pytest


EXPECTED = {
    "1": "a",
    "2": "c",
    "3": "d",
    "4": "b",
}


@pytest.fixture(scope="module")
def answers():
    f = Path("/app/answers.json")
    assert f.exists(), "answers.json not found"
    return json.loads(f.read_text())


def test_question_1(answers):
    got = answers.get("1", "").strip().lower()
    assert got == "a", f"Q1: expected 'a', got '{got}'"


def test_question_2(answers):
    got = answers.get("2", "").strip().lower()
    assert got == "c", f"Q2: expected 'c', got '{got}'"


def test_question_3(answers):
    got = answers.get("3", "").strip().lower()
    assert got == "d", f"Q3: expected 'd', got '{got}'"


def test_question_4(answers):
    got = answers.get("4", "").strip().lower()
    assert got == "b", f"Q4: expected 'b', got '{got}'"
