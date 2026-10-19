from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


_SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class SkillDocument:
    name: str
    description: str
    instructions: str
    metadata: dict[str, object] = field(default_factory=dict)

    def render(self) -> str:
        frontmatter = {**self.metadata, "name": self.name, "description": self.description}
        encoded = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).strip()
        return f"---\n{encoded}\n---\n\n{self.instructions.strip()}\n"


def validate_skill_name(name: str) -> None:
    if len(name) > 64 or not _SKILL_NAME.fullmatch(name):
        raise ValueError("Skill names must be <=64 characters of lowercase letters, digits, and hyphens")


def parse_skill_text(text: str) -> SkillDocument:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must begin with YAML frontmatter")
    try:
        raw_frontmatter, instructions = text[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError("SKILL.md frontmatter is not terminated") from exc

    frontmatter = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    name = str(frontmatter.pop("name", ""))
    description = str(frontmatter.pop("description", ""))
    validate_skill_name(name)
    if not description.strip():
        raise ValueError("SKILL.md requires a non-empty description")
    if not instructions.strip():
        raise ValueError("SKILL.md requires instructions")
    return SkillDocument(name, description, instructions.strip(), frontmatter)


def load_skill_document(path: Path) -> SkillDocument:
    return parse_skill_text(path.read_text(encoding="utf-8"))
