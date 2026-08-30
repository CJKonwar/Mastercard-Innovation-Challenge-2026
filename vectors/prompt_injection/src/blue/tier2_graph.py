"""Tier 2: provenance graph over a trace, plus a rule-based scorer."""
from __future__ import annotations
from schemas import Trace, CapabilityClass, Provenance

try:
    import networkx as nx
except Exception:
    nx = None


def _authorized_text(trace: Trace) -> str:
    """Everything the user actually delegated: the instruction plus scope.

    Matching only the raw instruction ("buy 1 phone case") meant any argument
    carrying a real task detail - an order number, a confirmed amount - could
    never match, tainted or not. Delegated scope (budget, allowed merchants,
    ...) is also something the user authorized, so it belongs in the same
    text the check matches against.
    """
    parts = [trace.user_instruction]
    for v in trace.delegated_scope.values():
        if isinstance(v, (list, tuple, set)):
            parts.extend(str(x) for x in v)
        else:
            parts.append(str(v))
    return " ".join(parts).lower()


def build_graph(trace: Trace):
    """Turn a trace into a graph of sources, the user, and tool calls."""
    if nx is None:
        raise RuntimeError("pip install networkx")
    g = nx.DiGraph()
    g.add_node("USER", ntype="user", instruction=trace.user_instruction)
    for s in trace.sources:
        g.add_node(s.source_id, ntype="source", provenance=s.provenance.value,
                   surface=s.surface.value if s.surface else None)
    authorized_text = _authorized_text(trace)
    for c in trace.tool_calls:
        g.add_node(c.call_id, ntype="toolcall", tool=c.tool_name,
                   capability=c.capability.value)
        for sid in c.tainted_by:
            g.add_edge(sid, c.call_id, etype="derives")
        for v in c.args.values():
            text = str(v)
            if len(text) >= 4 and text.lower() in authorized_text:
                g.add_edge("USER", c.call_id, etype="authorizes")
    return g


class GraphDetector:
    """Scores the provenance path from untrusted source to financial action."""

    def __init__(self, gnn=None):
        self.gnn = gnn

    def score(self, trace: Trace) -> tuple[float, dict]:
        """Risk plus a short explanation of what drove it."""
        g = build_graph(trace)
        if self.gnn is not None:
            return self.gnn.predict(g)
        for c in trace.tool_calls:
            if c.capability is not CapabilityClass.FINANCIAL:
                continue
            untrusted = [sid for sid in c.tainted_by
                         if (s := trace.source(sid)) and s.provenance is Provenance.UNTRUSTED]
            authorized = g.has_edge("USER", c.call_id)
            if untrusted and not authorized:
                return 0.95, {"flagged_call": c.tool_name,
                              "tainted_by": untrusted, "reason": "untrusted->financial, no user auth"}
        return 0.05, {"reason": "no tainted financial path"}
