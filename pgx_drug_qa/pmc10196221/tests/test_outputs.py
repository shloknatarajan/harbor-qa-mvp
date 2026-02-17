import json
from pathlib import Path

import pytest


EXPECTED = {
    "1": "c",
    "2": "a",
    "3": "c",
    "4": "b",
    "5": "a",
    "6": "b",
    "7": "c",
    "8": "d",
    "9": "c",
    "10": "c",
    "11": "a",
    "12": "c",
    "13": "a",
    "14": "a",
}


@pytest.fixture(scope='module')
def answers():
    f = Path("/app/answers.json")
    assert f.exists(), "answers.json not found"
    return json.loads(f.read_text())


def test_question_1(answers):
    got = answers.get("1", "").strip().lower()
    assert got == "c", f"Q1: expected 'c', got '{got}'"


def test_question_2(answers):
    got = answers.get("2", "").strip().lower()
    assert got == "a", f"Q2: expected 'a', got '{got}'"


def test_question_3(answers):
    got = answers.get("3", "").strip().lower()
    assert got == "c", f"Q3: expected 'c', got '{got}'"


def test_question_4(answers):
    got = answers.get("4", "").strip().lower()
    assert got == "b", f"Q4: expected 'b', got '{got}'"


def test_question_5(answers):
    got = answers.get("5", "").strip().lower()
    assert got == "a", f"Q5: expected 'a', got '{got}'"


def test_question_6(answers):
    got = answers.get("6", "").strip().lower()
    assert got == "b", f"Q6: expected 'b', got '{got}'"


def test_question_7(answers):
    got = answers.get("7", "").strip().lower()
    assert got == "c", f"Q7: expected 'c', got '{got}'"


def test_question_8(answers):
    got = answers.get("8", "").strip().lower()
    assert got == "d", f"Q8: expected 'd', got '{got}'"


def test_question_9(answers):
    got = answers.get("9", "").strip().lower()
    assert got == "c", f"Q9: expected 'c', got '{got}'"


def test_question_10(answers):
    got = answers.get("10", "").strip().lower()
    assert got == "c", f"Q10: expected 'c', got '{got}'"


def test_question_11(answers):
    got = answers.get("11", "").strip().lower()
    assert got == "a", f"Q11: expected 'a', got '{got}'"


def test_question_12(answers):
    got = answers.get("12", "").strip().lower()
    assert got == "c", f"Q12: expected 'c', got '{got}'"


def test_question_13(answers):
    got = answers.get("13", "").strip().lower()
    assert got == "a", f"Q13: expected 'a', got '{got}'"


def test_question_14(answers):
    got = answers.get("14", "").strip().lower()
    assert got == "a", f"Q14: expected 'a', got '{got}'"

