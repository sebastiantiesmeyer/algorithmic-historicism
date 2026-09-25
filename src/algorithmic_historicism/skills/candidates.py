from __future__ import annotations

from pathlib import Path


class CandidateSkillStore:
    def __init__(self, candidates_root: Path):
        self.candidates_root = candidates_root
        self.candidates_root.mkdir(parents=True, exist_ok=True)

    def create(self, name: str, provenance: str) -> Path:
        path = self.candidates_root / name
        path.mkdir(parents=True, exist_ok=False)
        (path / "SKILL.md").write_text(f"# {name}\n\nProvenance: {provenance}\n")
        (path / "metadata.yaml").write_text(f"name: {name}\nstate: candidate\nprovenance: {provenance}\n")
        (path / "implementation.py").write_text("def build_component(params, context):\n    return params, context\n")
        return path

    def lifecycle_decision(self, name: str, decision: str) -> None:
        path = self.candidates_root / name / "metadata.yaml"
        content = path.read_text()
        path.write_text(content + f"decision: {decision}\n")
