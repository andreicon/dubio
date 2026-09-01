import json
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import pytest

from dubio.audio.measure import load_wav, write_wav
from dubio.config import Config
from dubio.engines.asr.base import ASRResult, Segment, Word
from dubio.engines.asr.fake import FakeASR
from dubio.engines.diarization.base import SpeakerTurn
from dubio.engines.diarization.fake import FakeDiarizer
from dubio.engines.separation.fake import FakeSeparator
from dubio.engines.translation.fake import FakeTranslator
from dubio.engines.tts.fake import FakeTTS
from dubio.pipeline.diarize import diarize
from dubio.pipeline.extract import extract
from dubio.pipeline.mix import mix_project
from dubio.pipeline.regenerate import regenerate_utterance
from dubio.pipeline.render import render
from dubio.pipeline.run import run
from dubio.pipeline.separate import separate
from dubio.pipeline.transcribe import transcribe
from dubio.pipeline.translate import translate_project
from dubio.pipeline.validate import validate_project
from dubio.project.manifest import Character, Manifest, Project, Voice
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


def _fixture_manifest(source: Path, voices: bool = True) -> Manifest:
    manifest = Manifest(
        project=Project(id="ep1", source=str(source), source_language="eng", target_language="ron"),
        characters={
            "SPEAKER_00": Character(name="Bugs", voice="bugs_ro" if voices else None),
            "SPEAKER_01": Character(name="Daffy", voice="daffy_ro" if voices else None),
        },
    )
    if voices:
        manifest.voices["bugs_ro"] = Voice(engine="fake")
        manifest.voices["daffy_ro"] = Voice(engine="fake")
    return manifest


