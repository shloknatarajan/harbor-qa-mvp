"""Display results from a Harbor job run and save to run_results/.

Can be used standalone or called automatically from main.py after a job.

Usage:
    python show_results.py                            # show latest job
    python show_results.py jobs/2026-02-17__10-24-05  # show specific job
    python show_results.py --all                      # show all jobs
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

RESULTS_DIR = Path("run_results")


def _get_task_dir(result: dict) -> Path | None:
    source = result.get("source")
    task_name = result.get("task_name")
    if not source or not task_name:
        return None
    task_dir = Path(source) / task_name
    return task_dir if task_dir.exists() else None


def parse_answer_options(result: dict) -> dict[str, dict[str, str]]:
    """Parse answer options from instruction.md.

    Returns {question_number: {letter: text}}, e.g.
    {"1": {"a": "temsirolimus", "b": "sirolimus", ...}, "2": {...}}
    For single-question tasks, returns {"1": {letter: text}}.
    """
    task_dir = _get_task_dir(result)
    if not task_dir:
        return {}
    instruction = task_dir / "instruction.md"
    if not instruction.exists():
        return {}
    text = instruction.read_text()

    # Detect multi-question format (## Question N)
    q_headers = list(re.finditer(r"^## Question (\d+)", text, re.MULTILINE))
    if q_headers:
        result_opts: dict[str, dict[str, str]] = {}
        for i, hdr in enumerate(q_headers):
            q_num = hdr.group(1)
            start = hdr.end()
            end = q_headers[i + 1].start() if i + 1 < len(q_headers) else len(text)
            section = text[start:end]
            opts = {}
            for m in re.finditer(r"^- ([a-z])\)\s+(.+)$", section, re.MULTILINE):
                opts[m.group(1)] = m.group(2).strip()
            result_opts[q_num] = opts
        return result_opts

    # Single-question fallback
    options = {}
    for m in re.finditer(r"^- ([a-z])\)\s+(.+)$", text, re.MULTILINE):
        options[m.group(1)] = m.group(2).strip()
    return {"1": options} if options else {}


def extract_correct_answers(result: dict) -> dict[str, str]:
    """Extract correct answer letters from the task's test file.

    Returns a dict like {"1": "c", "2": "a"} for multi-question tasks,
    or {"1": "c"} for single-question tasks.
    """
    task_dir = _get_task_dir(result)
    if not task_dir:
        return {}
    test_file = task_dir / "tests" / "test_outputs.py"
    if test_file.exists():
        content = test_file.read_text()
        # Multi-question: EXPECTED = {"1": "c", "2": "a"}
        m = re.search(r"EXPECTED\s*=\s*(\{[^}]+\})", content)
        if m:
            try:
                # Remove trailing commas before closing brace (Python dict literal)
                raw = m.group(1).replace("'", '"')
                raw = re.sub(r",\s*}", "}", raw)
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        # Single-question: assert answer == "c"
        m = re.search(r'assert\s+answer\s*==\s*["\'](\w+)["\']', content)
        if m:
            return {"1": m.group(1)}
    return {}


def _is_summary_qa_task(result: dict) -> bool:
    """Check if this is a summary_qa task (drugs/phenotypes/paper count)."""
    task_dir = _get_task_dir(result)
    if not task_dir:
        return False
    test_file = task_dir / "tests" / "test_outputs.py"
    if not test_file.exists():
        return False
    content = test_file.read_text()
    return "EXPECTED_DRUGS" in content


def extract_summary_qa_expected(result: dict) -> dict | None:
    """Extract expected drugs, phenotypes, and paper count from summary_qa test file."""
    task_dir = _get_task_dir(result)
    if not task_dir:
        return None
    test_file = task_dir / "tests" / "test_outputs.py"
    if not test_file.exists():
        return None
    content = test_file.read_text()

    expected = {}
    m = re.search(r"EXPECTED_DRUGS\s*=\s*(\[.*?\])", content)
    if m:
        try:
            expected["drugs"] = json.loads(m.group(1).replace("'", '"'))
        except json.JSONDecodeError:
            expected["drugs"] = []

    m = re.search(r"EXPECTED_PHENOTYPES\s*=\s*(\[.*?\])", content)
    if m:
        try:
            expected["phenotypes"] = json.loads(m.group(1).replace("'", '"'))
        except json.JSONDecodeError:
            expected["phenotypes"] = []

    m = re.search(r"EXPECTED_RELEVANT_PAPER_COUNT\s*=\s*(\d+)", content)
    if m:
        expected["relevant_paper_count"] = int(m.group(1))

    return expected if expected else None


def extract_summary_qa_agent_answers(trial_dir: Path) -> dict | None:
    """Extract the agent's summary_qa answers from its log."""
    log_file = trial_dir / "agent" / "claude-code.txt"
    if not log_file.exists():
        return None
    content = log_file.read_text()

    # Look for Write tool with /app/answers.json
    for m in re.finditer(
        r'"(?:file_path|filePath)"\s*:\s*"/app/answers\.json"\s*,\s*"content"\s*:\s*"((?:[^"\\]|\\.)*)"',
        content,
    ):
        try:
            raw = m.group(1).replace("\\n", "\n").replace('\\"', '"')
            parsed = json.loads(raw)
            if "drugs" in parsed or "phenotypes" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def format_summary_qa_comparison(
    expected: dict, agent: dict | None, lines: list[str]
):
    """Append summary_qa comparison lines showing drugs/phenotypes/count."""
    if agent is None:
        lines.append("        (no agent answers extracted)")
        return

    # Drugs comparison
    exp_drugs = set(expected.get("drugs", []))
    got_drugs = {s.strip().lower() for s in agent.get("drugs", []) if s.strip()}
    drug_found = exp_drugs & got_drugs
    drug_missing = exp_drugs - got_drugs
    drug_extra = got_drugs - exp_drugs
    drug_icon = "✓" if not drug_missing else "✗"
    lines.append(
        f"        Drugs {drug_icon}: {len(drug_found)}/{len(exp_drugs)} recall"
        + (f"  missing: {sorted(drug_missing)}" if drug_missing else "")
        + (f"  extra: {sorted(drug_extra)}" if drug_extra else "")
    )

    # Phenotypes comparison
    exp_pheno = set(expected.get("phenotypes", []))
    got_pheno = {s.strip().lower() for s in agent.get("phenotypes", []) if s.strip()}
    pheno_found = exp_pheno & got_pheno
    pheno_missing = exp_pheno - got_pheno
    pheno_extra = got_pheno - exp_pheno
    pheno_icon = "✓" if not pheno_missing else "✗"
    lines.append(
        f"        Pheno {pheno_icon}: {len(pheno_found)}/{len(exp_pheno)} recall"
        + (f"  missing: {sorted(pheno_missing)}" if pheno_missing else "")
        + (f"  extra: {sorted(pheno_extra)}" if pheno_extra else "")
    )

    # Paper count comparison
    exp_count = expected.get("relevant_paper_count")
    got_count = agent.get("relevant_paper_count", -1)
    if exp_count is not None:
        count_icon = "✓" if got_count == exp_count else "✗"
        lines.append(
            f"        Count {count_icon}: agent={got_count} expected={exp_count}"
        )


