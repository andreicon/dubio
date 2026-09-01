import shutil
import subprocess
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dubio.cli import app
from dubio.config import load_config
from dubio.engines.asr.base import Word
from dubio.engines.asr.fake import FakeASR
from dubio.engines.diarization.base import SpeakerTurn
from dubio.engines.diarization.fake import FakeDiarizer
from dubio.engines.separation.fake import FakeSeparator
from dubio.engines.translation.fake import FakeTranslator
from dubio.engines.tts.fake import FakeTTS
from dubio.pipeline.diarize import diarize
from dubio.pipeline.extract import extract
from dubio.pipeline.run import StageSpec, run, stage_complete
from dubio.pipeline.transcribe import transcribe
from dubio.pipeline.voices import map_character
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths


def test_stage_complete_by_artifact(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    spec = StageSpec("extract", lambda p: (p.audio_dir / "source.wav").exists(), lambda paths, config, engines: None)

    assert stage_complete(spec, paths) is False

    paths.audio_dir.mkdir(parents=True)
    (paths.audio_dir / "source.wav").write_bytes(b"x")

    assert stage_complete(spec, paths) is True


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
def test_run_skips_completed_stages_and_forces_resume(tmp_path):
    source = tmp_path / "episode.mp4"
    _make_fixture(source)
    paths = ProjectPaths(tmp_path, "ep1")

    Manifest(
        project=Project(id="ep1", source=str(source), source_language="eng", target_language="ron")
    ).save(paths.manifest)

    media_info = extract(paths, load_config(None))
    assert media_info.video_codec == "h264"

    scripted_audio = str(paths.audio_dir / "source.wav")
    asr = FakeASR({scripted_audio: ("What are you doing, băiete?", "eng", 12.43, 15.87, [Word("What", 12.43, 12.71)])})
    transcribe(paths, asr, load_config(None))

    diarizer = FakeDiarizer([SpeakerTurn("SPEAKER_00", 12.0, 16.0)])
    diarize(paths, diarizer, load_config(None))

    manifest = Manifest.load(paths.manifest)
    map_character(manifest, "SPEAKER_00", "Bugs")
    manifest.save(paths.manifest)

    original_source = (paths.audio_dir / "source.wav").stat().st_mtime_ns
    original_transcript = (paths.audio_dir / "transcript.json").stat().st_mtime_ns
    original_diarization = (paths.audio_dir / "diarization.json").stat().st_mtime_ns

    engines = {
        "separator": FakeSeparator(),
        "asr": asr,
        "diarizer": diarizer,
        "translator": FakeTranslator({"What are you doing, băiete?": ["What are you doing, boy?"]}),
        "tts": FakeTTS(paths.tts_dir),
    }

    run(paths, load_config(None), engines)

    time.sleep(0.01)
    run(paths, load_config(None), engines)

    assert (paths.audio_dir / "source.wav").stat().st_mtime_ns == original_source
    assert (paths.audio_dir / "transcript.json").stat().st_mtime_ns == original_transcript
    assert (paths.audio_dir / "diarization.json").stat().st_mtime_ns == original_diarization

    before_translate = (paths.base / "translation.json").stat().st_mtime_ns
    run(paths, load_config(None), engines, force_from="translate")
    assert (paths.base / "translation.json").stat().st_mtime_ns >= before_translate
    assert (paths.output_dir / "ep1-ro.mp4").exists()


def test_run_command_is_registered():
    result = CliRunner().invoke(app, ["run", "--help"])
    assert result.exit_code == 0, result.output
    assert "--force-from" in result.output
