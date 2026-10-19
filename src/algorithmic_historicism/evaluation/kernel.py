from __future__ import annotations

from dataclasses import dataclass, field

from .base import EvaluationGate, EvaluationRequest, EvaluationResult, TaskEvaluator


@dataclass(frozen=True)
class EvaluationPolicy:
    """Generic promotion signal configured with task-specific score requirements."""

    threshold: float = 0.75
    required_scores: dict[str, float] = field(default_factory=dict)
    score_weights: dict[str, float] = field(default_factory=dict)

    def aggregate(self, scores: dict[str, float | None]) -> float:
        available = {name: value for name, value in scores.items() if value is not None}
        if not available:
            return 0.0
        weights = {name: self.score_weights.get(name, 1.0) for name in available}
        total_weight = sum(weights.values())
        if total_weight <= 0:
            raise ValueError("Evaluation score weights must sum to a positive value")
        return sum(available[name] * weights[name] for name in available) / total_weight

    def accepts(self, result: EvaluationResult) -> bool:
        required_pass = all(
            result.scores.get(name) is not None and result.scores[name] >= minimum
            for name, minimum in self.required_scores.items()
        )
        return result.gate_passed and required_pass and result.score >= self.threshold


class EvaluationKernel:
    """Runs generic gates and policy around a task-provided evaluator."""

    def __init__(
        self,
        *,
        task_evaluator: TaskEvaluator,
        gates: list[EvaluationGate] | None = None,
        policy: EvaluationPolicy | None = None,
    ):
        self.task_evaluator = task_evaluator
        self.gates = gates or []
        self.policy = policy or EvaluationPolicy()

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        gate_results = [gate.check(request) for gate in self.gates]
        failures = [result for result in gate_results if not result.passed]
        if failures:
            messages = [result.message for result in failures]
            return EvaluationResult(
                score=0.0,
                gate_passed=False,
                passed=False,
                critique="; ".join(messages),
                repair_targets=messages,
                execution_errors=messages,
                details={"gates": [result.model_dump(mode="json") for result in gate_results]},
            )

        result = self.task_evaluator.evaluate(request)
        result.gate_passed = True
        result.score = self.policy.aggregate(result.scores)
        result.passed = self.policy.accepts(result)
        result.details.setdefault(
            "gates", [gate_result.model_dump(mode="json") for gate_result in gate_results]
        )
        return result
