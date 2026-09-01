import numpy as np
from typer.testing import CliRunner

from dubio.audio.measure import write_wav
from dubio.cli import app
from dubio.config import Config, EngineCfg
from dubio.engines.asr.fake import FakeASR
from dubio.engines.tts.fake import FakeTTS
from dubio.pipeline.regenerate import regenerate_utterance
from dubio.project.manifest import Character, Manifest, Project, SourceSpan, Translation, Utterance, Voice
from dubio.project.paths import ProjectPaths


def test_regenerate_only_target(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")

    other = paths.tts_dir / "utt_000002.wav"
    write_wav(other, np.zeros(1000), 48_000)
    mtime = other.stat().st_mtime_ns

    manifest = Manifest(project=Project(id="ep1", source="s", source_language="eng", target_language="ron"))
    manifest.characters["SPEAKER_00"] = Character(name="Bugs", voice="v")
    manifest.voices["v"] = Voice(engine="fake")
    manifest.utterances.append(
        Utterance(
            id="utt_000001",
            speaker="SPEAKER_00",
            source=SourceSpan(text="x", start=0, end=2),
            translation=Translation(text="Ce faci?", status="approved"),
        )
    )
    write_wav(paths.audio_dir / "music.wav", np.zeros(48_000 * 2), 48_000)
    write_wav(paths.audio_dir / "sfx.wav", np.zeros(48_000 * 2), 48_000)
    manifest.save(paths.manifest)

    engines = {"tts": FakeTTS(out_dir=paths.tts_dir), "asr": FakeASR()}
    regenerate_utterance(paths, "utt_000001", engines, Config())

    assert (paths.tts_dir / "utt_000001.wav").exists()
    assert other.stat().st_mtime_ns == mtime
    assert (paths.mix_dir / "final.wav").exists()


def test_regenerate_cli_supports_single_utterance(tmp_path, monkeypatch):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="s", source_language="eng", target_language="ron"),
        characters={"SPEAKER_00": Character(name="Bugs", voice="v")},
        voices={"v": Voice(engine="fake")},
        utterances=[
            Utterance(
                id="utt_000001",
                speaker="SPEAKER_00",
                source=SourceSpan(text="x", start=0, end=2),
                translation=Translation(text="Ce faci?", status="approved"),
            )
        ],
    )
    write_wav(paths.audio_dir / "music.wav", np.zeros(48_000 * 2), 48_000)
    write_wav(paths.audio_dir / "sfx.wav", np.zeros(48_000 * 2), 48_000)
    manifest.save(paths.manifest)

    from dubio import cli as cli_module

    monkeypatch.setattr(
        cli_module,
        "load_config",
        lambda path=None: Config(tts=EngineCfg(engine="fake"), asr=EngineCfg(engine="fake")),
    )

    result = CliRunner().invoke(
        app,
        ["regenerate", "ep1", "--projects-root", str(tmp_path), "--utterance", "utt_000001"],
    )

    assert result.exit_code == 0, result.output
    assert (paths.tts_dir / "utt_000001.wav").exists()
    assert (paths.mix_dir / "final.wav").exists()
