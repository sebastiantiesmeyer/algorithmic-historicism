from __future__ import annotations

from pydantic import BaseModel


class EvaluationResult(BaseModel):
    geometry_valid: bool
    visual_similarity: float | None = None
    structural_similarity: float | None = None
    simplicity: float | None = None
    critique: str
    passed: bool
