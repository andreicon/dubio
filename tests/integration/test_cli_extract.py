import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dubio.cli import app
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths


def _make_fixture(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=160x120:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-shortest",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_extract_command_writes_media_info(tmp_path):
    source = tmp_path / "clip.mp4"
    _make_fixture(source)

    paths = ProjectPaths(tmp_path, "ep1")
    Manifest(
        project=Project(
            id="ep1",
            source=str(source),
            source_language="eng",
            target_language="ron",
        )
    ).save(paths.manifest)

    result = CliRunner().invoke(
        app,
        ["extract", "ep1", "--projects-root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert (paths.audio_dir / "source.wav").exists()
    assert (paths.audio_dir / "media_info.json").exists()
