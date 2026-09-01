from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

from dubio.errors import DubError
from dubio.project.manifest import Manifest


def render(paths, config) -> Path:
    manifest = Manifest.load(paths.manifest)
    out = paths.output_dir / f"{manifest.project.id}-ro.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = None

    with NamedTemporaryFile(delete=False, dir=out.parent, suffix=out.suffix) as handle:
        tmp = Path(handle.name)

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(manifest.project.source),
                "-i",
                str(paths.mix_dir / "final.wav"),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-shortest",
                str(tmp),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise DubError(
                "RENDER-001",
                "video render failed",
                {"stdout": result.stdout, "stderr": result.stderr, "output": str(out)},
            )

        tmp.replace(out)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()

    return out
