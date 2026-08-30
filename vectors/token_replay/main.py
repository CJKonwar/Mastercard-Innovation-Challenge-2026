#!/usr/bin/env python3
"""
main.py — runs the full Agent Token Replay pipeline end-to-end, in order:

  1. generate/generator.py         -> regenerates data/sessions.csv
  2. defend/evaluate_layer1.py     -> Layer 1 (deterministic) baseline report
  3. defend/train_layer2.py        -> Layer 2 (ML) standalone report
  4. defend/evaluate_pipeline.py   -> combined Layer1+Layer2 system score
  5. defend/save_model.py          -> persists the trained Layer 2 model to
                                       outputs/ (layer2_model.txt, .pkl)
  6. defend/mine_failures.py       -> OPTIONAL, off by default (--with-mining)

Each script is run exactly as it was designed to be run by hand: as a
subprocess with its own folder as the working directory, using this same
Python interpreter. Nothing in generate/ or defend/ is modified or imported
directly -- this file only orchestrates them, so it's safe to drop in
without touching anyone else's code.

Run from the repo root:
    python main.py                   # full run, ends with a saved model artifact
    python main.py --with-mining     # also runs mine_failures.py at the end
    python main.py --skip-generate   # reuse the existing data/sessions.csv instead of regenerating it
    python main.py --skip-save-model # skip persisting the model artifact

Exits non-zero and stops immediately if any step fails, so a broken step is
never silently skipped.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# Each step: (human-readable name, folder relative to repo root, script filename)
STEPS = [
    ("Generate: build synthetic dataset", "generate", "generator.py"),
    ("Defend Layer 1: deterministic verifier baseline", "defend", "evaluate_layer1.py"),
    ("Defend Layer 2: train + evaluate ML risk scorer", "defend", "train_layer2.py"),
    ("Combined pipeline: Layer 1 -> Layer 2 system score", "defend", "evaluate_pipeline.py"),
    ("Persist Layer 2 model artifact", "defend", "save_model.py"),
]

OPTIONAL_MINING_STEP = ("Feedback loop: mine Layer 2 false negatives", "defend", "mine_failures.py")


def run_step(name, folder, script):
    """Run one stage in its own directory, since stage scripts use relative paths."""
    folder_path = REPO_ROOT / folder
    script_path = folder_path / script

    if not script_path.exists():
        print(f"\n[SKIP] {script} not found at {script_path} -- check the repo layout.")
        return False

    print("\n" + "=" * 78)
    print(f"STEP: {name}")
    print(f"      running {script}  (cwd={folder_path})")
    print("=" * 78)

    started = time.time()
    # cwd=folder_path reproduces `cd generate && python generator.py` etc. --
    # this matters because these scripts use relative imports (e.g. `import
    # schema`) and relative paths (e.g. "../data/sessions.csv").
    result = subprocess.run([sys.executable, script], cwd=folder_path)
    elapsed = time.time() - started

    if result.returncode != 0:
        print(f"\n[FAILED] {script} exited with code {result.returncode} after {elapsed:.1f}s.")
        return False

    print(f"\n[OK] {script} finished in {elapsed:.1f}s.")
    return True


def main():
    """Run the pipeline end to end and summarise which stages passed."""
    parser = argparse.ArgumentParser(description="Run the Agent Token Replay pipeline end-to-end.")
    parser.add_argument(
        "--skip-generate", action="store_true",
        help="Skip regenerating data/sessions.csv; reuse whatever is already there.",
    )
    parser.add_argument(
        "--skip-save-model", action="store_true",
        help="Skip persisting the trained Layer 2 model artifact to outputs/.",
    )
    parser.add_argument(
        "--with-mining", action="store_true",
        help="Also run defend/mine_failures.py at the end (diagnostic, not part of the scored pipeline).",
    )
    args = parser.parse_args()

    steps = STEPS[1:] if args.skip_generate else STEPS
    if args.skip_save_model:
        steps = [s for s in steps if s[2] != "save_model.py"]
    if args.with_mining:
        steps = steps + [OPTIONAL_MINING_STEP]

    print("Agent Token Replay -- full pipeline run")
    print(f"Repo root: {REPO_ROOT}")
    print(f"Python:    {sys.executable}")
    if args.skip_generate:
        print("(--skip-generate: reusing existing data/sessions.csv)")
    if args.skip_save_model:
        print("(--skip-save-model: not persisting the model artifact)")
    if args.with_mining:
        print("(--with-mining: will also run mine_failures.py)")

    overall_start = time.time()
    completed = []

    for name, folder, script in steps:
        ok = run_step(name, folder, script)
        completed.append((name, ok))
        if not ok:
            break

    total_elapsed = time.time() - overall_start

    print("\n" + "=" * 78)
    print("PIPELINE SUMMARY")
    print("=" * 78)
    for name, ok in completed:
        print(f"  [{'OK' if ok else 'FAILED'}] {name}")

    if all(ok for _, ok in completed) and len(completed) == len(steps):
        print(f"\nAll steps completed successfully in {total_elapsed:.1f}s.")
        print("See the 'COMBINED PIPELINE' section above for the headline")
        print("precision/recall/F1/AUC numbers for the solution walkthrough.")
        sys.exit(0)
    else:
        print(f"\nStopped after {total_elapsed:.1f}s due to a failure above.")
        print("Fix the failing step and re-run -- earlier steps don't need to")
        print("be repeated if their output (e.g. data/sessions.csv) is unchanged;")
        print("use --skip-generate to skip regenerating the dataset.")
        sys.exit(1)


if __name__ == "__main__":
    main()
