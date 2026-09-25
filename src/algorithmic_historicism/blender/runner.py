from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlenderRunResult:
    blender_version: str
    return_code: int
    stdout: str
    stderr: str
    blend_path: Path
    render_path: Path


class BlenderRunner:
    def run(self, script_path: Path, attempt_dir: Path, timeout_seconds: int = 60) -> BlenderRunResult:
        raise NotImplementedError


class MockBlenderRunner(BlenderRunner):
    def run(self, script_path: Path, attempt_dir: Path, timeout_seconds: int = 60) -> BlenderRunResult:
        blend_path = attempt_dir / "model.blend"
        render_path = attempt_dir / "render.png"
        blend_path.write_text("mock blend")
        render_path.write_bytes(b"mock-render")
        return BlenderRunResult(
            blender_version="mock-0.0",
            return_code=0,
            stdout=f"Executed {script_path.name}",
            stderr="",
            blend_path=blend_path,
            render_path=render_path,
        )


class SubprocessBlenderRunner(BlenderRunner):
    def __init__(self, blender_bin: str):
        self.blender_bin = blender_bin

    def _version(self) -> str:
        cmd = [self.blender_bin, "--version"]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        first_line = completed.stdout.splitlines()[0] if completed.stdout else "unknown"
        return first_line

    def run(self, script_path: Path, attempt_dir: Path, timeout_seconds: int = 60) -> BlenderRunResult:
        blend_path = attempt_dir / "model.blend"
        render_path = attempt_dir / "render.png"
        cmd = [
            self.blender_bin,
            "--background",
            "--python",
            str(script_path),
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            if completed.returncode == 0:
                blend_path.write_text("placeholder blend artifact")
                render_path.write_bytes(b"placeholder render artifact")
            return BlenderRunResult(
                blender_version=self._version(),
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                blend_path=blend_path,
                render_path=render_path,
            )
        except subprocess.TimeoutExpired as exc:
            return BlenderRunResult(
                blender_version=self._version(),
                return_code=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\nBlender execution timed out",
                blend_path=blend_path,
                render_path=render_path,
            )
