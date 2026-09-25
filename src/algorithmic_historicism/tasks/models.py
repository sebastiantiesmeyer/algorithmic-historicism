from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ComponentTask(BaseModel):
    task_id: str
    component_type: str
    reference_image: Path
    description: str
    hints: dict[str, Any] = Field(default_factory=dict)
    max_iterations: int = 3
