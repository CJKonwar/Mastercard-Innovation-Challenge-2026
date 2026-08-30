"""
evaluate_pipeline.py — combined Layer 1 + Layer 2 end-to-end evaluation (§4.4)

Layer 1's deterministic checks run first, over the full dataset in
chronological order (nonce-registry state is stateful, so this must be the
whole dataset, not just the held-out test rows -- see note below). Layer 2
then only scores the rows Layer 1 accepted, exactly like Figure 2's decision
flow: a Layer-1 reject short-circuits, nothing reaches the ML risk scorer.

This produces ONE end-to-end system score (precision/recall/F1/AUC, per
attack sub-class, plus combined FPR) instead of reporting either layer's
number in isolation -- the actual figure for the solution walkthrough, per
PROGRESS.md's next-steps #2.

Why Layer 1 has to run on the FULL dataset even though we only report on the
test split: a T1/T3/T4/retry row shares its nonce with the legitimate base
row it was cloned from (see generator.py's derive_* functions), and those
two rows can land on opposite sides of the train/test split. Layer 1's
NonceRegistry needs to see the base row first to correctly judge the derived
row, regardless of which split either one falls in. So: run Layer 1
chronologically over everything, then look up its verdict for just the
test-set rows Layer 2 was evaluated on, and combine at that point.

Run: python evaluate_pipeline.py
"""

import csv
import json
import os
from collections import Counter
from datetime import datetime

import numpy as np
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix,
)

from deterministic_verifier import NonceRegistry, verify_event
from train_layer2 import train_and_evaluate, DATA_PATH

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "results.json")


def load_rows(path):
    """Read the session dataset as dicts."""
    with open(path) as f:
        return list(csv.DictReader(f))


def run_layer1_full(rows):
    """
    Runs Layer 1 over ALL rows in chronological order (state matters -- see
    module docstring) and returns {event_id: verdict_dict}.
    """
    rows_sorted = sorted(rows, key=lambda r: r["used_at"])
    registry = NonceRegistry()
    verdicts = {}
    for row in rows_sorted:
        verdicts[row["event_id"]] = verify_event(row, registry)
    return verdicts


