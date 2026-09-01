import shutil
import subprocess
from pathlib import Path

import pytest

from dubio.pipeline.extract import extract_audio, probe


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
def test_probe_and_extract(tmp_path):
    mp4 = tmp_path / "clip.mp4"
    _make_fixture(mp4)

    info = probe(mp4)

    assert abs(info.duration - 2.0) < 0.3
    assert info.fps == 24

    wav = extract_audio(mp4, tmp_path / "source.wav", sr=48000)

    assert wav.exists()
