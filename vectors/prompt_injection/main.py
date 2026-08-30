from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import joblib
import ollama

from agent import TargetAgent
from blue import BlueTeam
from coevolve import (benign_utility, coevolve, retrain_detectors,
                      run_round, seed_payloads)
from judge import OutcomeJudge
from red import Attacker, MapElitesArchive
from report import BAR, format_benign_scorecard, format_scorecard, score_payloads

OUT_DIR = Path(__file__).resolve().parent / "outputs"
ARCHIVE_PATH = OUT_DIR / "archive.json"
HISTORY_PATH = OUT_DIR / "coevolution_history.json"
TIER1_PATH = OUT_DIR / "tier1_gbdt.joblib"
TIER2_PATH = OUT_DIR / "tier2_gnn.pt"


def _banner(title: str) -> None:
    """Print a section header."""
    print(f"\n{BAR}\n  {title}\n{BAR}\n")


def _require_ollama() -> None:
    """Exit early with a clear message if the local model backend is down."""
    try:
        ollama.Client().list()
    except Exception as e:
        sys.exit(f"Ollama isn't reachable ({e}).\nNeither the attacker nor the "
                 f"target agent has an offline fallback, and the agent runs on "
                 f"every seed regardless of --budget.\nStart it with "
                 f"`brew services start ollama` or `ollama serve`.")


def _load_blue() -> BlueTeam:
    """Trained detectors if they exist on disk, rule-based otherwise."""
    if not (TIER1_PATH.exists() and TIER2_PATH.exists()):
        print("  no trained detectors on disk yet - using the rule-based "
              "Blue Team\n  (run `python main.py defend` to train them)")
        return BlueTeam()
    from blue.tier1_content import ContentDetector
    from blue.tier2_gnn import GNNRiskModel
    from blue.tier2_graph import GraphDetector
    print(f"  loaded trained detectors from {OUT_DIR.name}/")
    return BlueTeam(content=ContentDetector(gbdt=joblib.load(TIER1_PATH)),
                    graph=GraphDetector(gnn=GNNRiskModel.load(TIER2_PATH)))


def _spark(values: list[float], width: int = 12) -> str:
    """Tiny inline bar chart, so a trend is visible without a plot."""
    blocks = " .:-=+*#%@"
    out = []
    for v in values:
        if v != v:
            out.append("?")
            continue
        out.append(blocks[min(int(v * (len(blocks) - 1)), len(blocks) - 1)])
    return "".join(out)


def _print_sawtooth(history: list[dict]) -> None:
    """The ASR-vs-round table: the headline result of a loop run."""
    print("\n  ASR vs. round  (this is the co-evolution signal)")
    print("  " + "-" * 68)
    print(f"    {'rnd':>3} {'coverage':>9} {'mean fit':>9} "
          f"{'seed ASR':>9} {'mut ASR':>8} {'mut risk':>9} {'won':>4}")
    for h in history:
        sa = h.get("seed_asr", float("nan"))
        ma = h.get("mutation_asr", float("nan"))
        mr = h.get("mutation_mean_risk", float("nan"))
        sa_s = "  n/a" if sa != sa else f"{100*sa:5.1f}%"
        ma_s = "  n/a" if ma != ma else f"{100*ma:5.1f}%"
        mr_s = "n/a" if mr != mr else f"{mr:.3f}"
        print(f"    {h['round']:>3} {h['coverage']:>4}/{h['total_cells']:<4} "
              f"{h['mean_fitness']:>9.3f} {sa_s:>9} {ma_s:>8} {mr_s:>9} "
              f"{h.get('mutations_won_cell', 0):>4}")
    print("  " + "-" * 68)

    seed = [h.get("seed_asr", float("nan")) for h in history]
    mut = [h.get("mutation_asr", float("nan")) for h in history]
    print(f"    seed ASR trend      {_spark(seed)}   (fixed attacks - "
          f"falling = defense improving)")
    print(f"    mutation ASR trend  {_spark(mut)}   (evolving attacks - "
          f"the arms race)")

    valid = [s for s in seed if s == s]
    if len(valid) >= 2:
        delta = valid[-1] - valid[0]
        if delta < -0.02:
            print(f"\n    -> seed ASR fell {100*abs(delta):.1f} points across "
                  f"{len(valid)} rounds on an UNCHANGED attack set:")
            print(f"       the retrained detectors are genuinely stronger.")
        elif delta > 0.02:
            print(f"\n    -> seed ASR ROSE {100*delta:.1f} points on an unchanged "
                  f"attack set - retraining made the defense worse. Check the "
                  f"Tier 2 warnings above.")
        else:
            print(f"\n    -> seed ASR essentially flat ({100*delta:+.1f} pts) - "
                  f"retraining isn't moving the defense yet. Try more rounds "
                  f"or a bigger --budget.")
    print()


