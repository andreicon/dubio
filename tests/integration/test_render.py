import shutil
import json
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


def _probe_streams(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["streams"]


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

    source_streams = _probe_streams(source)
    output_streams = _probe_streams(out)
    source_video = next(stream for stream in source_streams if stream["codec_type"] == "video")
    output_video = next(stream for stream in output_streams if stream["codec_type"] == "video")

    assert output_video["codec_name"] == source_video["codec_name"]
    assert output_video["width"] == source_video["width"]
    assert output_video["height"] == source_video["height"]
    assert output_video["r_frame_rate"] == source_video["r_frame_rate"]
