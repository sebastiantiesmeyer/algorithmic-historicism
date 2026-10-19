from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class SkillPackage(BaseModel):
    name: str
    root: Path
    accepted: bool = True
    description: str = ""
    skill_md_path: Path | None = None
    implementation_path: Path | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    parameters: list[str] = Field(default_factory=list)
    applicability: list[str] = Field(default_factory=list)
    version: str = "0.1.0"
    provenance: str | None = None
    benchmark_history: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)

    @property
    def skill_markdown(self) -> Path | None:
        return self.skill_md_path or (self.root / "SKILL.md" if self.root.exists() else None)
