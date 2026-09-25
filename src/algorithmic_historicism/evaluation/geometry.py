from __future__ import annotations

from pathlib import Path


class GeometryValidator:
    def validate(self, return_code: int, blend_path: Path, expected_object_exists: bool = True) -> tuple[bool, str]:
        if return_code != 0:
            return False, "Blender execution failed"
        if not expected_object_exists:
            return False, "Expected object missing"
        if not blend_path.exists() or blend_path.stat().st_size == 0:
            return False, "Blend output missing or empty"
        return True, "Geometry validation passed"
