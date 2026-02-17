from pathlib import Path


def test_answer():
    answer_file = Path("/app/answer.txt")
    assert answer_file.exists(), "answer.txt not found"
    answer = answer_file.read_text().strip()
    assert answer == "4", f"Expected '4', got '{answer}'"
