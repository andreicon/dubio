from __future__ import annotations

import subprocess

from dubio.errors import DubError


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise DubError(
            "FFMPEG-001",
            "ffmpeg command failed",
            {"cmd": cmd, "stdout": result.stdout, "stderr": result.stderr},
        )
    return result
