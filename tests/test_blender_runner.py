from pathlib import Path

from algorithmic_historicism.blender.runner import SubprocessBlenderRunner


def test_blender_subprocess_failure_handling(tmp_path: Path):
    script = tmp_path / "gen.py"
    script.write_text("print('hello')")
    runner = SubprocessBlenderRunner("python")
    result = runner.run(script, tmp_path, timeout_seconds=10)
    assert result.return_code != 0
    assert result.blender_version
