"""
train_layer2.py — Layer 2: ML risk scorer (§4.1, §4.4)

Trains a gradient-boosted classifier (LightGBM) on the Generate-pillar output,
using the feature set from features.py. Evaluation follows the brief's exact
wording: precision, recall, F1, AUC -- reported overall, per attack sub-class,
and explicitly against the Layer-1-only deterministic baseline (§4.4).

Run: python train_layer2.py
"""

import csv

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix,
)
from sklearn.model_selection import train_test_split

from features import build_features, MODEL_FEATURES, CATEGORICAL_FEATURES

DATA_PATH = "../data/sessions.csv"

# Layer-1-only baseline, from evaluate_layer1.py's output on this same dataset.
# Hardcoded here (rather than re-run live) so the comparison print-out is a
# fixed reference point; re-run evaluate_layer1.py if the dataset changes.
LAYER1_BASELINE_RECALL = {"T1": 1.00, "T2": 1.00, "T3": 0.00, "T4": 0.00}
LAYER1_BASELINE_FPR_LEGIT = 0.00
LAYER1_BASELINE_FPR_RETRY = 0.00


def load_rows(path):
    """Read the session dataset as dicts."""
    with open(path) as f:
        return list(csv.DictReader(f))


def train_and_evaluate(seed=42, test_size=0.30, threshold=0.5):
    """Fit the risk scorer and report metrics against the Layer-1 baseline."""
    rows = load_rows(DATA_PATH)
    df = build_features(rows)

    X = df[MODEL_FEATURES]
    y = df["fraud"]

    # Stratify on the full multiclass label (not just binary fraud) so rare
    # sub-classes like T4 (32 rows total) still get representation in test.
    train_idx, test_idx = train_test_split(
        df.index, test_size=test_size, random_state=seed, stratify=df["label"]
    )
    X_train, X_test = X.loc[train_idx], X.loc[test_idx]
    y_train, y_test = y.loc[train_idx], y.loc[test_idx]
    label_test = df.loc[test_idx, "label"]
    profile_test = df.loc[test_idx, "drift_profile"]

    model = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=15,          # kept small -- this is a small dataset, avoid overfitting
        min_child_samples=5,    # lowered from the default (20) because minority classes here are tiny
        class_weight="balanced",  # fraud is ~6% of rows; don't let the model just predict "legitimate" always
        random_state=seed,
        verbosity=-1,
    )
    model.fit(X_train, y_train, categorical_feature=CATEGORICAL_FEATURES)

    proba_test = model.predict_proba(X_test)[:, 1]
    pred_test = (proba_test >= threshold).astype(int)

    print("=" * 70)
    print("LAYER 2 — OVERALL (binary fraud vs. not, on held-out test set)")
    print("=" * 70)
    print(f"Test set size: {len(y_test)}  (fraud={y_test.sum()}, legitimate={len(y_test)-y_test.sum()})")
    print(f"Precision: {precision_score(y_test, pred_test, zero_division=0):.3f}")
    print(f"Recall:    {recall_score(y_test, pred_test, zero_division=0):.3f}")
    print(f"F1:        {f1_score(y_test, pred_test, zero_division=0):.3f}")
    try:
        print(f"AUC:       {roc_auc_score(y_test, proba_test):.3f}")
    except ValueError:
        print("AUC:       undefined (only one class present in test fold)")

    tn, fp, fn, tp = confusion_matrix(y_test, pred_test).ravel()
    print(f"Confusion matrix -> TN={tn} FP={fp} FN={fn} TP={tp}")

    print("\n" + "=" * 70)
    print("PER ATTACK SUB-CLASS RECALL (of test rows with this true label, how many flagged)")
    print("=" * 70)
    print(f"{'label':10s} {'n_test':>7s} {'recall':>8s}   {'Layer-1 baseline':>17s}   {'Layer-2 delta':>14s}")
    for lbl in ["T1", "T2", "T3", "T4"]:
        mask = label_test == lbl
        n = mask.sum()
        if n == 0:
            print(f"{lbl:10s} {'0':>7s}   (no test rows this fold)")
            continue
        recall = pred_test[mask.values].mean()
        base = LAYER1_BASELINE_RECALL[lbl]
        delta = recall - base
        print(f"{lbl:10s} {n:7d} {recall:8.1%}   {base:17.1%}   {delta:+14.1%}")

    print("\n" + "=" * 70)
    print("FALSE POSITIVE RATE (legitimate traffic wrongly flagged)")
    print("=" * 70)
    for lbl, base in [("legitimate", LAYER1_BASELINE_FPR_LEGIT), ("legitimate_retry", LAYER1_BASELINE_FPR_RETRY)]:
        mask = label_test == lbl
        n = mask.sum()
        if n == 0:
            print(f"{lbl:18s} (no test rows this fold)")
            continue
        fpr = pred_test[mask.values].mean()
        print(f"{lbl:18s} n={n:4d}  Layer-2 FPR={fpr:6.2%}   Layer-1 baseline={base:6.2%}")

    print("\n" + "=" * 70)
    print("RECALL BY DRIFT-PROFILE DIFFICULTY TIER (T1/T3/T4 only -- the real PR curve)")
    print("=" * 70)
    print("obvious < device_spoofed / same_network < full_hard, roughly increasing difficulty")
    for profile in ["obvious", "device_spoofed", "same_network", "full_hard"]:
        mask = (profile_test == profile) & (label_test.isin(["T1", "T3", "T4"]))
        n = mask.sum()
        if n == 0:
            print(f"  {profile:16s} (no test rows this fold)")
            continue
        recall = pred_test[mask.values].mean()
        print(f"  {profile:16s} n={n:4d}  recall={recall:6.1%}")

    print("\n" + "=" * 70)
    print("FEATURE IMPORTANCE (gain-based)")
    print("=" * 70)
    importances = pd.Series(model.feature_importances_, index=MODEL_FEATURES).sort_values(ascending=False)
    for feat, imp in importances.items():
        print(f"  {feat:24s} {imp:8.0f}")

    return model, df, (X_test, y_test, label_test, pred_test, proba_test)


if __name__ == "__main__":
    train_and_evaluate()
