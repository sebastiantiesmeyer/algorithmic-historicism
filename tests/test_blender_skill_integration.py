import os
from pathlib import Path

import pytest

from algorithmic_historicism.blender.runner import SubprocessBlenderRunner


@pytest.mark.blender_integration
@pytest.mark.skipif(not os.getenv("BLENDER_BIN"), reason="BLENDER_BIN not configured")
def test_rustication_skill_blender_integration(tmp_path: Path):
    script = tmp_path / "generated.py"
    script.write_text("import bpy\n")
    runner = SubprocessBlenderRunner(os.environ["BLENDER_BIN"])
    result = runner.run(script, tmp_path, timeout_seconds=60)
    assert result.return_code == 0
