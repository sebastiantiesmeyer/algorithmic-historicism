from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..blender.runner import BlenderRunner
from ..evaluation.composite import CompositeEvaluator
from ..experience.models import AttemptSummary
from ..experience.store import TrajectoryStore
from ..skills.registry import SkillRegistry
from ..skills.retrieval import retrieve_relevant_skills
from ..tasks.models import ComponentTask
from .modeler import default_plan


class ComponentModelingAgent:
    def __init__(
        self,
        *,
        trajectory_store: TrajectoryStore,
        skill_registry: SkillRegistry,
        blender_runner: BlenderRunner,
        evaluator: CompositeEvaluator,
    ):
        self.trajectory_store = trajectory_store
        self.skill_registry = skill_registry
        self.blender_runner = blender_runner
        self.evaluator = evaluator

    def run(self, task: ComponentTask) -> Path:
        task_dir = self.trajectory_store.init_task(task)
        relevant_skills = retrieve_relevant_skills(task, self.skill_registry)

        for _ in range(task.max_iterations):
            attempt_dir = self.trajectory_store.next_attempt_dir(task_dir)
            plan = default_plan(task)
            plan_path = attempt_dir / "plan.json"
            self.trajectory_store.write_json(plan_path, {
                "architectural_interpretation": plan.architectural_interpretation,
                "geometric_primitives": plan.geometric_primitives,
                "symmetry_assumptions": plan.symmetry_assumptions,
                "repetition_assumptions": plan.repetition_assumptions,
                "strategy": plan.strategy,
                "dimensions_and_ratios": plan.dimensions_and_ratios,
                "uncertain_features": plan.uncertain_features,
                "required_existing_skills": relevant_skills,
                "potentially_new_capability": plan.potentially_new_capability,
            })

            script_path = attempt_dir / "generated.py"
            script_path.write_text(
                "# auto-generated task script\n"
                "def build_component(params, context):\n"
                "    return {'status': 'ok', 'component': params.get('component_type')}\n"
            )

            run_result = self.blender_runner.run(script_path, attempt_dir)
            stdout_path = attempt_dir / "stdout.txt"
            stderr_path = attempt_dir / "stderr.txt"
            stdout_path.write_text(run_result.stdout)
            stderr_path.write_text(run_result.stderr)

            evaluation = self.evaluator.evaluate(
                return_code=run_result.return_code,
                blend_path=run_result.blend_path,
                render_path=run_result.render_path,
                reference=task.reference_image,
                description=task.description,
            )
            evaluation_path = attempt_dir / "evaluation.json"
            self.trajectory_store.write_json(evaluation_path, evaluation.model_dump())

            summary = AttemptSummary(
                attempt_id=attempt_dir.name,
                plan_path=plan_path,
                generated_script_path=script_path,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                blend_path=run_result.blend_path,
                render_path=run_result.render_path,
                evaluation_path=evaluation_path,
                created_at=datetime.now(timezone.utc),
            )
            self.trajectory_store.append_attempt(task_dir, summary)

            if evaluation.passed:
                break
        return task_dir