def extract_agent_answers(trial_dir: Path) -> dict[str, str]:
    """Extract the agent's answers from its log/trajectory.

    Returns a dict like {"1": "c", "2": "a"} for multi-question tasks,
    or {"1": "c"} for single-question tasks.
    """
    log_file = trial_dir / "agent" / "claude-code.txt"
    if not log_file.exists():
        return {}
    content = log_file.read_text()

    # Multi-question: Write tool with /app/answers.json content
    # Matches both "file_path" (tool input) and "filePath" (tool result)
    for m in re.finditer(
        r'"(?:file_path|filePath)"\s*:\s*"/app/answers\.json"\s*,\s*"content"\s*:\s*"((?:[^"\\]|\\.)*)"',
        content,
    ):
        try:
            raw = m.group(1).replace("\\n", "\n").replace('\\"', '"')
            return json.loads(raw)
        except json.JSONDecodeError:
            continue

    # Single-question: Write tool with /app/answer.txt content
    for m in re.finditer(
        r'"(?:file_path|filePath)"\s*:\s*"/app/answer\.txt"\s*,\s*"content"\s*:\s*"((?:[^"\\]|\\.)*)"',
        content,
    ):
        return {"1": m.group(1).strip()}

    # Fallback: echo commands
    for m in re.finditer(
        r'echo\s+(?:\\?"?|\'?)(\w)(?:\\?"?|\'?)\s*>\s*/app/answer\.txt', content
    ):
        return {"1": m.group(1).strip()}

    return {}


