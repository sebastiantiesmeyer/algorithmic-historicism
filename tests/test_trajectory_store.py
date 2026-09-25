from pathlib import Path

import pytest

from algorithmic_historicism.experience.models import AttemptSummary
from algorithmic_historicism.experience.store import TrajectoryStore
from algorithmic_historicism.tasks.models import ComponentTask


def test_trajectory_persistence_and_immutability(tmp_path: Path):
    store = TrajectoryStore(tmp_path / "runs")
    task = ComponentTask(
        task_id="task-1",
        component_type="rustication",
        reference_image=Path("ref.png"),
        description="d",
    )
    task_dir = store.init_task(task)
    attempt_dir = store.next_attempt_dir(task_dir)

    payload = {"key": "value"}
    json_path = attempt_dir / "plan.json"
    store.write_json(json_path, payload)
    with pytest.raises(FileExistsError):
        store.write_json(json_path, payload)

    dummy = attempt_dir / "x.txt"
    dummy.write_text("x")
    summary = AttemptSummary(
        attempt_id="attempt_001",
        plan_path=json_path,
        generated_script_path=dummy,
        stdout_path=dummy,
        stderr_path=dummy,
        blend_path=dummy,
        render_path=dummy,
        evaluation_path=dummy,
    )
    store.append_attempt(task_dir, summary)
    trajectory = (task_dir / "trajectory.json").read_text()
    assert "attempt_001" in trajectory
