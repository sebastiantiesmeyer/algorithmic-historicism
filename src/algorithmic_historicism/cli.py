from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from .agent.orchestrator import ComponentModelingAgent
from .blender.runner import MockBlenderRunner
from .evaluation.composite import CompositeEvaluator
from .experience.store import TrajectoryStore
from .integrations.evoskill import EvoSkillAdapter
from .skills.candidates import CandidateSkillStore
from .skills.registry import SkillRegistry
from .tasks.models import ComponentTask
from .wiki.local import LocalWikiStore

app = typer.Typer(help="algorithmic-historicism CLI")
skills_app = typer.Typer(help="skill operations")
app.add_typer(skills_app, name="skills")


@app.command("model")
def model_component(
    image: Path = typer.Option(..., "--image"),
    type_: str = typer.Option(..., "--type"),
    description: str = typer.Option(..., "--description"),
    max_iterations: int = typer.Option(3, "--max-iterations"),
):
    task = ComponentTask(
        task_id=f"task-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        component_type=type_,
        reference_image=image,
        description=description,
        max_iterations=max_iterations,
    )
    agent = ComponentModelingAgent(
        trajectory_store=TrajectoryStore(Path("runs")),
        skill_registry=SkillRegistry(Path("skills")),
        blender_runner=MockBlenderRunner(),
        evaluator=CompositeEvaluator(),
    )
    task_dir = agent.run(task)
    typer.echo(str(task_dir))


@app.command("consolidate")
def consolidate(run_path: Path):
    trajectory_path = run_path / "trajectory.json"
    data = trajectory_path.read_text()
    wiki = LocalWikiStore(Path("wiki"))
    wiki.append_observation(
        "general",
        "Trajectory consolidated",
        {"task_id": run_path.name, "attempt_ids": [], "date": datetime.now(timezone.utc).isoformat(), "skill": None},
    )
    typer.echo(f"consolidated {len(data)} bytes")


@skills_app.command("list")
def list_skills():
    registry = SkillRegistry(Path("skills"))
    for skill in registry.list_accepted():
        typer.echo(skill.name)


@skills_app.command("evaluate")
def evaluate_skill(skill_name: str):
    adapter = EvoSkillAdapter()
    result = adapter.evaluate_candidate(skill_name, f"{skill_name}-candidate", ["case_01"])
    typer.echo(result["status"])


@app.command("evolve")
def evolve(skill_name: str):
    store = CandidateSkillStore(Path("skills/.candidates"))
    created = store.create(f"{skill_name}-candidate", provenance="cli:evolve")
    typer.echo(str(created))
