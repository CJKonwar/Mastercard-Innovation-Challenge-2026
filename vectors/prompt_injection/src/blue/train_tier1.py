"""Training for Tier 1's gradient-boosted classifier."""
from __future__ import annotations
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, roc_auc_score

from .tier1_content import extract_features, FEATURE_ORDER


def build_examples(malicious: list[tuple[str, str]], benign: list[tuple[str, str]]):
    """Vectorise texts and tag each with its cell, so splits can group by cell."""
    X, y, groups = [], [], []
    for text, cell in malicious:
        f = extract_features(text)
        X.append([f[k] for k in FEATURE_ORDER]); y.append(1); groups.append(cell)
    for text, cell in benign:
        f = extract_features(text)
        X.append([f[k] for k in FEATURE_ORDER]); y.append(0); groups.append(cell)
    return np.array(X), np.array(y), np.array(groups)


def train_gbdt(malicious: list[tuple[str, str]], benign: list[tuple[str, str]],
              test_size: float = 0.25, seed: int = 0, verbose: bool = True):
    """Fit the classifier, reporting a held-out score before refitting on everything."""
    X, y, groups = build_examples(malicious, benign)
    n_pos, n_neg = int(y.sum()), int((y == 0).sum())
    if verbose:
        print(f"tier1 dataset: {len(X)} examples ({n_pos} malicious, "
             f"{n_neg} benign) across {len(set(groups))} cells")

    def _weights(labels):
        total = len(labels)
        w_pos = total / (2 * n_pos) if n_pos else 0.0
        w_neg = total / (2 * n_neg) if n_neg else 0.0
        return np.where(labels == 1, w_pos, w_neg)

    if verbose and n_pos and n_neg:
        total = len(y)
        print(f"class weights: malicious x{total/(2*n_pos):.2f}, "
             f"benign x{total/(2*n_neg):.2f} "
             f"(counters the {100*n_pos/total:.0f}% malicious skew)")

    can_split = len(set(groups)) >= 2 and len(set(y)) > 1
    if can_split:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        train_idx, test_idx = next(splitter.split(X, y, groups))
        probe = GradientBoostingClassifier(n_estimators=50, max_depth=2, random_state=seed)
        probe.fit(X[train_idx], y[train_idx], sample_weight=_weights(y[train_idx]))
        if verbose:
            if len(set(y[test_idx])) > 1:
                y_pred = probe.predict(X[test_idx])
                y_proba = probe.predict_proba(X[test_idx])[:, 1]
                print(classification_report(y[test_idx], y_pred,
                                            target_names=["benign", "malicious"],
                                            zero_division=0))
                auc = roc_auc_score(y[test_idx], y_proba)
                n_te_pos, n_te_neg = int(y[test_idx].sum()), int((y[test_idx] == 0).sum())
                print(f"test AUC: {auc:.3f}  "
                     f"(on {n_te_pos} malicious / {n_te_neg} benign)")
                if min(n_te_pos, n_te_neg) < 10:
                    print(f"  NOTE: only {min(n_te_pos, n_te_neg)} samples in the "
                         f"smaller test class - this AUC is decorative, not "
                         f"evidence. Check the benign-corpus FPR instead "
                         f"(`main.py judge --benign`).")
            else:
                print("test split has only one class - held-out metric skipped "
                     "(dataset too small/imbalanced this round, not a bug)")
    elif verbose:
        print("not enough distinct cells/classes yet for a held-out split - "
             "training on everything with no reported test metric")

    clf = GradientBoostingClassifier(n_estimators=50, max_depth=2, random_state=seed)
    clf.fit(X, y, sample_weight=_weights(y))
    return clf
