"""
AI Defense Lab - unified entry point for both attack vectors.

    python main.py prompt-injection loop --rounds 6 --budget 30
    python main.py token-replay --skip-generate
    python main.py merchant-fraud
    python main.py graph-fraud

Each vector is a self-contained module under vectors/. They are deliberately
NOT merged into a shared package, because each resolves its own paths
differently: graph_fraud and merchant_fraud both do a bare `import config`
from their own directory (two different config.py files that would collide);
prompt_injection puts its own src/ on sys.path with flat modules;
token_replay's stage scripts read ../data/... and must run from their own
subfolder. Running each in its own working directory keeps all four valid.

This dispatcher forwards every remaining argument to the vector's own main.py,
so each module's CLI stays exactly as documented in its own README.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VECTORS = {
    "prompt-injection": (
        ROOT / "vectors" / "prompt_injection",
        "Indirect prompt injection into agentic commerce surfaces",
    ),
    "graph-fraud": (
        ROOT / "vectors" / "graph_fraud",
        "Mule networks & cross-rail laundering on the transaction graph",
    ),
    "token-replay": (
        ROOT / "vectors" / "token_replay",
        "Agentic-token replay & consent-flow abuse on the Agent Pay trust chain",
    ),
    "merchant-fraud": (
        ROOT / "vectors" / "merchant_fraud",
        "CTGAN adversarial hard-negative mining against a merchant-fraud detector",
    ),
}


def usage(code: int = 0) -> None:
    print(__doc__.strip())
    print("\nVectors:")
    for name, (path, desc) in VECTORS.items():
        mark = " " if (path / "main.py").exists() else "  [MISSING]"
        print(f"  {name:<18}{desc}{mark}")
    print("\nEverything after the vector name is passed straight through, e.g.")
    print("  python main.py prompt-injection judge --benign")
    sys.exit(code)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        usage()

    name = sys.argv[1]
    if name not in VECTORS:
        print(f"Unknown vector: {name!r}\n")
        usage(2)

    path, _ = VECTORS[name]
    entry = path / "main.py"
    if not entry.exists():
        sys.exit(f"{name}: no main.py at {entry}")

    # cwd = the vector's own directory; graph_fraud's `import config` and
    # `from src....` both resolve relative to it.
    sys.exit(subprocess.call([sys.executable, "main.py", *sys.argv[2:]], cwd=path))


if __name__ == "__main__":
    main()
