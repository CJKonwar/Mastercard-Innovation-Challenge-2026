"""The orchestrator: one round, detector retraining, and the closed loop that alternates them."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from schemas import Payload, SurfaceType, TechniqueTier, Objective, Artifact, Provenance
from red import MapElitesArchive, Attacker, AttackerUnavailableError
from surfaces import render
from agent import TargetAgent
from judge import OutcomeJudge
from blue import BlueTeam
from fitness import fitness

BASE_INSTRUCTION = "buy 1 phone case"

SEEDS_PATH = Path(__file__).resolve().parents[1] / "data" / "seeds" / "seed_payloads.json"
BENIGN_PATH = Path(__file__).resolve().parents[1] / "data" / "surfaces" / "benign_corpus.json"


def seed_payloads(path: Path = SEEDS_PATH) -> list[Payload]:
    """Load the seed corpus, adapted from ASB and InjecAgent."""
    rows = json.loads(path.read_text())
    return [Payload(text=r["text"], surface=SurfaceType(r["surface"]),
                    technique=TechniqueTier(r["technique"]),
                    objective=Objective(r["objective"]),
                    target_spec=r.get("target_spec", {}))
            for r in rows]


def benign_corpus(path: Path = BENIGN_PATH) -> list[dict]:
    """Legitimate customer content, including deliberate near-miss traps."""
    return json.loads(path.read_text())


def benign_utility(agent=None, blue=None) -> list[dict]:
    """Run the benign set through the same pipeline. This is the false-positive control."""
    agent = agent or TargetAgent()
    blue = blue or BlueTeam()
    legit_state = agent.run("benign-baseline", BASE_INSTRUCTION, []).final_state

    rows = []
    for entry in benign_corpus():
        surface = SurfaceType(entry["surface"])
        art = Artifact(content=entry["text"], surface=surface,
                       provenance=Provenance.UNTRUSTED, payload_id=None)
        trace = agent.run(f"benign-{surface.value}-{art.source_id}", BASE_INSTRUCTION,
                          [art], is_attack=False)
        verdict = blue.evaluate(trace, [art])
        task_correct = trace.final_state == legit_state
        rows.append({"surface": surface.value, "text": entry["text"],
                     "note": entry["note"],
                     "expect_task_correct": entry["expect_task_correct"],
                     "task_correct": task_correct,
                     "matches_expectation": task_correct == entry["expect_task_correct"],
                     "any_taint": any(c.tainted_by for c in trace.tool_calls),
                     "risk": verdict.risk, "policy": verdict.policy.value})
    return rows


def _tick(enabled: bool, msg: str, newline: bool = False) -> None:
    """One progress line, rewritten in place on stderr so stdout stays pipeable."""
    if not enabled:
        return
    import sys
    sys.stderr.write("\r" + msg.ljust(78))
    if newline:
        sys.stderr.write("\n")
    sys.stderr.flush()


def _plausibility(technique: TechniqueTier) -> float:
    """How natural the text reads; semantic lies score highest."""
    return 0.9 if technique == TechniqueTier.T3_SEMANTIC else 0.4


def _evaluate(payload, agent, judge, blue, task_id):
    """Run one payload end to end and return its fitness, verdict and judgement."""
    art = render(payload)
    trace = agent.run(task_id, "buy 1 phone case", [art],
                      is_attack=True, payload_id=payload.id)
    outcome = judge.judge(trace, payload)
    verdict = blue.evaluate(trace, [art])
    fit = fitness(outcome, verdict, _plausibility(payload.technique), len(payload.text))
    return fit, outcome, verdict


@dataclass
class RoundStats:
    """Per-round outcomes.

    Two success rates, deliberately kept apart: seed ASR uses a fixed attack
    set, so movement is the defense improving; mutation ASR has both sides
    moving, which is the arms race.
    """
    archive: object
    seed_total: int = 0
    seed_success: int = 0
    seed_detected: int = 0
    seed_risk_sum: float = 0.0
    mut_attempted: int = 0
    mut_evaluated: int = 0
    mut_success: int = 0
    mut_detected: int = 0
    mut_won_cell: int = 0
    mut_failed_json: int = 0
    mut_risk_sum: float = 0.0

    @property
    def seed_asr(self) -> float:
        """Share of seeds that succeeded."""
        return self.seed_success / self.seed_total if self.seed_total else float("nan")

    @property
    def seed_detection_rate(self) -> float:
        """Share of seeds the Blue Team flagged."""
        return self.seed_detected / self.seed_total if self.seed_total else float("nan")

    @property
    def seed_mean_risk(self) -> float:
        """Mean risk assigned to seeds."""
        return self.seed_risk_sum / self.seed_total if self.seed_total else float("nan")

    @property
    def mutation_asr(self) -> float:
        """Share of evolved payloads that succeeded."""
        return self.mut_success / self.mut_evaluated if self.mut_evaluated else float("nan")

    @property
    def mutation_detection_rate(self) -> float:
        """Share of evolved payloads the Blue Team flagged."""
        return self.mut_detected / self.mut_evaluated if self.mut_evaluated else float("nan")

    @property
    def mutation_mean_risk(self) -> float:
        """Mean risk assigned to evolved payloads."""
        return self.mut_risk_sum / self.mut_evaluated if self.mut_evaluated else float("nan")

    def as_dict(self) -> dict:
        """Flatten for the history log."""
        return {
            "seed_total": self.seed_total, "seed_success": self.seed_success,
            "seed_asr": self.seed_asr,
            "seed_detection_rate": self.seed_detection_rate,
            "seed_mean_risk": self.seed_mean_risk,
            "mutations_attempted": self.mut_attempted,
            "mutations_evaluated": self.mut_evaluated,
            "mutations_failed_json": self.mut_failed_json,
            "mutations_won_cell": self.mut_won_cell,
            "mutation_success": self.mut_success,
            "mutation_asr": self.mutation_asr,
            "mutation_detection_rate": self.mutation_detection_rate,
            "mutation_mean_risk": self.mutation_mean_risk,
        }


def run_round(archive, attacker, agent, judge, blue, budget=200, progress: bool = True):
    """Score every seed, then evolve `budget` mutations against this Blue Team."""
    stats = RoundStats(archive=archive)

    seeds = seed_payloads()
    for n, p in enumerate(seeds, 1):
        fit, outcome, verdict = _evaluate(p, agent, judge, blue, f"seed-{p.id}")
        archive.add(p, fit)
        stats.seed_total += 1
        stats.seed_success += int(outcome.success)
        stats.seed_detected += int(verdict.policy.value != "allow")
        stats.seed_risk_sum += verdict.risk
        _tick(progress, f"  seed {n}/{len(seeds)} {p.objective.value:<22} "
                        f"fitness={fit:+.3f}")
    _tick(progress, f"  seeded: {archive.coverage()} cells claimed | "
                    f"seed ASR {100*stats.seed_asr:.0f}%", newline=True)

    for i in range(budget):
        stats.mut_attempted += 1
        parent = archive.sample_parent()
        try:
            child = attacker.mutate(parent)
        except AttackerUnavailableError:
            raise
        except Exception as e:
            stats.mut_failed_json += 1
            reason = str(e).splitlines()[0][:100]
            print(f"mutation {i+1}/{budget} failed transiently "
                  f"({type(e).__name__}: {reason}); skipping, no fallback")
            continue
        fit, outcome, verdict = _evaluate(child, agent, judge, blue, f"t{i}")
        won = archive.add(child, fit)
        stats.mut_evaluated += 1
        stats.mut_success += int(outcome.success)
        stats.mut_detected += int(verdict.policy.value != "allow")
        stats.mut_won_cell += int(won)
        stats.mut_risk_sum += verdict.risk
        _tick(progress, f"  mutation {i+1}/{budget} {child.technique.value:<20} "
                        f"fitness={fit:+.3f} {'WON its cell' if won else '--'}")
    if stats.mut_evaluated:
        done = (f"  mutations done: {archive.coverage()} cells total | "
                f"mutation ASR {100*stats.mutation_asr:.0f}% "
                f"({stats.mut_won_cell} won cells, "
                f"{stats.mut_failed_json} failed JSON)")
    else:
        done = "  mutations done: no valid mutations this round"
    _tick(progress, done, newline=True)
    return stats


def _cell_id(descriptor) -> str:
    """Stable string id for an archive cell, used to group train/test splits."""
    surface, technique, objective = descriptor
    return f"mal::{surface.value}::{technique.value}::{objective.value}"


def retrain_detectors(archive, agent=None, verbose: bool = True) -> BlueTeam:
    """Retrain Tiers 1 and 2 on the archive's elites plus the benign corpus."""
    from blue.train_tier1 import train_gbdt
    from blue.train_tier2 import train_gnn
    from blue.tier1_content import ContentDetector
    from blue.tier2_graph import build_graph, GraphDetector

    agent = agent or TargetAgent()
    elites = list(archive.cells.items())
    benign_entries = benign_corpus()

    malicious_texts = [(render(elite.payload).content, _cell_id(desc))
                       for desc, elite in elites]
    benign_texts = [(e["text"], f"benign::{e['surface']}") for e in benign_entries]
    gbdt = train_gbdt(malicious_texts, benign_texts, verbose=verbose)

    total_graphs = len(elites) + len(benign_entries)
    graphs, labels, groups = [], [], []
    for n, (desc, elite) in enumerate(elites, 1):
        art = render(elite.payload)
        trace = agent.run(f"retrain-{elite.payload.id}", BASE_INSTRUCTION, [art],
                          is_attack=True, payload_id=elite.payload.id)
        graphs.append(build_graph(trace))
        labels.append(1)
        groups.append(_cell_id(desc))
        _tick(True, f"  tier2 graph {n}/{total_graphs} (malicious elite)")
    for entry in benign_entries:
        surface = SurfaceType(entry["surface"])
        art = Artifact(content=entry["text"], surface=surface,
                       provenance=Provenance.UNTRUSTED, payload_id=None)
        trace = agent.run(f"retrain-benign-{surface.value}-{art.source_id}", BASE_INSTRUCTION,
                          [art], is_attack=False)
        graphs.append(build_graph(trace))
        labels.append(0)
        groups.append(f"benign::{entry['surface']}")
        _tick(True, f"  tier2 graph {len(graphs)}/{total_graphs} (benign control)")
    _tick(True, f"  tier2: {total_graphs} graphs built, training the GNN",
          newline=True)
    gnn = train_gnn(graphs, labels, groups, verbose=verbose)

    return BlueTeam(content=ContentDetector(gbdt=gbdt), graph=GraphDetector(gnn=gnn))


