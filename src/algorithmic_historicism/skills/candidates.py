from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

import yaml

from .format import SkillDocument, validate_skill_name


class CandidateSkillStore:
    def __init__(self, candidates_root: Path):
        self.candidates_root = candidates_root
        self.candidates_root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        name: str,
        provenance: str,
        *,
        description: str = "Candidate agent skill.",
        instructions: str | None = None,
        parent_skill: str | None = None,
        source_patterns: list[str] | None = None,
    ) -> Path:
        validate_skill_name(name)
        path = self.candidates_root / name
        if path.exists():
            raise FileExistsError(f"Candidate already exists: {path}")
        path.mkdir(parents=True, exist_ok=False)
        created_at = datetime.now(timezone.utc).isoformat()
        document = SkillDocument(
            name=name,
            description=description,
            instructions=instructions or f"# {name}\n\nApply the procedure supported by the recorded evidence.",
        )
        (path / "SKILL.md").write_text(document.render(), encoding="utf-8")
        metadata = {
            "name": name,
            "state": "PROPOSED",
            "provenance": provenance,
            "created_at": created_at,
            "parent_skill": parent_skill,
            "mutation_reason": "benchmark-evolution",
            "source_patterns": source_patterns or [],
        }
        (path / "metadata.yaml").write_text(
            yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False), encoding="utf-8"
        )
        return path

    def lifecycle_decision(self, name: str, decision: str, **extra: object) -> None:
        path = self.candidates_root / name / "metadata.yaml"
        metadata = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        metadata.update({
            "state": decision,
            "decision": decision,
            "decision_date": datetime.now(timezone.utc).isoformat(),
            **extra,
        })
        path.write_text(yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False), encoding="utf-8")

    def promote(self, name: str, accepted_root: Path) -> Path:
        source = self.candidates_root / name
        if not source.exists():
            raise FileNotFoundError(f"Candidate skill not found: {name}")
        destination = accepted_root / name
        if destination.exists():
            raise FileExistsError(f"Accepted skill already exists: {destination}")
        accepted_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination)
        metadata_path = destination / "metadata.yaml"
        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        metadata["state"] = "accepted"
        metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False), encoding="utf-8")
        return destination

    def list_candidates(self) -> list[Path]:
        if not self.candidates_root.exists():
            return []
        return sorted(p for p in self.candidates_root.iterdir() if p.is_dir() and not p.name.startswith("."))
