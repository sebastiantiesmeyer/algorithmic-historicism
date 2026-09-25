from __future__ import annotations

import json
from pathlib import Path

from ..tasks.models import ComponentTask
from .models import AttemptSummary, Trajectory


class TrajectoryStore:
    def __init__(self, runs_root: Path):
        self.runs_root = runs_root
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def init_task(self, task: ComponentTask) -> Path:
        task_dir = self.runs_root / task.task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "task.json").write_text(task.model_dump_json(indent=2, serialize_as_any=True))
        trajectory = Trajectory(task_id=task.task_id, task_path=task_dir / "task.json")
        (task_dir / "trajectory.json").write_text(trajectory.model_dump_json(indent=2))
        return task_dir

    def next_attempt_dir(self, task_dir: Path) -> Path:
        existing = sorted(p for p in task_dir.glob("attempt_*") if p.is_dir())
        number = len(existing) + 1
        attempt_dir = task_dir / f"attempt_{number:03d}"
        if attempt_dir.exists():
            raise FileExistsError(f"Attempt directory already exists: {attempt_dir}")
        attempt_dir.mkdir(parents=True)
        return attempt_dir

    def append_attempt(self, task_dir: Path, summary: AttemptSummary) -> None:
        trajectory_path = task_dir / "trajectory.json"
        trajectory = Trajectory.model_validate_json(trajectory_path.read_text())
        trajectory.attempts.append(summary)
        trajectory_path.write_text(trajectory.model_dump_json(indent=2))

    def write_json(self, path: Path, payload: dict) -> None:
        if path.exists():
            raise FileExistsError(f"Immutable artifact already exists: {path}")
        path.write_text(json.dumps(payload, indent=2))