def format_answer(letter: str | None, options: dict[str, str]) -> str:
    """Format an answer as '(c) exenatide' or just the letter if no options."""
    if not letter:
        return "?"
    text = options.get(letter.lower())
    if text:
        return f"({letter}) {text}"
    return letter


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def format_duration(start: str, end: str) -> str:
    try:
        t0 = datetime.fromisoformat(start.rstrip("Z"))
        t1 = datetime.fromisoformat(end.rstrip("Z"))
    except ValueError:
        return "?"
    total = int((t1 - t0).total_seconds())
    if total < 60:
        return f"{total}s"
    return f"{total // 60}m {total % 60}s"


def format_trial(trial_dir: Path) -> tuple[list[str], dict]:
    lines = []
    result = load_json(trial_dir / "result.json")
    if result is None:
        lines.append(f"  {trial_dir.name}: no result.json found")
        return lines, {"status": "missing"}

    task_name = result.get("task_name", trial_dir.name)
    reward = None
    if result.get("verifier_result") and result["verifier_result"].get("rewards"):
        reward = result["verifier_result"]["rewards"].get("reward")

    exc = result.get("exception_info")
    duration = "?"
    if result.get("started_at") and result.get("finished_at"):
        duration = format_duration(result["started_at"], result["finished_at"])

    if exc:
        icon, status = "FAIL", "error"
    elif reward is not None and reward >= 1.0:
        icon, status = "PASS", "pass"
    elif reward is not None and reward > 0:
        icon, status = "PARTIAL", "partial"
    elif reward is not None:
        icon, status = "FAIL", "fail"
    else:
        icon, status = "????", "unknown"

    tokens = ""
    if result.get("agent_result"):
        ar = result["agent_result"]
        tokens = f"  tokens: {ar.get('n_input_tokens', 0):,} in / {ar.get('n_output_tokens', 0):,} out"

    phases = []
    for phase_name, phase_key in [
        ("env", "environment_setup"),
        ("setup", "agent_setup"),
        ("agent", "agent_execution"),
        ("verify", "verifier"),
    ]:
        phase = result.get(phase_key)
        if phase and phase.get("started_at") and phase.get("finished_at"):
            phases.append(
                f"{phase_name}={format_duration(phase['started_at'], phase['finished_at'])}"
            )

    reward_str = f"reward={reward}" if reward is not None else "no reward"
    lines.append(f"  [{icon}] {task_name:<20} {reward_str:<14} {duration:<10}{tokens}")
    if phases:
        lines.append(f"        ({', '.join(phases)})")

    if exc:
        exc_type = exc.get("exception_type", "Unknown")
        exc_msg = exc.get("exception_message", "")
        if len(exc_msg) > 120:
            exc_msg = exc_msg[:120] + "..."
        lines.append(f"        error: {exc_type}: {exc_msg}")

    # Summary QA tasks: show drugs/phenotypes/count comparison
    if _is_summary_qa_task(result):
        expected_sq = extract_summary_qa_expected(result)
        agent_sq = extract_summary_qa_agent_answers(trial_dir)
        if expected_sq:
            format_summary_qa_comparison(expected_sq, agent_sq, lines)
    else:
        # MCQ tasks: show question-by-question comparison
        options_by_q = parse_answer_options(result)
        agent_answers = extract_agent_answers(trial_dir)
        correct_answers = extract_correct_answers(result)
        all_q_nums = sorted(set(agent_answers) | set(correct_answers))
        if all_q_nums:
            for q in all_q_nums:
                q_options = options_by_q.get(q, {})
                agent_str = format_answer(agent_answers.get(q), q_options)
                correct_str = format_answer(correct_answers.get(q), q_options)
                match = (
                    "✓"
                    if agent_answers.get(q, "").lower()
                    == correct_answers.get(q, "").lower()
                    else "✗"
                )
                lines.append(
                    f"        Q{q}: {match}  model: {agent_str}  |  expected: {correct_str}"
                )

    return lines, {"status": status, "reward": reward}