class ScriptedASR(FakeASR):
    def transcribe(self, audio_path: str, language=None) -> ASRResult:
        return ASRResult(
            "What are you doing, băiete? Bună dimineața!",
            language or "eng",
            [
                Segment(
                    "What are you doing, băiete?",
                    0.10,
                    1.10,
                    [Word("What", 0.10, 0.20), Word("are", 0.22, 0.30), Word("băiete", 0.70, 0.90)],
                ),
                Segment(
                    "Bună dimineața!",
                    1.06,
                    1.80,
                    [Word("Bună", 1.05, 1.20), Word("dimineața", 1.25, 1.60)],
                ),
            ],
        )


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="ffmpeg and ffprobe required")
def test_mvp_acceptance_end_to_end(tmp_path, caplog, capsys):
    source = tmp_path / "episode.mp4"
    _make_fixture(source)
    paths = ProjectPaths(tmp_path, "ep1")
    _fixture_manifest(source).save(paths.manifest)

    config = Config()
    source_wav = paths.audio_dir / "source.wav"
    asr = ScriptedASR()
    diarizer = FakeDiarizer([SpeakerTurn("SPEAKER_00", 0.0, 1.0), SpeakerTurn("SPEAKER_01", 1.0, 2.0)])
    translator = FakeTranslator(
        {
            "What are you doing, băiete?": ["Ce faci, băiete?"],
            "Bună dimineața!": ["Bună dimineața!"],
        }
    )
    tts = FakeTTS(paths.tts_dir, chars_per_second=10.0)
    engines = {"separator": FakeSeparator(), "asr": asr, "diarizer": diarizer, "translator": translator, "tts": tts}

    extract(paths, config)
    assert source_wav.exists()

    separate(paths, engines["separator"], config)
    transcribe(paths, asr, config)
    diarize(paths, diarizer, config)
    translate_project(paths, translator, config)

    manifest = Manifest.load(paths.manifest)
    assert len(manifest.utterances) == 2
    assert [utt.speaker for utt in manifest.utterances] == ["SPEAKER_00", "SPEAKER_01"]
    assert [utt.translation.text for utt in manifest.utterances] == ["Ce faci, băiete?", "Bună dimineața!"]
    assert "băiete" in manifest.utterances[0].source.text
    assert manifest.utterances[0].translation.status == "translated"
    assert manifest.utterances[0].translation.candidates[0]["text"] == "Ce faci, băiete?"

    manifest.characters["SPEAKER_00"].voice = "bugs_ro"
    manifest.characters["SPEAKER_01"].voice = "daffy_ro"
    manifest.save(paths.manifest)

    run(paths, config, engines)

    manifest = Manifest.load(paths.manifest)
    assert (paths.audio_dir / "source.wav").exists()
    assert (paths.validation_dir / "report.json").exists()
    assert (paths.audio_dir / "tts").exists()
    assert (paths.audio_dir / "processed").exists()
    assert (paths.audio_dir / "music.wav").exists()
    assert (paths.audio_dir / "sfx.wav").exists()
    assert (paths.mix_dir / "dialogue.wav").exists()
    assert (paths.mix_dir / "final.wav").exists()
    assert (paths.output_dir / "ep1-ro.mp4").exists()

    report = json.loads((paths.validation_dir / "report.json").read_text(encoding="utf-8"))
    assert report["project"] == "ep1"
    assert len(report["utterances"]) == 2
    assert len(report["overlaps"]) == 1
    assert report["overlaps"][0]["seconds"] > 0.0

    first = manifest.get_utterance("utt_000001")
    second = manifest.get_utterance("utt_000002")
    assert first.tts.file and Path(first.tts.file).exists()
    assert second.tts.file and Path(second.tts.file).exists()
    assert first.tts.duration is not None
    assert second.tts.duration is not None
    assert first.validation.language == "pass"
    assert first.validation.measurements["loudness"]["integrated_lufs"] == pytest.approx(-16.0, abs=2.0)
    assert first.validation.measurements["loudness"]["true_peak_db"] <= 0.0
    assert first.validation.overlap in ("warning", "fail")

    final_samples, final_sr = load_wav(paths.mix_dir / "final.wav")
    source_samples, source_sr = load_wav(source_wav)
    assert final_sr == source_sr
    assert len(final_samples) == len(source_samples)
    assert (paths.audio_dir / "music.wav").exists()
    assert (paths.audio_dir / "sfx.wav").exists()

    first_tts = paths.tts_dir / "utt_000001.wav"
    second_tts = paths.tts_dir / "utt_000002.wav"
    first_processed = paths.processed_dir / "utt_000001.wav"
    second_processed = paths.processed_dir / "utt_000002.wav"
    before = {path: path.stat().st_mtime_ns for path in [first_tts, second_tts, first_processed, second_processed]}
    regenerate_utterance(paths, "utt_000001", engines, config)
    after = {path: path.stat().st_mtime_ns for path in [first_tts, second_tts, first_processed, second_processed]}
    assert after[first_tts] > before[first_tts]
    assert after[first_processed] > before[first_processed]
    assert after[second_tts] == before[second_tts]
    assert after[second_processed] == before[second_processed]

    manifest_before = {path: path.stat().st_mtime_ns for path in [paths.audio_dir / "source.wav", paths.audio_dir / "transcript.json", paths.audio_dir / "diarization.json", paths.base / "translation.json", paths.validation_dir / "report.json", paths.mix_dir / "final.wav", paths.output_dir / "ep1-ro.mp4"]}
    time.sleep(0.01)
    with caplog.at_level("INFO"):
        run(paths, config, engines)
    manifest_after = {path: path.stat().st_mtime_ns for path in [paths.audio_dir / "source.wav", paths.audio_dir / "transcript.json", paths.audio_dir / "diarization.json", paths.base / "translation.json", paths.validation_dir / "report.json", paths.mix_dir / "final.wav", paths.output_dir / "ep1-ro.mp4"]}
    assert manifest_after == manifest_before
    skipped_output = capsys.readouterr().out
    assert "stage_skipped" in skipped_output

    failing_paths = ProjectPaths(tmp_path, "failcase")
    Manifest(
        project=Project(id="failcase", source=str(source), source_language="eng", target_language="ron"),
        characters={
            "SPEAKER_00": Character(name="Bugs"),
            "SPEAKER_01": Character(name="Daffy"),
        },
        utterances=[utt.model_copy(deep=True) for utt in manifest.utterances],
    ).save(failing_paths.manifest)
    failing_paths.audio_dir.mkdir(parents=True, exist_ok=True)
    write_wav(failing_paths.audio_dir / "source.wav", np.zeros(48_000), 48_000)
    write_wav(failing_paths.audio_dir / "music.wav", np.zeros(48_000), 48_000)
    write_wav(failing_paths.audio_dir / "sfx.wav", np.zeros(48_000), 48_000)
    (failing_paths.audio_dir / "transcript.json").write_text("{}", encoding="utf-8")
    (failing_paths.audio_dir / "diarization.json").write_text("[]", encoding="utf-8")
    (failing_paths.base / "translation.json").parent.mkdir(parents=True, exist_ok=True)
    (failing_paths.base / "translation.json").write_text("[]", encoding="utf-8")
    with caplog.at_level("INFO"):
        with pytest.raises(Exception) as excinfo:
            run(failing_paths, config, engines)
    failed_output = capsys.readouterr().out
    assert getattr(excinfo.value, "code", None) == "RUN-001"
    assert "stage_failed" in failed_output
    assert "synthesize" in failed_output
