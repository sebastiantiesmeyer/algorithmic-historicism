from __future__ import annotations

from pathlib import Path

import yaml

from .models import SkillPackage
from .format import load_skill_document


class SkillRegistry:
    def __init__(self, skills_root: Path):
        self.skills_root = skills_root

    def _load_metadata(self, path: Path) -> dict:
        metadata_path = path / "metadata.yaml"
        if not metadata_path.exists():
            return {}
        with metadata_path.open("r", encoding="utf-8") as fh:
            try:
                payload = yaml.safe_load(fh) or {}
            except Exception:
                payload = {}
        return payload if isinstance(payload, dict) else {}

    def list_accepted(self) -> list[SkillPackage]:
        packages: list[SkillPackage] = []
        if not self.skills_root.exists():
            return packages
        for path in sorted(self.skills_root.iterdir()):
            if not path.is_dir() or path.name.startswith("."):
                continue
            metadata = self._load_metadata(path)
            if (path / "SKILL.md").exists():
                try:
                    document = load_skill_document(path / "SKILL.md")
                except ValueError:
                    document = None
                packages.append(
                    SkillPackage(
                        name=document.name if document else path.name,
                        root=path,
                        accepted=True,
                        description=document.description if document else metadata.get("description", ""),
                        skill_md_path=path / "SKILL.md",
                        implementation_path=path / "implementation.py",
                        metadata=metadata,
                        parameters=metadata.get("parameters", []),
                        applicability=metadata.get("applicability", []),
                        version=str(metadata.get("version", "0.1.0")),
                        provenance=str(metadata.get("provenance", "")) or None,
                        benchmark_history=list(metadata.get("benchmark_history", [])),
                        known_limitations=list(metadata.get("known_limitations", [])),
                    )
                )
        return packages
