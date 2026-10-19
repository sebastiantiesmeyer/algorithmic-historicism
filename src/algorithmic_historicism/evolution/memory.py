from __future__ import annotations

import re
from typing import Protocol

from ..wiki.models import ExperienceRecord, MemoryCandidate
from ..wiki.workspace import WikiWorkspace
from .models import RolloutTrace


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "run"


class MemoryConsolidator(Protocol):
    def consolidate(
        self, experiences: list[ExperienceRecord], wiki: WikiWorkspace
    ) -> list[str]: ...


class TraceMemoryMaintainer:
    """Converts evaluated rollouts into the shared experience-memory pipeline."""

    def __init__(self, run_id: str, consolidator: MemoryConsolidator | None = None):
        if consolidator is None:
            from ..wiki.consolidator import EvidenceConsolidator

            consolidator = EvidenceConsolidator()
        self.run_id = _slug(run_id)
        self.consolidator = consolidator

    def consolidate(
        self,
        traces: list[RolloutTrace],
        wiki: WikiWorkspace,
        iteration: int,
    ) -> list[str]:
        records = [self._record(trace, iteration) for trace in traces]
        return self.consolidator.consolidate(records, wiki)

    def _record(self, trace: RolloutTrace, iteration: int) -> ExperienceRecord:
        candidates = [
            MemoryCandidate.model_validate(candidate)
            for candidate in trace.evaluation.get("memory_candidates", [])
        ]
        return ExperienceRecord(
            experience_id=f"{self.run_id}-i{iteration:03d}-{_slug(trace.case_id)}",
            source=self.run_id,
            task_summary=trace.input,
            outcome="success" if trace.score >= 1.0 else "failure",
            score=trace.score,
            strategy_ids=[trace.skill_name] if trace.skill_name else [],
            artifacts={"expected": trace.expected, "prediction": trace.prediction},
            evaluation=trace.evaluation,
            memory_candidates=candidates,
            tags=[trace.split],
        )
