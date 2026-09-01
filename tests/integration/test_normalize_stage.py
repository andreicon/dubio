import numpy as np

from typer.testing import CliRunner

from dubio.audio.measure import load_wav, measure_loudness, write_wav
from dubio.cli import app
from dubio.config import Config
from dubio.pipeline.normalize import normalize_utterance, normalize_project, process_clip
from dubio.project.manifest import Character, Manifest, Project, SourceSpan, TTSInfo, Utterance, Voice
from dubio.project.paths import ProjectPaths


def test_normalize_writes_processed_and_metadata(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    sr = 48_000
    t = np.arange(sr) / sr
    write_wav(paths.tts_dir / "utt_000001.wav", 0.02 * np.sin(2 * np.pi * 300 * t), sr)

    manifest = Manifest(
        project=Project(id="ep1", source="s", source_language="eng", target_language="ron"),
    )
    manifest.characters["SPEAKER_00"] = Character(name="Bugs", voice="v")
    manifest.voices["v"] = Voice(engine="fake", gain_db=6.0)
    utterance = Utterance(
        id="utt_000001",
        speaker="SPEAKER_00",
        source=SourceSpan(text="x", start=0, end=1),
        tts=TTSInfo(file=str(paths.tts_dir / "utt_000001.wav"), duration=1.0),
    )
    manifest.utterances.append(utterance)

    normalize_utterance(manifest, utterance, paths, Config())

    out = paths.processed_dir / "utt_000001.wav"
    assert out.exists()

    samples, sr = load_wav(out)
    loudness = measure_loudness(samples, sr).integrated_lufs
    assert abs(loudness - (-10.0)) < 2.5
    assert measure_loudness(samples, sr).true_peak_db <= -1.0 + 0.25
    assert "loudness" in utterance.validation.measurements
    assert abs(utterance.validation.measurements["loudness"]["integrated_lufs"] - loudness) < 0.01
    assert abs(utterance.validation.measurements["loudness"]["true_peak_db"] - measure_loudness(samples, sr).true_peak_db) < 0.01


def test_process_clip_applies_default_chain_order():
    sr = 48_000
    samples = np.zeros(sr)
    samples[1000] = 1.0

    processed = process_clip(samples, sr, {"eq_bands": [], "compress": {}}, -16.0, -1.0)

    assert isinstance(processed, np.ndarray)
    assert processed.shape == samples.shape


def test_normalize_project_and_cli_command(tmp_path, monkeypatch):
    paths = ProjectPaths(tmp_path, "ep1")
    sr = 48_000
    t = np.arange(sr) / sr
    write_wav(paths.tts_dir / "utt_000001.wav", 0.02 * np.sin(2 * np.pi * 300 * t), sr)
    write_wav(paths.tts_dir / "utt_000002.wav", 0.02 * np.sin(2 * np.pi * 500 * t), sr)

    manifest = Manifest(
        project=Project(id="ep1", source="s", source_language="eng", target_language="ron"),
        characters={"SPEAKER_00": Character(name="Bugs", voice="v")},
        voices={"v": Voice(engine="fake", gain_db=0.0)},
        utterances=[
            Utterance(id="utt_000001", speaker="SPEAKER_00", source=SourceSpan(text="x", start=0, end=1), tts=TTSInfo(file=str(paths.tts_dir / "utt_000001.wav"))),
            Utterance(id="utt_000002", speaker="SPEAKER_00", source=SourceSpan(text="y", start=1, end=2), tts=TTSInfo(file=str(paths.tts_dir / "utt_000002.wav"))),
        ],
    )
    manifest.save(paths.manifest)

    normalize_project(paths, Config())
    assert (paths.processed_dir / "utt_000001.wav").exists()
    assert (paths.processed_dir / "utt_000002.wav").exists()

    cli_paths = ProjectPaths(tmp_path, "ep2")
    write_wav(cli_paths.tts_dir / "utt_000001.wav", 0.02 * np.sin(2 * np.pi * 300 * t), sr)
    write_wav(cli_paths.tts_dir / "utt_000002.wav", 0.02 * np.sin(2 * np.pi * 500 * t), sr)
    Manifest(
        project=Project(id="ep2", source="s", source_language="eng", target_language="ron"),
        characters={"SPEAKER_00": Character(name="Bugs", voice="v")},
        voices={"v": Voice(engine="fake", gain_db=0.0)},
        utterances=[
            Utterance(id="utt_000001", speaker="SPEAKER_00", source=SourceSpan(text="x", start=0, end=1), tts=TTSInfo(file=str(cli_paths.tts_dir / "utt_000001.wav"))),
            Utterance(id="utt_000002", speaker="SPEAKER_00", source=SourceSpan(text="y", start=1, end=2), tts=TTSInfo(file=str(cli_paths.tts_dir / "utt_000002.wav"))),
        ],
    ).save(cli_paths.manifest)

    from dubio import cli as cli_module

    cli_module.load_config = lambda path=None: Config()

    result = CliRunner().invoke(
        app,
        ["normalize", "ep2", "--projects-root", str(tmp_path), "--utterance", "utt_000001"],
    )

    assert result.exit_code == 0, result.output
    assert (cli_paths.processed_dir / "utt_000001.wav").exists()
    assert not (cli_paths.processed_dir / "utt_000002.wav").exists()
