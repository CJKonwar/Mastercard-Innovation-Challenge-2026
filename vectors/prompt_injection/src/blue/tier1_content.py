"""Tier 1: per-artifact content screening on cheap text features."""
from __future__ import annotations
import math, re
from schemas import Artifact

FEATURE_ORDER = ["len", "zero_width", "delim_hits", "imperative_density",
                 "entropy", "has_b64", "acct_like"]

DELIMS = ["system", "assistant", "<|im_start|>", "###", "ignore previous"]
IMPERATIVES = ["ignore", "must", "set", "send", "transfer", "change", "update", "pay"]


def extract_features(text: str) -> dict:
    """Cheap text signals: length, entropy, zero-width chars, delimiters, imperatives."""
    t = text.lower()
    n = max(len(text), 1)
    zw = sum(text.count(c) for c in ["\u200b", "\u200c", "\u200d"])
    counts = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    entropy = -sum((c/n) * math.log2(c/n) for c in counts.values())
    return {
        "len": len(text),
        "zero_width": zw,
        "delim_hits": sum(t.count(d) for d in DELIMS),
        "imperative_density": sum(t.count(w) for w in IMPERATIVES) / (n/100),
        "entropy": entropy,
        "has_b64": 1.0 if re.search(r"[A-Za-z0-9+/]{24,}={0,2}", text) else 0.0,
        "acct_like": 1.0 if re.search(r"\b\d{4}-\d{4}\b", text) else 0.0,
    }


class ContentDetector:
    """Scores an artifact on its text alone, with or without a trained model."""

    def __init__(self, model=None, gbdt=None):
        self.model = model
        self.gbdt = gbdt

    def score(self, artifact: Artifact) -> float:
        """Probability this artifact carries an injection."""
        f = extract_features(artifact.content)
        if self.gbdt is not None:
            import numpy as np
            vec = np.array([[f[k] for k in FEATURE_ORDER]])
            return float(self.gbdt.predict_proba(vec)[0, 1])
        if self.model is not None:
            out = self.model(artifact.content)[0]
            p = float(out["score"])
            return p if str(out["label"]).upper() in ("INJECTION", "LABEL_1", "POSITIVE") else 1.0 - p
        s = 0.0
        s += 0.5 if f["delim_hits"] else 0.0
        s += 0.3 if f["zero_width"] else 0.0
        s += 0.3 * f["has_b64"]
        s += min(0.4, 0.1 * f["imperative_density"])
        return min(s, 1.0)
