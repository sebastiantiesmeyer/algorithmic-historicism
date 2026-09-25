from __future__ import annotations

from typing import Protocol


class WikiStore(Protocol):
    def append_observation(self, topic: str, observation: str, provenance: dict) -> None: ...
