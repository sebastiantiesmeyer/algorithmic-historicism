from pathlib import Path

from algorithmic_historicism.tasks.models import ComponentTask


def test_component_task_serialization_roundtrip():
    task = ComponentTask(
        task_id="t1",
        component_type="rustication",
        reference_image=Path("examples/rustication/reference.png"),
        description="desc",
        hints={"a": 1},
        max_iterations=3,
    )
    restored = ComponentTask.model_validate_json(task.model_dump_json())
    assert restored == task
