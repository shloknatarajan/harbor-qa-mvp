"""Load environment variables and run Harbor CLI agent on a local dataset."""

import subprocess
import sys

from dotenv import load_dotenv


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


if __name__ == "__main__":
    main()
