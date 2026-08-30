"""The MAP-Elites archive: one champion payload per (surface, technique, objective) cell."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from schemas import Payload, ArchiveDescriptor, SurfaceType, TechniqueTier, Objective
import random


@dataclass
class Elite:
    """The best payload found so far for one cell, and its score."""
    payload: Payload
    fitness: float


class MapElitesArchive:
    """Keeps one champion per cell, so search is rewarded for breadth."""

    def __init__(self) -> None:
        self.cells: dict[ArchiveDescriptor, Elite] = {}
        self.history: list[tuple[int, ArchiveDescriptor, float]] = []
        self._step = 0

    def add(self, payload: Payload, fit: float) -> bool:
        """Insert a payload; returns True if it claimed or took over its cell."""
        self._step += 1
        key = payload.descriptor
        cur = self.cells.get(key)
        if cur is None or fit > cur.fitness:
            self.cells[key] = Elite(payload, fit)
            self.history.append((self._step, key, fit))
            return True
        return False

    def sample_parent(self) -> Optional[Payload]:
        """Pick a random elite to mutate from."""
        if not self.cells:
            return None
        return random.choice(list(self.cells.values())).payload

    def coverage(self) -> int:
        """How many cells have a working attack."""
        return len(self.cells)

    def total_cells(self) -> int:
        """How many cells exist in total."""
        return len(SurfaceType) * len(TechniqueTier) * len(Objective)

    def mean_fitness(self) -> float:
        """Mean score across occupied cells."""
        return (sum(e.fitness for e in self.cells.values()) / len(self.cells)) if self.cells else 0.0

    def best(self) -> Optional[Elite]:
        """The single highest-scoring elite."""
        return max(self.cells.values(), key=lambda e: e.fitness) if self.cells else None

    def as_records(self) -> list[dict]:
        """Flatten to plain dicts for reporting."""
        return [{"surface": k[0].value, "technique": k[1].value,
                 "objective": k[2].value, "fitness": e.fitness,
                 "text": e.payload.text} for k, e in self.cells.items()]

    def save(self, path) -> None:
        """Persist the archive, including target_spec so the judge can score it later."""
        rows = [{"surface": k[0].value, "technique": k[1].value,
                 "objective": k[2].value, "fitness": e.fitness,
                 "text": e.payload.text,
                 "target_spec": dict(e.payload.target_spec)}
                for k, e in self.cells.items()]
        Path(path).write_text(json.dumps(rows, indent=2))

    @classmethod
    def load(cls, path) -> "MapElitesArchive":
        """Rebuild an archive saved by save()."""
        archive = cls()
        for r in json.loads(Path(path).read_text()):
            payload = Payload(text=r["text"], surface=SurfaceType(r["surface"]),
                              technique=TechniqueTier(r["technique"]),
                              objective=Objective(r["objective"]),
                              target_spec=r.get("target_spec", {}))
            archive.cells[payload.descriptor] = Elite(payload, r["fitness"])
        return archive
