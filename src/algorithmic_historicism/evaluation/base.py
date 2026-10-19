from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    """Task-neutral inputs passed through the evaluation mechanism."""

    case_id: str
    task: dict[str, object] = Field(default_factory=dict)
    candidate: dict[str, object] = Field(default_factory=dict)
    artifacts: dict[str, Path] = Field(default_factory=dict)
    references: dict[str, Path] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class GateResult(BaseModel):
    passed: bool
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    score: float = 0.0
    gate_passed: bool = True
    confidence: float = 1.0
    critique: str = ""
    passed: bool = False
    preserve: list[str] = Field(default_factory=list)
    repair_targets: list[str] = Field(default_factory=list)
    execution_errors: list[str] = Field(default_factory=list)
    generalizable_observations: list[str] = Field(default_factory=list)
    memory_candidates: list[dict[str, object]] = Field(default_factory=list)
    scores: dict[str, float | None] = Field(default_factory=dict)
    details: dict[str, object] = Field(default_factory=dict)

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        if "scores" not in data:
            data["scores"] = {}
        return data


class EvaluationGate(Protocol):
    def check(self, request: EvaluationRequest) -> GateResult: ...


class TaskEvaluator(Protocol):
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult: ...
