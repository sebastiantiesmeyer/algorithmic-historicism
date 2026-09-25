from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WikiSkillAdapter:
    name: str = "wikiskill-adapter"

    def consolidate(self, trajectory_path: str) -> dict:
        return {"trajectory_path": trajectory_path, "status": "adapter-ready"}
