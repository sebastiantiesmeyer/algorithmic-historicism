from __future__ import annotations

from dataclasses import dataclass

from ..skills.format import SkillDocument


@dataclass(frozen=True)
class FrontierEntry:
    name: str
    score: float
    skill: SkillDocument | None
    parent: str | None = None


class CandidateFrontier:
    """Bounded, validation-ranked program frontier inspired by EvoSkill."""

    def __init__(self, capacity: int = 3):
        if capacity < 1:
            raise ValueError("Frontier capacity must be positive")
        self.capacity = capacity
        self._entries: list[FrontierEntry] = []

    @property
    def entries(self) -> tuple[FrontierEntry, ...]:
        return tuple(self._entries)

    @property
    def best(self) -> FrontierEntry:
        if not self._entries:
            raise LookupError("Frontier is empty")
        return self._entries[0]

    def add(self, entry: FrontierEntry) -> bool:
        if len(self._entries) >= self.capacity and entry.score <= self._entries[-1].score:
            return False
        self._entries.append(entry)
        self._entries.sort(key=lambda item: (-item.score, item.name))
        del self._entries[self.capacity :]
        return entry in self._entries
