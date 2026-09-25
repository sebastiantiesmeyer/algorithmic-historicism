from __future__ import annotations

from ..tasks.models import ComponentTask
from .registry import SkillRegistry


def retrieve_relevant_skills(task: ComponentTask, registry: SkillRegistry) -> list[str]:
    names = [pkg.name for pkg in registry.list_accepted()]
    return [name for name in names if task.component_type.replace("_", "-") in name or task.component_type in name]
