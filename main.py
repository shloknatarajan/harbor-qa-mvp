"""Load environment variables and run Harbor CLI agent on a local dataset.

Example usage:
    python main.py                                                            # run chained-questions (default)
    python main.py -p cpic_zero_context -a claude-code -n 3 -l 5             # CPIC zero-context (100 tasks)
    python main.py -p cpic_zero_context_condensed -a claude-code -n 3 -l 5   # CPIC zero-context condensed (72 tasks)
    python main.py -p cpic_evidence_benchmark -a claude-code -n 3 -l 5       # CPIC evidence benchmark (106 tasks)
    python main.py -p cpic_evidence_benchmark_condensed -a claude-code -n 3 -l 5  # CPIC evidence condensed (27 tasks)
    python main.py -p pgx_drug_qa -a claude-code -n 1                        # PGx drug QA
    python main.py -p summary_qa -a claude-code -n 1                         # summary QA

Chain-aware usage (chained-questions dataset):
    python main.py -c 5                                               # run first 5 complete chains
    python main.py -c 5 -s 10                                         # run 5 chains, skipping first 10
    python main.py -t variant_chain_001000                            # run one specific chain by ID
    python main.py -t variant_chain_001000 -t variant_chain_001001   # run two specific chains

    -c / --chains : number of complete chains to run (replaces -l for chain datasets)
    -s / --skip   : number of chains to skip before selecting (offset into sorted chain list)
    -t / --chain  : specific chain ID(s) to run (can be repeated); bypasses -c / -s

    The chain dataset is always data/chained-questions. Pass -p to override.

Filtering tasks:
    python main.py -p cpic_zero_context -a claude-code -l 5                  # first 5 tasks only
    python main.py -p cpic_zero_context -a claude-code -t "dpyd*"            # glob pattern
    python main.py -p cpic_zero_context -a claude-code -x "mt_rnr1*"         # exclude tasks
"""

import re
import subprocess
import sys
import threading
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from show_results import get_latest_job_dir, show_and_save

CHAIN_DATASET = "data/chained-questions"
CHAIN_TASK_RE = re.compile(r"^(variant_chain_\d+)_(q\d+)$")


def enumerate_chains(dataset_path: str) -> dict[str, list[str]]:
    """Return a sorted dict of {chain_id: [task_name, ...]} from the dataset directory."""
    data_dir = Path(dataset_path)
    chains: dict[str, list[str]] = defaultdict(list)
    for d in data_dir.iterdir():
        if d.is_dir():
            m = CHAIN_TASK_RE.match(d.name)
            if m:
                chains[m.group(1)].append(d.name)
    return {k: sorted(v) for k, v in sorted(chains.items())}


def _continuous_save(stop_event: threading.Event):
    """Poll for the latest job directory and save results every 15 seconds."""
    last_saved = None
    while not stop_event.is_set():
        stop_event.wait(15)
        job_dir = get_latest_job_dir()
        if not job_dir:
            continue
        trial_results = sorted(job_dir.glob("*/result.json"))
        current_state = [(p, p.stat().st_mtime) for p in trial_results]
        if current_state != last_saved:
            last_saved = current_state
            try:
                show_and_save(job_dir)
            except Exception as e:
                print(f"  (continuous save error: {e})")


def _pop_arg(args: list[str], *flags: str) -> str | None:
    """Remove a flag and its value from args in-place, return the value or None."""
    for flag in flags:
        if flag in args:
            idx = args.index(flag)
            args.pop(idx)          # remove the flag
            if idx < len(args):
                return args.pop(idx)  # remove and return the value
    return None


def main():
    load_dotenv()

    args = list(sys.argv[1:])

    # Inject default agent if not specified
    if not any(a in args for a in ("-a", "--agent")):
        args = ["-a", "claude-code"] + args

    # --- Determine dataset path ---
    if not any(a in args for a in ("-p", "--path", "--dataset")):
        dataset_path = CHAIN_DATASET
        args = ["-p", CHAIN_DATASET] + args
    else:
        # Find the value after -p / --path / --dataset
        dataset_path = None
        for flag in ("-p", "--path", "--dataset"):
            if flag in args:
                idx = args.index(flag)
                if idx + 1 < len(args):
                    dataset_path = args[idx + 1]
                break

    # --- Chain-aware argument handling ---
    # Only applies when running the chain dataset
    is_chain_dataset = dataset_path and Path(dataset_path).name == Path(CHAIN_DATASET).name

    # Pull our custom chain flags out of args before passing to harbor
    n_chains = _pop_arg(args, "-c", "--chains")
    skip_chains = _pop_arg(args, "-s", "--skip")

    # Collect explicit chain IDs: -t / --chain (our custom flag, NOT harbor's -t)
    explicit_chains: list[str] = []
    while True:
        val = _pop_arg(args, "-t", "--chain")
        if val is None:
            break
        explicit_chains.append(val)

    if is_chain_dataset:
        all_chains = enumerate_chains(dataset_path)

        if explicit_chains:
            # Run only the specified chain IDs
            selected_task_names: list[str] = []
            for chain_id in explicit_chains:
                tasks = all_chains.get(chain_id)
                if tasks is None:
                    print(f"Warning: chain '{chain_id}' not found in {dataset_path}")
                    continue
                selected_task_names.extend(tasks)
        else:
            # Select a slice of chains by position
            skip = int(skip_chains) if skip_chains else 0
            limit = int(n_chains) if n_chains else None
            chain_ids = list(all_chains.keys())[skip : (skip + limit) if limit else None]
            selected_task_names = [t for cid in chain_ids for t in all_chains[cid]]
            print(
                f"Selected {len(chain_ids)} chain(s) "
                f"(tasks {skip * 4 + 1}–{skip * 4 + len(selected_task_names)}): "
                f"{chain_ids[0]} … {chain_ids[-1]}" if chain_ids else "No chains selected."
            )

        # Pass each task name as an explicit harbor --task-name flag
        for task_name in selected_task_names:
            args.extend(["--task-name", task_name])

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
