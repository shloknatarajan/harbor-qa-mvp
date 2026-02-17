import json
from pathlib import Path

import pytest


EXPECTED = {
    "1": "a",
    "2": "d",
    "3": "b",
    "4": "b",
    "5": "a",
    "6": "c",
    "7": "c",
    "8": "d",
    "9": "c",
    "10": "d",
    "11": "a",
    "12": "b",
    "13": "a",
    "14": "c",
    "15": "d",
    "16": "c",
    "17": "c",
    "18": "c",
    "19": "b",
    "20": "b",
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
    assert got == "d", f"Q2: expected 'd', got '{got}'"


def test_question_3(answers):
    got = answers.get("3", "").strip().lower()
    assert got == "b", f"Q3: expected 'b', got '{got}'"


def test_question_4(answers):
    got = answers.get("4", "").strip().lower()
    assert got == "b", f"Q4: expected 'b', got '{got}'"


def test_question_5(answers):
    got = answers.get("5", "").strip().lower()
    assert got == "a", f"Q5: expected 'a', got '{got}'"


def test_question_6(answers):
    got = answers.get("6", "").strip().lower()
    assert got == "c", f"Q6: expected 'c', got '{got}'"


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
    assert got == "d", f"Q10: expected 'd', got '{got}'"


def test_question_11(answers):
    got = answers.get("11", "").strip().lower()
    assert got == "a", f"Q11: expected 'a', got '{got}'"


def test_question_12(answers):
    got = answers.get("12", "").strip().lower()
    assert got == "b", f"Q12: expected 'b', got '{got}'"


def test_question_13(answers):
    got = answers.get("13", "").strip().lower()
    assert got == "a", f"Q13: expected 'a', got '{got}'"


def test_question_14(answers):
    got = answers.get("14", "").strip().lower()
    assert got == "c", f"Q14: expected 'c', got '{got}'"


def test_question_15(answers):
    got = answers.get("15", "").strip().lower()
    assert got == "d", f"Q15: expected 'd', got '{got}'"


def test_question_16(answers):
    got = answers.get("16", "").strip().lower()
    assert got == "c", f"Q16: expected 'c', got '{got}'"


def test_question_17(answers):
    got = answers.get("17", "").strip().lower()
    assert got == "c", f"Q17: expected 'c', got '{got}'"


def test_question_18(answers):
    got = answers.get("18", "").strip().lower()
    assert got == "c", f"Q18: expected 'c', got '{got}'"


def test_question_19(answers):
    got = answers.get("19", "").strip().lower()
    assert got == "b", f"Q19: expected 'b', got '{got}'"


def test_question_20(answers):
    got = answers.get("20", "").strip().lower()
    assert got == "b", f"Q20: expected 'b', got '{got}'"
