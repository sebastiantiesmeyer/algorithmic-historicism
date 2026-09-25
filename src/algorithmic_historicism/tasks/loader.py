from __future__ import annotations

import json
from pathlib import Path

import yaml

from .models import ComponentTask


def load_task(path: Path) -> ComponentTask:
    payload: dict
    if path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(path.read_text())
    else:
        payload = json.loads(path.read_text())
    return ComponentTask.model_validate(payload)
