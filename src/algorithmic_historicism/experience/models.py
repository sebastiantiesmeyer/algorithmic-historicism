from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class AttemptSummary(BaseModel):
    attempt_id: str
    plan_path: Path
    generated_script_path: Path
    stdout_path: Path
    stderr_path: Path
    blend_path: Path
    render_path: Path
    evaluation_path: Path
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trajectory(BaseModel):
    task_id: str
    task_path: Path
    attempts: list[AttemptSummary] = Field(default_factory=list)
