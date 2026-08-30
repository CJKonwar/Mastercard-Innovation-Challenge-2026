"""What each vector accepts from the UI, and the exact CLI command that expresses it -
the same command a user would type themselves, run through the same root dispatcher."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable


def prompt_injection_cmd(params: dict) -> list[str]:
    rounds = int(params.get("rounds", 3))
    budget = int(params.get("budget", 20))
    if not (1 <= rounds <= 10):
        raise ValueError("rounds must be between 1 and 10")
    if not (1 <= budget <= 100):
        raise ValueError("budget must be between 1 and 100")
    return [PYTHON, "main.py", "prompt-injection", "loop", "--rounds", str(rounds), "--budget", str(budget)]


def token_replay_cmd(params: dict) -> list[str]:
    cmd = [PYTHON, "main.py", "token-replay"]
    if params.get("skipGenerate"):
        cmd.append("--skip-generate")
    if params.get("withMining"):
        cmd.append("--with-mining")
    return cmd


def merchant_fraud_cmd(params: dict) -> list[str]:
    samples = int(params.get("samples", 5000))
    if not (100 <= samples <= 20000):
        raise ValueError("samples must be between 100 and 20000")
    return [PYTHON, "main.py", "merchant-fraud", "--samples", str(samples)]


def graph_fraud_cmd(params: dict) -> list[str]:
    epochs = int(params.get("epochs", 12))
    if not (1 <= epochs <= 30):
        raise ValueError("epochs must be between 1 and 30")
    return [PYTHON, "main.py", "graph-fraud", "--epochs", str(epochs)]


VECTORS = {
    "prompt-injection": prompt_injection_cmd,
    "token-replay": token_replay_cmd,
    "merchant-fraud": merchant_fraud_cmd,
    "graph-fraud": graph_fraud_cmd,
}
