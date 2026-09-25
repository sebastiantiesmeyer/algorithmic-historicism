from pathlib import Path

from algorithmic_historicism.agent.orchestrator import ComponentModelingAgent
from algorithmic_historicism.blender.runner import MockBlenderRunner
from algorithmic_historicism.evaluation.base import EvaluationResult
from algorithmic_historicism.evaluation.composite import CompositeEvaluator
from algorithmic_historicism.evaluation.visual import VisualEvaluator
from algorithmic_historicism.experience.store import TrajectoryStore
from algorithmic_historicism.skills.registry import SkillRegistry
from algorithmic_historicism.tasks.models import ComponentTask


class AlwaysFailVisualEvaluator(VisualEvaluator):
    def evaluate(self, reference: Path, render: Path, description: str, geometry_valid: bool) -> EvaluationResult:
        return EvaluationResult(geometry_valid=geometry_valid, critique="fail", passed=False)


def test_iteration_limit_respected(tmp_path: Path):
    (tmp_path / "ref.png").write_bytes(b"r")
    (tmp_path / "skills").mkdir()
    evalr = CompositeEvaluator(visual_evaluator=AlwaysFailVisualEvaluator())
    agent = ComponentModelingAgent(
        trajectory_store=TrajectoryStore(tmp_path / "runs"),
        skill_registry=SkillRegistry(tmp_path / "skills"),
        blender_runner=MockBlenderRunner(),
        evaluator=evalr,
    )
    task = ComponentTask(
        task_id="iter-limit",
        component_type="rustication",
        reference_image=tmp_path / "ref.png",
        description="d",
        max_iterations=3,
    )
    run_dir = agent.run(task)
    attempts = list(run_dir.glob("attempt_*"))
    assert len(attempts) == 3


def test_mock_end_to_end_run(tmp_path: Path):
    (tmp_path / "ref.png").write_bytes(b"r")
    skill_dir = tmp_path / "skills" / "routed-rustication"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# skill")

    agent = ComponentModelingAgent(
        trajectory_store=TrajectoryStore(tmp_path / "runs"),
        skill_registry=SkillRegistry(tmp_path / "skills"),
        blender_runner=MockBlenderRunner(),
        evaluator=CompositeEvaluator(),
    )
    task = ComponentTask(
        task_id="ok-run",
        component_type="rustication",
        reference_image=tmp_path / "ref.png",
        description="d",
    )
    run_dir = agent.run(task)
    assert (run_dir / "trajectory.json").exists()
    assert len(list(run_dir.glob("attempt_*"))) == 1
