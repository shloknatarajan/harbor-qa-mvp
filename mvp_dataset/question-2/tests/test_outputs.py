from pathlib import Path


def test_answer():
    answer_file = Path("/app/answer.txt")
    assert answer_file.exists(), "answer.txt not found"
    answer = answer_file.read_text().strip().lower()
    assert "washington" in answer, f"Expected 'Washington' in answer, got '{answer}'"
