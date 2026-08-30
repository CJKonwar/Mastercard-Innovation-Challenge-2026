"""
evaluate_layer1.py — runs the Layer-1 deterministic verifier over the full
synthetic dataset in chronological order (nonce-registry state is order-
dependent, so this matters) and reports accept/reject breakdown per label.

This is the "Layer-1-only deterministic baseline" §4.4 says every later
Layer-2 claim must be measured against.

Run: python evaluate_layer1.py
"""

import csv
from collections import Counter, defaultdict
from datetime import datetime

from deterministic_verifier import NonceRegistry, verify_event

DATA_PATH = "../data/sessions.csv"


def load_rows(path):
    """Read the session dataset as dicts."""
    with open(path) as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: r["used_at"])  # chronological arrival order
    return rows


def run_layer1(rows):
    """Replay every event through the deterministic verifier, in time order."""
    registry = NonceRegistry()
    results = []
    for row in rows:
        verdict = verify_event(row, registry)
        results.append((row, verdict))
    return results


def report(results):
    """Print Layer-1 recall per sub-class and its false-positive rate."""
    fraud_labels = {"T1", "T2", "T3", "T4"}
    per_label = defaultdict(lambda: Counter())

    for row, verdict in results:
        per_label[row["label"]][verdict["decision"]] += 1

    print(f"{'label':18s} {'total':>6s} {'ACCEPT':>8s} {'REJECT':>8s}   reject_rate")
    print("-" * 60)
    for label in ["legitimate", "legitimate_retry", "T1", "T2", "T3", "T4"]:
        c = per_label[label]
        total = c["ACCEPT"] + c["REJECT"]
        if total == 0:
            continue
        reject_rate = c["REJECT"] / total
        print(f"{label:18s} {total:6d} {c['ACCEPT']:8d} {c['REJECT']:8d}   {reject_rate:6.1%}")

    print()
    # Headline numbers that matter for the design doc's claims:
    legit_total = per_label["legitimate"]["ACCEPT"] + per_label["legitimate"]["REJECT"]
    legit_fp_rate = per_label["legitimate"]["REJECT"] / legit_total if legit_total else 0.0

    retry_total = per_label["legitimate_retry"]["ACCEPT"] + per_label["legitimate_retry"]["REJECT"]
    retry_fp_rate = per_label["legitimate_retry"]["REJECT"] / retry_total if retry_total else 0.0

    print(f"False-positive rate on legitimate (first-use):  {legit_fp_rate:.2%}  (target: 0%)")
    print(f"False-positive rate on legitimate_retry:         {retry_fp_rate:.2%}  (target: 0%, this is the idempotency-window test)")

    for label in ["T1", "T2", "T3", "T4"]:
        total = per_label[label]["ACCEPT"] + per_label[label]["REJECT"]
        caught = per_label[label]["REJECT"]
        rate = caught / total if total else 0.0
        expectation = "expected: caught deterministically" if label in ("T1", "T2") else "expected: mostly MISSED here -> Layer 2's job"
        print(f"{label} caught by Layer 1: {caught}/{total} ({rate:.1%})  [{expectation}]")

    # Break down reasons for rejection, and nonce_status for T3/T4 specifically
    # so it's visible *why* they slip through (fresh vs duplicate vs reuse).
    print("\nReject reasons by label:")
    reasons = defaultdict(Counter)
    for row, verdict in results:
        if verdict["decision"] == "REJECT":
            reasons[row["label"]][verdict["reason"]] += 1
    for label, c in reasons.items():
        print(f"  {label:18s} {dict(c)}")

    print("\nNonce status distribution for T3/T4 (showing why the sliding window lets them through):")
    for label in ["T3", "T4"]:
        c = Counter(v["nonce_status"] for r, v in results if r["label"] == label)
        print(f"  {label}: {dict(c)}")


if __name__ == "__main__":
    rows = load_rows(DATA_PATH)
    results = run_layer1(rows)
    report(results)
