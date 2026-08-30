"""Training for Tier 2's GNN, with the metrics needed to tell learning from guessing."""
from __future__ import annotations
import random
import torch

from .tier2_gnn import GNNRiskModel


def group_split(groups: list[str], test_frac: float = 0.25, seed: int = 0):
    """Split by cell, never by sample: same-cell mutations are near-duplicates."""
    unique = sorted(set(groups))
    rng = random.Random(seed)
    rng.shuffle(unique)
    n_test = max(1, int(len(unique) * test_frac)) if len(unique) > 1 else 0
    test_groups = set(unique[:n_test])
    train_idx = [i for i, g in enumerate(groups) if g not in test_groups]
    test_idx = [i for i, g in enumerate(groups) if g in test_groups]
    return train_idx, test_idx


def evaluate(model: GNNRiskModel, graphs: list, labels: list[int], idx: list[int]) -> float:
    """Plain accuracy. Prefer metrics(), which is honest under imbalance."""
    if not idx:
        return float("nan")
    correct = 0
    for i in idx:
        risk, _ = model.predict(graphs[i])
        correct += int((risk >= 0.5) == bool(labels[i]))
    return correct / len(idx)


def metrics(model: GNNRiskModel, graphs: list, labels: list[int],
            idx: list[int]) -> dict:
    """Balanced accuracy, precision/recall/F1, and the majority-class baseline to beat."""
    if not idx:
        return {}
    tp = fp = tn = fn = 0
    for i in idx:
        risk, _ = model.predict(graphs[i])
        pred, truth = risk >= 0.5, bool(labels[i])
        if pred and truth:      tp += 1
        elif pred and not truth: fp += 1
        elif not pred and truth: fn += 1
        else:                    tn += 1

    n_pos, n_neg = tp + fn, tn + fp
    recall_pos = tp / n_pos if n_pos else float("nan")
    recall_neg = tn / n_neg if n_neg else float("nan")
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    f1 = (2 * precision * recall_pos / (precision + recall_pos)
          if (precision == precision and recall_pos == recall_pos
              and precision + recall_pos > 0) else float("nan"))
    if n_pos and n_neg:
        balanced = (recall_pos + recall_neg) / 2
    else:
        balanced = float("nan")
    return {
        "n": len(idx), "n_pos": n_pos, "n_neg": n_neg,
        "accuracy": (tp + tn) / len(idx),
        "balanced_accuracy": balanced,
        "precision": precision, "recall": recall_pos,
        "specificity": recall_neg, "f1": f1,
        "majority_baseline": max(n_pos, n_neg) / len(idx),
    }


def _fmt(m: dict) -> str:
    """One-line metrics summary."""
    def g(k):
        v = m.get(k, float("nan"))
        return "  n/a" if v != v else f"{v:.3f}"
    return (f"acc {g('accuracy')} | balanced {g('balanced_accuracy')} "
            f"(majority baseline {g('majority_baseline')}) | "
            f"P {g('precision')} R {g('recall')} F1 {g('f1')} "
            f"specificity {g('specificity')}")


def train_gnn(graphs: list, labels: list[int], groups: list[str],
             hidden: int = 32, epochs: int = 200, lr: float = 0.01,
             batch_size: int = 8, seed: int = 0, verbose: bool = True) -> GNNRiskModel:
    """Train with balanced class weights, keeping the best checkpoint by train score."""
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if verbose:
        print(f"tier2 dataset: {len(graphs)} graphs ({n_pos} malicious, "
             f"{n_neg} benign) across {len(set(groups))} cells")

    train_idx, test_idx = group_split(groups, seed=seed)
    if verbose:
        print(f"train: {len(train_idx)} graphs / test: {len(test_idx)} graphs "
             f"(split by cell, so no cell appears on both sides)")

    total = len(labels)
    w_pos = total / (2 * n_pos) if n_pos else 0.0
    w_neg = total / (2 * n_neg) if n_neg else 0.0
    if verbose and n_pos and n_neg:
        print(f"class weights: malicious x{w_pos:.2f}, benign x{w_neg:.2f} "
              f"(counters the {100*n_pos/total:.0f}% malicious skew)")

    torch.manual_seed(seed)
    model = GNNRiskModel(hidden=hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    rng = random.Random(seed)

    best_state, best_score, best_epoch = None, -1.0, -1
    order = list(train_idx)

    for epoch in range(epochs):
        rng.shuffle(order)
        model.train()
        total_loss, n_seen, batch_losses = 0.0, 0, []
        opt.zero_grad()

        for i in order:
            feats, a_d, a_a, mask = model.graph_to_tensors(graphs[i])
            if mask.sum() == 0:
                continue
            pred = model.forward(feats, a_d, a_a, mask)
            target = torch.tensor([float(labels[i])])
            w = w_pos if labels[i] else w_neg
            loss = torch.nn.functional.binary_cross_entropy(
                pred, target, weight=torch.tensor([w]))
            batch_losses.append(loss)
            total_loss += loss.item()
            n_seen += 1

            if len(batch_losses) >= batch_size:
                torch.stack(batch_losses).mean().backward()
                opt.step()
                opt.zero_grad()
                batch_losses = []

        if batch_losses:
            torch.stack(batch_losses).mean().backward()
            opt.step()
            opt.zero_grad()

        model.eval()
        tr = metrics(model, graphs, labels, train_idx)
        score = tr.get("balanced_accuracy", float("nan"))
        if score != score:
            score = tr.get("accuracy", 0.0)
        if score > best_score:
            best_score, best_epoch = score, epoch
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if verbose and (epoch % 40 == 0 or epoch == epochs - 1):
            print(f"epoch {epoch:3d}  loss {total_loss/max(n_seen,1):.4f}  "
                 f"train balanced-acc {score:.3f}")

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()

    if verbose:
        print(f"selected epoch {best_epoch} (best train balanced accuracy)")
        print(f"  train: {_fmt(metrics(model, graphs, labels, train_idx))}")
        te = metrics(model, graphs, labels, test_idx)
        if te:
            print(f"  test : {_fmt(te)}")
            ba, base = te.get("balanced_accuracy"), te.get("majority_baseline")
            if ba == ba and te.get("n_pos") and te.get("n_neg"):
                if ba <= 0.5:
                    print("  WARNING: test balanced accuracy <= 0.50 - this model "
                         "is no better than chance; do not ship it.")
                elif te["accuracy"] < base:
                    print("  WARNING: test accuracy is below the majority-class "
                         "baseline - always guessing the common class would score "
                         "higher.")
            else:
                print("  (test split has only one class - balanced accuracy is "
                     "undefined; dataset too small this round, not a bug)")

    return model