def format_job(job_dir: Path) -> str:
    lines = []
    result = load_json(job_dir / "result.json")
    config = load_json(job_dir / "config.json")

    lines.append(f"\n{'=' * 70}")
    lines.append(f"Job: {job_dir.name}")
    lines.append(f"{'=' * 70}")

    if config:
        datasets = [d.get("path", "?") for d in config.get("datasets", [])]
        agents = [a.get("name", "?") for a in config.get("agents", [])]
        lines.append(f"  Dataset:  {', '.join(datasets)}")
        lines.append(f"  Agent:    {', '.join(agents)}")

    if result:
        duration = "?"
        if result.get("started_at") and result.get("finished_at"):
            duration = format_duration(result["started_at"], result["finished_at"])
        n_trials = result.get("n_total_trials", "?")
        n_errors = result.get("stats", {}).get("n_errors", 0)
        lines.append(
            f"  Trials:   {n_trials}  |  Errors: {n_errors}  |  Duration: {duration}"
        )

        for eval_name, eval_data in result.get("stats", {}).get("evals", {}).items():
            metrics = eval_data.get("metrics", [])
            mean = metrics[0].get("mean", "?") if metrics else "?"
            lines.append(f"  Eval:     {eval_name}  ->  mean reward = {mean}")
    else:
        lines.append("  (no job-level result.json)")

    lines.append(f"\n  {'─' * 60}")
    lines.append("  Trials:")

    trial_dirs = sorted(
        d for d in job_dir.iterdir() if d.is_dir() and (d / "result.json").exists()
    )

    if not trial_dirs:
        lines.append("  (no trial results found)")
        return "\n".join(lines)

    stats = {"pass": 0, "fail": 0, "error": 0, "partial": 0, "unknown": 0, "missing": 0}
    for td in trial_dirs:
        trial_lines, info = format_trial(td)
        lines.extend(trial_lines)
        stats[info["status"]] = stats.get(info["status"], 0) + 1

    lines.append(
        f"\n  Summary: {stats['pass']} passed, {stats['fail'] + stats['error']} failed, "
        f"{stats.get('partial', 0)} partial"
    )
    return "\n".join(lines)


def get_latest_job_dir() -> Path | None:
    jobs_dir = Path("jobs")
    if not jobs_dir.exists():
        return None
    dirs = sorted(d for d in jobs_dir.iterdir() if d.is_dir())
    return dirs[-1] if dirs else None


def show_and_save(job_dir: Path):
    output = format_job(job_dir)
    print(output)

    RESULTS_DIR.mkdir(exist_ok=True)
    out_file = RESULTS_DIR / f"{job_dir.name}.txt"
    out_file.write_text(output.strip() + "\n")
    print(f"\n  (saved to {out_file})")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--all":
            jobs_dir = Path("jobs")
            job_dirs = sorted(jobs_dir.iterdir()) if jobs_dir.exists() else []
            if not job_dirs:
                print("No jobs found in jobs/")
                return
            for jd in job_dirs:
                if jd.is_dir():
                    show_and_save(jd)
            return
        else:
            job_path = Path(arg)
            if not job_path.exists():
                print(f"Job directory not found: {arg}")
                sys.exit(1)
            show_and_save(job_path)
            return

    job_dir = get_latest_job_dir()
    if job_dir is None:
        print("No jobs found.")
        sys.exit(1)
    show_and_save(job_dir)


if __name__ == "__main__":
    main()
