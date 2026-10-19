from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


Split = Literal["training", "validation", "test"]


class BenchmarkCase(BaseModel):
    case_id: str
    input: str
    expected: str
    split: Split
    metadata: dict[str, object] = Field(default_factory=dict)


class BenchmarkSuite(BaseModel):
    name: str
    cases: list[BenchmarkCase]

    @classmethod
    def from_jsonl(cls, path: Path, *, name: str | None = None) -> "BenchmarkSuite":
        cases = [
            BenchmarkCase.model_validate(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return cls(name=name or path.stem, cases=cases)

    def select(self, split: Split) -> list[BenchmarkCase]:
        return [case for case in self.cases if case.split == split]

    def validate_splits(self) -> None:
        missing = [split for split in ("training", "validation", "test") if not self.select(split)]
        if missing:
            raise ValueError(f"Benchmark is missing split(s): {', '.join(missing)}")


class RolloutTrace(BaseModel):
    case_id: str
    split: Split
    input: str
    expected: str
    prediction: str
    score: float = 0.0
    skill_name: str | None = None
    events: list[dict[str, object]] = Field(default_factory=list)
    evaluation: dict[str, object] = Field(default_factory=dict)


class SkillProposal(BaseModel):
    name: str
    description: str
    instructions: str
    rationale: str
    source_patterns: list[str] = Field(default_factory=list)


class IterationResult(BaseModel):
    iteration: int
    candidate_name: str | None
    baseline_score: float
    candidate_score: float | None
    frontier_admitted: bool = False
    accepted: bool


class EvolutionReport(BaseModel):
    benchmark: str
    baseline_validation_score: float
    best_validation_score: float
    baseline_test_score: float
    test_score: float
    accepted_skill: str | None
    iterations: list[IterationResult] = Field(default_factory=list)
