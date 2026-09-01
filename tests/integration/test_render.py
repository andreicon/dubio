import shutil
import subprocess

import numpy as np
import pytest

from dubio.audio.measure import write_wav
from dubio.config import Config
from dubio.pipeline.render import render
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths


def _fixture_video(path):
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
def test_render_muxes_final_audio_without_reencoding_video(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    source = tmp_path / "source.mp4"
    _fixture_video(source)

    Manifest(
        project=Project(
            id="ep1",
            source=str(source),
            source_language="eng",
            target_language="ron",
        )
    ).save(paths.manifest)

    write_wav(paths.mix_dir / "final.wav", np.zeros(48000 * 2), 48000)

    out = render(paths, Config())

    assert out.exists()
    assert out.name == "ep1-ro.mp4"
