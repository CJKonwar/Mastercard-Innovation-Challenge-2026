"""Fuses the three detector tiers into one risk score and an allow/step-up/block decision."""
from __future__ import annotations
from schemas import Trace, Artifact, DetectorVerdict, Policy, CapabilityClass
from .tier1_content import ContentDetector
from .tier2_graph import GraphDetector
from .tier3_intent import IntentChecker


class BlueTeam:
    """The three tiers, weighted into one score."""

    def __init__(self, content=None, graph=None, intent=None,
                 w=(0.5, 0.3, 0.2)):
        # Weights measured, not assumed. Tier 2 was originally weighted
        # heaviest (0.3/0.5/0.2) because provenance is the architectural
        # differentiator, but on the current archive it emits a near-constant
        # ~0.34 on benign traffic while Tier 1 separates cleanly
        # (0.006 vs 0.994). Shifting weight to Tier 1 widened the
        # benign/attack margin from 0.437 to 0.577.
        #
        # Deliberately NOT pushed further (0.6/0.2/0.2 measured 0.646): the
        # archive is ~94% T0 naive imperatives, which is exactly what Tier 1's
        # keyword and entropy features are best at. Against T3 semantic lies
        # Tier 1 degrades and provenance is the only signal that survives
        # rephrasing, so keeping Tier 2 materially weighted trades a little
        # measured margin for robustness to the attacks worth worrying about.
        self.content = content or ContentDetector()
        self.graph = graph or GraphDetector()
        self.intent = intent or IntentChecker()
        self.w = w

    def evaluate(self, trace: Trace, artifacts: list[Artifact]) -> DetectorVerdict:
        """Score a trace and decide policy.

        Financial actions are blocked at a lower threshold than reads, because
        the cost of missing one is asymmetric.
        """
        p_content = max((self.content.score(a) for a in artifacts), default=0.0)
        p_graph, gexpl = self.graph.score(trace)
        p_intent = self.intent.score(trace)
        risk = self.w[0]*p_content + self.w[1]*p_graph + self.w[2]*p_intent
        has_financial = any(c.capability is CapabilityClass.FINANCIAL
                            for c in trace.tool_calls)
        thr_block = 0.6 if has_financial else 0.85
        policy = (Policy.BLOCK if risk >= thr_block
                  else Policy.STEP_UP if risk >= 0.35 else Policy.ALLOW)
        return DetectorVerdict(p_content, p_graph, p_intent, round(risk, 3),
                               policy, {"graph": gexpl})
