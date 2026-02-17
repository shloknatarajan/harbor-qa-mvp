import json
from pathlib import Path

import pytest


EXPECTED = {
    "1": "b",
    "2": "d",
    "3": "a",
    "4": "b",
    "5": "d",
    "6": "c",
    "7": "b",
    "8": "d",
    "9": "b",
    "10": "b",
    "11": "b",
    "12": "a",
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
    assert got == "a", f"Q3: expected 'a', got '{got}'"


def test_question_4(answers):
    got = answers.get("4", "").strip().lower()
    assert got == "b", f"Q4: expected 'b', got '{got}'"


def test_question_5(answers):
    got = answers.get("5", "").strip().lower()
    assert got == "d", f"Q5: expected 'd', got '{got}'"


def test_question_6(answers):
    got = answers.get("6", "").strip().lower()
    assert got == "c", f"Q6: expected 'c', got '{got}'"


def test_question_7(answers):
    got = answers.get("7", "").strip().lower()
    assert got == "b", f"Q7: expected 'b', got '{got}'"


def test_question_8(answers):
    got = answers.get("8", "").strip().lower()
    assert got == "d", f"Q8: expected 'd', got '{got}'"


def test_question_9(answers):
    got = answers.get("9", "").strip().lower()
    assert got == "b", f"Q9: expected 'b', got '{got}'"


def test_question_10(answers):
    got = answers.get("10", "").strip().lower()
    assert got == "b", f"Q10: expected 'b', got '{got}'"


def test_question_11(answers):
    got = answers.get("11", "").strip().lower()
    assert got == "b", f"Q11: expected 'b', got '{got}'"


def test_question_12(answers):
    got = answers.get("12", "").strip().lower()
    assert got == "a", f"Q12: expected 'a', got '{got}'"
