import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dubio.config import load_config
from dubio.engines.asr.base import Word
from dubio.engines.asr.fake import FakeASR
from dubio.engines.diarization.base import SpeakerTurn
from dubio.engines.diarization.fake import FakeDiarizer
from dubio.cli import app
from dubio.pipeline.diarize import diarize
from dubio.pipeline.extract import extract
from dubio.pipeline.transcribe import transcribe
from dubio.pipeline.voices import map_character
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
            "-c:v",
            "libx264",
            "-shortest",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_m1_pipeline_fake_engines(tmp_path):
    source = tmp_path / "episode.mp4"
    _make_fixture(source)
    project_root = tmp_path
    paths = ProjectPaths(project_root, "ep1")

    result = CliRunner().invoke(
        app,
        ["init", "ep1", "--source", str(source), "--projects-root", str(project_root)],
    )
    assert result.exit_code == 0, result.output

    media_info = extract(paths, load_config(None))
    assert media_info.video_codec == "h264"

    scripted_audio = str(paths.audio_dir / "source.wav")
    asr = FakeASR(
        {
            scripted_audio: (
                "What are you doing, băiete?",
                "eng",
                12.43,
                15.87,
                [Word("What", 12.43, 12.71)],
            )
        }
    )
    transcribe(paths, asr, load_config(None))

    diarizer = FakeDiarizer([SpeakerTurn("SPEAKER_00", 12.0, 16.0)])
    diarize(paths, diarizer, load_config(None))

    manifest = Manifest.load(paths.manifest)
    map_character(manifest, "SPEAKER_00", "Bugs")
    manifest.save(paths.manifest)

    manifest = Manifest.load(paths.manifest)
    audio_transcript = json.loads((paths.audio_dir / "transcript.json").read_text(encoding="utf-8"))
    diarization = json.loads((paths.audio_dir / "diarization.json").read_text(encoding="utf-8"))

    assert manifest.utterances
    assert manifest.utterances[0].speaker == "SPEAKER_00"
    assert manifest.characters["SPEAKER_00"].name == "Bugs"
    assert manifest.utterances[0].source.text == "What are you doing, băiete?"
    assert audio_transcript["segments"][0]["text"] == "What are you doing, băiete?"
    assert audio_transcript["segments"][0]["words"][0]["word"] == "What"
    assert diarization[0]["speaker"] == "SPEAKER_00"
