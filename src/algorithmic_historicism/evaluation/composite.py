from __future__ import annotations

from pathlib import Path

from .base import EvaluationResult
from .geometry import GeometryValidator
from .visual import VisualEvaluator


class CompositeEvaluator:
    def __init__(self, geometry_validator: GeometryValidator | None = None, visual_evaluator: VisualEvaluator | None = None):
        self.geometry_validator = geometry_validator or GeometryValidator()
        self.visual_evaluator = visual_evaluator or VisualEvaluator()

    def evaluate(self, *, return_code: int, blend_path: Path, render_path: Path, reference: Path, description: str) -> EvaluationResult:
        geometry_valid, message = self.geometry_validator.validate(return_code, blend_path)
        result = self.visual_evaluator.evaluate(reference, render_path, description, geometry_valid)
        if not geometry_valid:
            result.critique = message
            result.passed = False
        return result
