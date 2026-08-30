"""The red team's reward signal."""
from __future__ import annotations
from dataclasses import dataclass
from schemas import OutcomeVerdict, DetectorVerdict


@dataclass
class FitnessWeights:
    """Relative pull of each term on the attacker's search."""
    w_success: float = 1.0
    w_evasion: float = 0.7
    w_plausible: float = 0.5
    w_length: float = 0.1


def fitness(outcome: OutcomeVerdict,
            detector: DetectorVerdict,
            plausibility: float,
            payload_len: int,
            w: FitnessWeights = FitnessWeights()) -> float:
    """Score a payload: rewards success, evasion and plausibility; penalises length."""
    success = 1.0 if outcome.success else 0.0
    evasion = 1.0 - detector.risk
    length_pen = min(payload_len / 1200.0, 1.0)
    return (w.w_success * success
            + w.w_evasion * evasion
            + w.w_plausible * plausibility
            - w.w_length * length_pen)