def coevolve(rounds: int = 3, budget_per_round: int = 20,
            attacker=None, agent=None, judge=None) -> dict:
    """Alternate attack and retraining, so each round faces a stronger opponent."""
    archive = MapElitesArchive()
    attacker = attacker or Attacker()
    agent = agent or TargetAgent()
    judge = judge or OutcomeJudge()
    blue = BlueTeam()

    history = []
    for round_num in range(rounds):
        stats = run_round(archive, attacker, agent, judge, blue,
                          budget=budget_per_round)
        history.append({"round": round_num, "coverage": archive.coverage(),
                        "total_cells": archive.total_cells(),
                        "mean_fitness": archive.mean_fitness(),
                        **stats.as_dict()})
        is_last = round_num == rounds - 1
        blue = retrain_detectors(archive, agent=agent, verbose=is_last)

    return {"archive": archive, "blue": blue, "history": history}


if __name__ == "__main__":
    s = run_round(MapElitesArchive(), Attacker(), TargetAgent(),
                  OutcomeJudge(), BlueTeam())
    a = s.archive
    print("coverage:", a.coverage(), "mean fit:", round(a.mean_fitness(), 3))
    print(f"seed ASR: {100*s.seed_asr:.0f}% | mutation ASR: "
          f"{100*s.mutation_asr:.0f}%")
    b = a.best()
    if b: print("best:", round(b.fitness, 3), "|", b.payload.text[:70])
