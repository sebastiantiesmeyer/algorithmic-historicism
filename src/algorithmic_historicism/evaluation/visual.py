from __future__ import annotations

from pathlib import Path

from .base import EvaluationResult


class VisualEvaluator:
    def evaluate(self, reference: Path, render: Path, description: str, geometry_valid: bool) -> EvaluationResult:
        if not geometry_valid:
            return EvaluationResult(geometry_valid=False, critique="Geometry invalid, visual critique deferred", passed=False)
        if not render.exists() or render.stat().st_size == 0:
            return EvaluationResult(geometry_valid=True, critique="Render missing", passed=False)
        critique = f"Mock critique for '{description}': maintain silhouette and proportion."
        return EvaluationResult(
            geometry_valid=True,
            visual_similarity=0.75,
            structural_similarity=0.7,
            simplicity=0.9,
            critique=critique,
            passed=True,
        )
