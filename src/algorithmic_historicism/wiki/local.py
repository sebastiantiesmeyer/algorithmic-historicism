from __future__ import annotations

from pathlib import Path


class LocalWikiStore:
    def __init__(self, wiki_root: Path):
        self.wiki_root = wiki_root
        self.wiki_root.mkdir(parents=True, exist_ok=True)

    def append_observation(self, topic: str, observation: str, provenance: dict) -> None:
        path = self.wiki_root / f"{topic}.md"
        if not path.exists():
            path.write_text(f"# {topic}\n\n")
        line = (
            f"- observation: {observation}\n"
            f"  task_id: {provenance.get('task_id')}\n"
            f"  attempt_ids: {provenance.get('attempt_ids', [])}\n"
            f"  date: {provenance.get('date')}\n"
            f"  skill: {provenance.get('skill')}\n"
        )
        path.write_text(path.read_text() + line)