def _save_blue(blue: BlueTeam) -> None:
    """Persist the trained detectors."""
    OUT_DIR.mkdir(exist_ok=True)
    joblib.dump(blue.content.gbdt, TIER1_PATH)
    blue.graph.gnn.save(TIER2_PATH)
    print(f"\n  models saved -> {TIER1_PATH.name}, {TIER2_PATH.name}")


def cmd_attack(args) -> None:
    """Phase 1: evolve payloads against the current Blue Team."""
    _require_ollama()
    _banner("PHASE 1 - RED TEAM (evolve injection payloads)")
    print(f"  seeds        {len(seed_payloads())} (bootstrapped into the archive first)")
    print(f"  rounds       {args.rounds}")
    print(f"  budget       {args.budget} mutations/round")
    print("  opponent:", end=" ")
    blue = _load_blue()
    print("\n  Each mutation is scored by judge + Blue Team as it is born -")
    print("  that score IS the evolutionary feedback. Live output follows.\n")

    archive = MapElitesArchive()
    attacker, agent, judge = Attacker(), TargetAgent(), OutcomeJudge()
    for r in range(args.rounds):
        st = run_round(archive, attacker, agent, judge, blue, budget=args.budget)
        print(f"  round {r}: coverage={archive.coverage()}/{archive.total_cells()} "
              f"mean_fitness={archive.mean_fitness():.3f} "
              f"seed_ASR={100*st.seed_asr:.0f}% "
              f"mutation_ASR={100*st.mutation_asr:.0f}%")

    OUT_DIR.mkdir(exist_ok=True)
    archive.save(ARCHIVE_PATH)
    best = archive.best()
    print(f"\n  archive saved -> {ARCHIVE_PATH.name} "
          f"({archive.coverage()} elites)")
    if best:
        print(f"  best fitness {best.fitness:.3f} | {best.payload.text[:70]}")
    print("\n  next: `python main.py defend` to retrain detectors on these.\n")


def cmd_defend(args) -> None:
    """Phase 2: retrain the detectors on what the red team found."""
    _require_ollama()
    _banner("PHASE 2 - BLUE TEAM (retrain detectors on what red found)")

    if args.seeds:
        archive = MapElitesArchive()
        for p in seed_payloads():
            archive.add(p, 0.0)
        print(f"  --seeds: bootstrapping on the {archive.coverage()} raw seeds "
              f"(no evolved elites)")
    elif ARCHIVE_PATH.exists():
        archive = MapElitesArchive.load(ARCHIVE_PATH)
    else:
        sys.exit(f"No archive at {ARCHIVE_PATH}.\nRun `python main.py attack` "
                 f"first, or `python main.py defend --seeds` to bootstrap "
                 f"from the raw seed corpus instead.")

    print(f"  training on {archive.coverage()} payloads + the benign corpus")
    print("  Tier 1 (GBDT, text features) and Tier 2 (GNN, provenance graphs).")
    print("  Tier 2 needs a real agent run per example to build each graph,")
    print("  so this is the slow part - live metrics below.\n")

    blue = retrain_detectors(archive, verbose=True)
    _save_blue(blue)
    print("\n  next: `python main.py judge` to score the archive against these.\n")


