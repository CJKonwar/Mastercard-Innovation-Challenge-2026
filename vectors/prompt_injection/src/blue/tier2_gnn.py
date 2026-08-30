"""Tier 2's trainable model: a small message-passing net over the provenance graph."""
from __future__ import annotations
import torch
import torch.nn as nn
import networkx as nx

NTYPES = ["user", "source", "toolcall"]
PROVENANCES = ["trusted", "untrusted"]
CAPABILITIES = ["read", "write", "financial"]
NODE_DIM = len(NTYPES) + len(PROVENANCES) + len(CAPABILITIES)


def _node_features(g: nx.DiGraph) -> tuple[list[str], torch.Tensor]:
    """One-hot each node by type, provenance and capability."""
    nodes = list(g.nodes())
    feats = torch.zeros(len(nodes), NODE_DIM)
    for i, n in enumerate(nodes):
        data = g.nodes[n]
        ntype = data.get("ntype", "")
        if ntype in NTYPES:
            feats[i, NTYPES.index(ntype)] = 1.0
        prov = data.get("provenance")
        if prov in PROVENANCES:
            feats[i, len(NTYPES) + PROVENANCES.index(prov)] = 1.0
        cap = data.get("capability")
        if cap in CAPABILITIES:
            feats[i, len(NTYPES) + len(PROVENANCES) + CAPABILITIES.index(cap)] = 1.0
    return nodes, feats


def _adjacency(g: nx.DiGraph, nodes: list[str], etype: str) -> torch.Tensor:
    """Adjacency matrix for a single edge type."""
    idx = {n: i for i, n in enumerate(nodes)}
    a = torch.zeros(len(nodes), len(nodes))
    for u, v, d in g.edges(data=True):
        if d.get("etype") == etype:
            a[idx[u], idx[v]] = 1.0
    return a


def _pool_mask(g: nx.DiGraph, nodes: list[str]) -> torch.Tensor:
    """Pool over financial calls, falling back to all calls if none are financial."""
    financial = torch.tensor([1.0 if g.nodes[n].get("ntype") == "toolcall"
                              and g.nodes[n].get("capability") == "financial"
                              else 0.0 for n in nodes])
    if financial.sum() > 0:
        return financial
    return torch.tensor([1.0 if g.nodes[n].get("ntype") == "toolcall" else 0.0
                         for n in nodes])


class GNNRiskModel(nn.Module):
    """One hop of message passing, then a readout over the calls that matter."""

    def __init__(self, hidden: int = 16):
        super().__init__()
        self.hidden = hidden
        self.w_self = nn.Linear(NODE_DIM, hidden)
        self.w_derives = nn.Linear(NODE_DIM, hidden)
        self.w_authorizes = nn.Linear(NODE_DIM, hidden)
        self.readout = nn.Linear(hidden, 1)

    def forward(self, feats: torch.Tensor, a_derives: torch.Tensor,
               a_authorizes: torch.Tensor, pool_mask: torch.Tensor) -> torch.Tensor:
        """Risk for one graph, as a tensor."""
        h = torch.relu(self.w_self(feats)
                       + self.w_derives(a_derives.t() @ feats)
                       + self.w_authorizes(a_authorizes.t() @ feats))
        denom = pool_mask.sum().clamp(min=1)
        pooled = (h * pool_mask.unsqueeze(1)).sum(0) / denom
        return torch.sigmoid(self.readout(pooled))

    def graph_to_tensors(self, g: nx.DiGraph):
        """Convert a graph into the tensors forward() expects."""
        nodes, feats = _node_features(g)
        a_derives = _adjacency(g, nodes, "derives")
        a_authorizes = _adjacency(g, nodes, "authorizes")
        mask = _pool_mask(g, nodes)
        return feats, a_derives, a_authorizes, mask

    def predict(self, g: nx.DiGraph) -> tuple[float, dict]:
        """Risk for one graph, plus why it was pooled that way."""
        feats, a_derives, a_authorizes, mask = self.graph_to_tensors(g)
        if mask.sum() == 0:
            return 0.05, {"reason": "no tool calls in trace"}
        with torch.no_grad():
            risk = self.forward(feats, a_derives, a_authorizes, mask).item()
        pooled_over = "financial calls" if any(
            g.nodes[n].get("capability") == "financial" for n in g.nodes()) else "all tool calls"
        return risk, {"reason": "GNN prediction", "pooled_over": pooled_over}

    def save(self, path):
        """Write weights to disk."""
        torch.save(self.state_dict(), path)

    @classmethod
    def load(cls, path, hidden: int | None = None):
        """Load weights, inferring hidden width from the checkpoint."""
        state = torch.load(path, weights_only=True)
        if hidden is None:
            hidden = state["w_self.weight"].shape[0]
        model = cls(hidden=hidden)
        model.load_state_dict(state)
        model.eval()
        return model
