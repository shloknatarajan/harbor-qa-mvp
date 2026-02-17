"""Load environment variables and run Harbor CLI agent on a local dataset.

Example usage:
    python main.py                                          # run mvp_dataset (default)
    python main.py -p mvp_pgx -a claude-code -n 1           # run mvp_pgx dataset
    python main.py -p pgx_drug_qa -a claude-code -n 1       # run pgx_drug_qa (100 PMCIDs)
    python main.py -p mvp_dataset -a claude-code -n 2       # run 2 attempts
"""

import subprocess
import sys

from dotenv import load_dotenv

from show_results import get_latest_job_dir, show_and_save


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
    subprocess.run(cmd, check=True)

    job_dir = get_latest_job_dir()
    if job_dir:
        show_and_save(job_dir)


if __name__ == "__main__":
    main()
