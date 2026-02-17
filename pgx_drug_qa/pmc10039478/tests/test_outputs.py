import json
from pathlib import Path

import pytest


EXPECTED = {
    "1": "b",
    "2": "d",
    "3": "d",
    "4": "b",
    "5": "c",
    "6": "d",
    "7": "c",
    "8": "a",
    "9": "d",
    "10": "a",
    "11": "a",
    "12": "c",
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
    assert got == "d", f"Q2: expected 'd', got '{got}'"


def test_question_3(answers):
    got = answers.get("3", "").strip().lower()
    assert got == "d", f"Q3: expected 'd', got '{got}'"


def test_question_4(answers):
    got = answers.get("4", "").strip().lower()
    assert got == "b", f"Q4: expected 'b', got '{got}'"


def test_question_5(answers):
    got = answers.get("5", "").strip().lower()
    assert got == "c", f"Q5: expected 'c', got '{got}'"


def test_question_6(answers):
    got = answers.get("6", "").strip().lower()
    assert got == "d", f"Q6: expected 'd', got '{got}'"


def test_question_7(answers):
    got = answers.get("7", "").strip().lower()
    assert got == "c", f"Q7: expected 'c', got '{got}'"


def test_question_8(answers):
    got = answers.get("8", "").strip().lower()
    assert got == "a", f"Q8: expected 'a', got '{got}'"


def test_question_9(answers):
    got = answers.get("9", "").strip().lower()
    assert got == "d", f"Q9: expected 'd', got '{got}'"


def test_question_10(answers):
    got = answers.get("10", "").strip().lower()
    assert got == "a", f"Q10: expected 'a', got '{got}'"


def test_question_11(answers):
    got = answers.get("11", "").strip().lower()
    assert got == "a", f"Q11: expected 'a', got '{got}'"


def test_question_12(answers):
    got = answers.get("12", "").strip().lower()
    assert got == "c", f"Q12: expected 'c', got '{got}'"
