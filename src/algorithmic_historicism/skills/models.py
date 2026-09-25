from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class SkillPackage(BaseModel):
    name: str
    root: Path
    accepted: bool
