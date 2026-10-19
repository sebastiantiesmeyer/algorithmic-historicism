from pathlib import Path

import pytest

from algorithmic_historicism.evaluation import (
    EvaluationKernel,
    EvaluationPolicy,
    EvaluationRequest,
    EvaluationResult,
    GateResult,
)


class RequiredArtifactGate:
    def check(self, request: EvaluationRequest) -> GateResult:
        artifact = request.artifacts.get("output")
        passed = artifact is not None and artifact.exists()
        return GateResult(passed=passed, message="artifact present" if passed else "artifact missing")


class UserSuppliedEvaluator:
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        return EvaluationResult(
            critique="Task-specific comparison",
            scores={"fidelity": 0.9, "simplicity": 0.6},
        )


def test_kernel_composes_generic_gates_with_task_evaluator(tmp_path: Path):
    artifact = tmp_path / "output.svg"
    artifact.write_text("<svg/>", encoding="utf-8")
    kernel = EvaluationKernel(
        task_evaluator=UserSuppliedEvaluator(),
        gates=[RequiredArtifactGate()],
        policy=EvaluationPolicy(
            threshold=0.7,
            required_scores={"fidelity": 0.8},
            score_weights={"fidelity": 3.0, "simplicity": 1.0},
        ),
    )

    result = kernel.evaluate(EvaluationRequest(case_id="case-1", artifacts={"output": artifact}))

    assert result.gate_passed
    assert result.score == pytest.approx(0.825)
    assert result.passed


def test_gate_failure_skips_task_evaluation(tmp_path: Path):
    class MustNotRun:
        def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
            raise AssertionError("task evaluator should not run after a gate failure")

    kernel = EvaluationKernel(task_evaluator=MustNotRun(), gates=[RequiredArtifactGate()])
    result = kernel.evaluate(EvaluationRequest(case_id="case-1"))

    assert not result.gate_passed
    assert not result.passed
    assert result.score == 0.0
    assert result.execution_errors == ["artifact missing"]
