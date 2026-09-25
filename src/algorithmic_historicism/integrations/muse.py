from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MuseAdapter:
    name: str = "muse-adapter"

    def propose_missing_skill(self, task_type: str) -> dict:
        return {"task_type": task_type, "proposal": f"candidate-{task_type}", "status": "adapter-ready"}