def main():
    """Score the full Layer 1 to Layer 2 pipeline and print the headline metrics."""
    rows = load_rows(DATA_PATH)
    layer1_verdicts = run_layer1_full(rows)

    # Reuses train_layer2's exact train/test split (same seed, same
    # stratification) so Layer 2's numbers here match what train_layer2.py
    # reports standalone -- the only thing this script adds is folding
    # Layer 1's verdict in ahead of it.
    model, df, (X_test, y_test, label_test, pred_test, proba_test) = train_and_evaluate()

    test_df = df.loc[X_test.index].copy()
    test_df["layer2_pred"] = pred_test
    test_df["layer2_proba"] = proba_test
    test_df["layer1_decision"] = test_df["event_id"].map(lambda eid: layer1_verdicts[eid]["decision"])
    test_df["layer1_reason"] = test_df["event_id"].map(lambda eid: layer1_verdicts[eid]["reason"])

    # Combined decision, per Figure 2: Layer 1 reject short-circuits; only
    # what Layer 1 accepts is scored by Layer 2.
    l1_reject = (test_df["layer1_decision"] == "REJECT").values
    layer2_pred = test_df["layer2_pred"].values
    layer2_proba = test_df["layer2_proba"].values

    combined_pred = np.where(l1_reject, 1, layer2_pred)
    # For a proper AUC, rows Layer 1 rejects outright get a max-confidence
    # score (1.0); everything else keeps Layer 2's continuous probability.
    combined_proba = np.where(l1_reject, 1.0, layer2_proba)

    y_true = test_df["fraud"].values
    label = test_df["label"].values

    print("=" * 70)
    print("COMBINED PIPELINE (Layer 1 -> Layer 2) — OVERALL, same held-out test set")
    print("=" * 70)
    print(f"Test set size: {len(y_true)}  (fraud={y_true.sum()}, legitimate={len(y_true) - y_true.sum()})")
    print(f"Precision: {precision_score(y_true, combined_pred, zero_division=0):.3f}")
    print(f"Recall:    {recall_score(y_true, combined_pred, zero_division=0):.3f}")
    print(f"F1:        {f1_score(y_true, combined_pred, zero_division=0):.3f}")
    try:
        print(f"AUC:       {roc_auc_score(y_true, combined_proba):.3f}")
    except ValueError:
        print("AUC:       undefined (only one class present in test fold)")
    tn, fp, fn, tp = confusion_matrix(y_true, combined_pred).ravel()
    print(f"Confusion matrix -> TN={tn} FP={fp} FN={fn} TP={tp}")

    print("\n" + "=" * 70)
    print("PER ATTACK SUB-CLASS RECALL — Layer1-only vs Layer2-only vs COMBINED")
    print("=" * 70)
    print(f"{'label':6s} {'n':>4s} {'Layer1-only':>13s} {'Layer2-only':>13s} {'COMBINED':>10s}   breakdown")
    for lbl in ["T1", "T2", "T3", "T4"]:
        mask = label == lbl
        n = int(mask.sum())
        if n == 0:
            continue
        l1_recall = l1_reject[mask].mean()
        l2_recall = layer2_pred[mask].mean()
        combined_recall = combined_pred[mask].mean()
        caught_l1 = int(l1_reject[mask].sum())
        caught_l2_only = int(((~l1_reject[mask]) & (layer2_pred[mask] == 1)).sum())
        missed = int(((~l1_reject[mask]) & (layer2_pred[mask] == 0)).sum())
        print(f"{lbl:6s} {n:4d} {l1_recall:13.1%} {l2_recall:13.1%} {combined_recall:10.1%}   "
              f"L1={caught_l1} L2-only={caught_l2_only} missed={missed}")

    print("\n" + "=" * 70)
    print("FALSE POSITIVE RATE — Layer1-only vs Layer2-only vs COMBINED")
    print("=" * 70)
    for lbl in ["legitimate", "legitimate_retry"]:
        mask = label == lbl
        n = int(mask.sum())
        if n == 0:
            continue
        l1_fpr = l1_reject[mask].mean()
        l2_fpr = layer2_pred[mask].mean()
        combined_fpr = combined_pred[mask].mean()
        print(f"{lbl:18s} n={n:4d}  Layer1={l1_fpr:6.2%}  Layer2={l2_fpr:6.2%}  COMBINED={combined_fpr:6.2%}")

    print("\n" + "=" * 70)
    print("WHERE EACH ATTACK IS CAUGHT (per sub-class, on this test set)")
    print("=" * 70)
    print("The division of labor Figure 2 describes: T1/T2 short-circuit at Layer 1;")
    print("T3/T4 pass through and are Layer 2's contribution.")
    for lbl in ["T1", "T2", "T3", "T4"]:
        mask = label == lbl
        n = int(mask.sum())
        if n == 0:
            continue
        c = Counter()
        for reject, l2p in zip(l1_reject[mask], layer2_pred[mask]):
            if reject:
                c["caught_at_layer1"] += 1
            elif l2p == 1:
                c["caught_at_layer2"] += 1
            else:
                c["missed_by_both"] += 1
        print(f"  {lbl}: {dict(c)}  (n={n})")

    save_results(y_true, combined_pred, combined_proba, label, l1_reject, layer2_pred, tn, fp, fn, tp)


def save_results(y_true, combined_pred, combined_proba, label, l1_reject, layer2_pred, tn, fp, fn, tp):
    """Persist the same numbers just printed, so a caller doesn't have to
    scrape stdout to know what a run produced."""
    subclasses = []
    for lbl in ["T1", "T2", "T3", "T4"]:
        mask = label == lbl
        n = int(mask.sum())
        if n == 0:
            continue
        l1_recall = float(l1_reject[mask].mean())
        subclasses.append({
            "label": lbl,
            "n": n,
            "layer1": l1_recall,
            "layer2": None if l1_recall == 1.0 else float(layer2_pred[mask].mean()),
            "combined": float(combined_pred[mask].mean()),
        })

    try:
        auc = float(roc_auc_score(y_true, combined_proba))
    except ValueError:
        auc = None

    out = {
        "timestamp": datetime.now().isoformat(),
        "testSetSize": int(len(y_true)),
        "fraudCount": int(y_true.sum()),
        "legitimateCount": int(len(y_true) - y_true.sum()),
        "precision": float(precision_score(y_true, combined_pred, zero_division=0)),
        "recall": float(recall_score(y_true, combined_pred, zero_division=0)),
        "f1": float(f1_score(y_true, combined_pred, zero_division=0)),
        "auc": auc,
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "subclasses": subclasses,
    }
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved -> {os.path.abspath(RESULTS_PATH)}")


if __name__ == "__main__":
    main()
