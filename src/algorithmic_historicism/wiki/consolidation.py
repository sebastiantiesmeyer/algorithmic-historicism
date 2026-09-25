from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .local import LocalWikiStore


def consolidate_trajectory(run_dir: Path, wiki_store: LocalWikiStore, topic: str = "general") -> None:
    trajectory_path = run_dir / "trajectory.json"
    if not trajectory_path.exists():
        return
    wiki_store.append_observation(
        topic,
        "Consolidated complete trajectory",
        {
            "task_id": run_dir.name,
            "attempt_ids": [],
            "date": datetime.now(timezone.utc).isoformat(),
            "skill": None,
        },
    )
