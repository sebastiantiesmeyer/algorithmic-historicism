from __future__ import annotations

from pathlib import Path

from .models import SkillPackage


class SkillRegistry:
    def __init__(self, skills_root: Path):
        self.skills_root = skills_root

    def list_accepted(self) -> list[SkillPackage]:
        packages: list[SkillPackage] = []
        for path in sorted(self.skills_root.iterdir()):
            if not path.is_dir() or path.name.startswith("."):
                continue
            if (path / "SKILL.md").exists():
                packages.append(SkillPackage(name=path.name, root=path, accepted=True))
        return packages