def cmd_judge(args) -> None:
    """Phase 3: score the archive and print the scorecard."""
    _require_ollama()
    _banner("PHASE 3 - JUDGMENT & FEEDBACK")
    if ARCHIVE_PATH.exists():
        archive = MapElitesArchive.load(ARCHIVE_PATH)
        payloads = [e.payload for e in archive.cells.values()]
        print(f"  scoring {len(payloads)} evolved elites from {ARCHIVE_PATH.name}")
    else:
        payloads = seed_payloads()
        print(f"  no archive found - scoring the {len(payloads)} raw seeds instead")
        print("  (run `python main.py attack` to score evolved payloads)")
    print("  against:", end=" ")
    blue = _load_blue()
    print()

    rows = score_payloads(payloads, blue=blue, label_prefix="judge")
    print(format_scorecard(rows))

    if args.benign:
        print(format_benign_scorecard(benign_utility(blue=blue)))
    else:
        print("  (add --benign for the false-positive rate on legitimate "
              "traffic)\n")


def cmd_loop(args) -> None:
    """The closed loop: attack, defend and judge, alternating each round."""
    _require_ollama()
    _banner("CLOSED LOOP - attack -> defend -> judge, co-evolving")
    print(f"  {args.rounds} rounds x {args.budget} mutations")
    print("  Round 0 attacks the rule-based Blue Team. Every later round")
    print("  attacks detectors retrained on the previous round's elites.")
    print("  Held-out detector metrics print on the FINAL round only.\n")

    result = coevolve(rounds=args.rounds, budget_per_round=args.budget)

    _print_sawtooth(result["history"])

    archive = result["archive"]
    best = archive.best()
    if best:
        print(f"\n  best overall: fitness={best.fitness:.3f} | {best.payload.text[:70]}")

    OUT_DIR.mkdir(exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(result["history"], indent=2))
    archive.save(ARCHIVE_PATH)
    _save_blue(result["blue"])
    print(f"  history saved  -> {HISTORY_PATH.name}")
    print(f"  archive saved  -> {ARCHIVE_PATH.name}")

    print(format_scorecard(
        score_payloads([e.payload for e in archive.cells.values()],
                       blue=result["blue"], label_prefix="loop"),
        title="FINAL SCORECARD (evolved elites vs. the retrained Blue Team)"))


def main() -> None:
    """Parse arguments and dispatch."""
    ap = argparse.ArgumentParser(
        description="AI Defense Lab - red team / blue team for agentic payments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Start with:  python main.py loop --rounds 3 --budget 20")
    sub = ap.add_subparsers(dest="command")

    p = sub.add_parser("attack", help="PHASE 1: red team evolves payloads")
    p.add_argument("--rounds", type=int, default=1)
    p.add_argument("--budget", type=int, default=20, help="mutations per round")
    p.set_defaults(func=cmd_attack)

    p = sub.add_parser("defend", help="PHASE 2: retrain detectors on the archive")
    p.add_argument("--seeds", action="store_true",
                   help="bootstrap on the raw seed corpus instead of an "
                        "evolved archive (cold start, no attack run needed)")
    p.set_defaults(func=cmd_defend)

    p = sub.add_parser("judge", help="PHASE 3: score the archive, print the scorecard")
    p.add_argument("--benign", action="store_true",
                   help="also measure the false-positive rate on benign traffic")
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("loop", help="the closed loop: all three, co-evolving")
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--budget", type=int, default=20, help="mutations per round")
    p.set_defaults(func=cmd_loop)

    args = ap.parse_args()
    if not getattr(args, "func", None):
        ap.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
