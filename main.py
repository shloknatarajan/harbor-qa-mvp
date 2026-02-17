"""Load environment variables and run Harbor CLI agent on a local dataset.

Example usage:
    python main.py                                          # run mvp_dataset (default)
    python main.py -p mvp_pgx -a claude-code -n 1           # run mvp_pgx dataset
    python main.py -p pgx_drug_qa -a claude-code -n 1       # run pgx_drug_qa (100 PMCIDs)
    python main.py -p mvp_dataset -a claude-code -n 2       # run 2 attempts

Filtering tasks:
    python main.py -p pgx_drug_qa -a claude-code -l 5                       # first 5 tasks only
    python main.py -p pgx_drug_qa -a claude-code -t pmc10298263             # specific task(s)
    python main.py -p pgx_drug_qa -a claude-code -x pmc10298263             # exclude task(s)
    python main.py -p pgx_drug_qa -a claude-code -t "pmc103*" -l 3          # glob + limit
"""

import subprocess
import sys
import threading
import time

from dotenv import load_dotenv

from show_results import get_latest_job_dir, show_and_save


def _continuous_save(stop_event: threading.Event):
    """Poll for the latest job directory and save results every 15 seconds."""
    last_saved = None
    while not stop_event.is_set():
        stop_event.wait(15)
        job_dir = get_latest_job_dir()
        if not job_dir:
            continue
        # Check if any trial results have changed
        trial_results = sorted(job_dir.glob("*/result.json"))
        current_state = [(p, p.stat().st_mtime) for p in trial_results]
        if current_state != last_saved:
            last_saved = current_state
            try:
                show_and_save(job_dir)
            except Exception as e:
                print(f"  (continuous save error: {e})")


def main():
    load_dotenv()

    args = sys.argv[1:] or [
        "-p",
        "mvp_dataset",
        "-a",
        "claude-code",
        "-n",
        "1",
    ]

    cmd = ["harbor", "run", *args]
    print(f"Running: {' '.join(cmd)}")

    # Start continuous result saving in background
    stop_event = threading.Event()
    saver = threading.Thread(target=_continuous_save, args=(stop_event,), daemon=True)
    saver.start()

    try:
        subprocess.run(cmd, check=True)
    finally:
        stop_event.set()
        saver.join(timeout=5)

    # Final save
    job_dir = get_latest_job_dir()
    if job_dir:
        show_and_save(job_dir)


if __name__ == "__main__":
    main()
