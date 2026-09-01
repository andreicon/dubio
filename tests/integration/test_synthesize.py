from typer.testing import CliRunner
from types import SimpleNamespace
import pytest

from dubio.cli import app
from dubio.config import Config, EngineCfg
from dubio.engines.tts.fake import FakeTTS
from dubio.audio.measure import write_wav
from dubio.pipeline.synthesize import synthesize_utterance
from dubio.pipeline.synthesize import synthesize_project
from dubio.project.manifest import Character, Manifest, Project, SourceSpan, Translation, Utterance, Voice
from dubio.project.paths import ProjectPaths
from dubio.utils.cache import Cache
from dubio.utils.cache import tts_cache_key


def test_synthesize_utterance_sets_tts_fields_and_writes_audio(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
    )
    manifest.characters["SPEAKER_00"] = Character(name="Bugs", voice="voice_bugs")
    manifest.voices["voice_bugs"] = Voice(engine="fake", reference=None)
    utterance = Utterance(
        id="utt_000001",
        speaker="SPEAKER_00",
        source=SourceSpan(text="What?", start=0.0, end=1.0),
        translation=Translation(text="Ce faci?", status="approved"),
    )
    manifest.utterances.append(utterance)

    tts = FakeTTS(out_dir=paths.tts_dir)
    synthesize_utterance(manifest, utterance, tts, Cache(paths.tts_dir / "_cache"), paths)

    assert utterance.tts.engine == "fake"
    assert utterance.tts.voice == "voice_bugs"
    assert utterance.tts.engine_version == "0"
    assert utterance.tts.duration is not None and utterance.tts.duration > 0
    assert utterance.tts.file is not None
    assert (paths.tts_dir / "utt_000001.wav").exists()


def test_synthesize_cli_regenerates_one_utterance_and_persists_manifest(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
        characters={"SPEAKER_00": Character(name="Bugs", voice="voice_bugs")},
        voices={"voice_bugs": Voice(engine="fake", reference=None)},
        utterances=[
            Utterance(
                id="utt_000001",
                speaker="SPEAKER_00",
                source=SourceSpan(text="What?", start=0.0, end=1.0),
                translation=Translation(text="Ce faci?", status="approved"),
            ),
            Utterance(
                id="utt_000002",
                speaker="SPEAKER_00",
                source=SourceSpan(text="Again?", start=1.0, end=2.0),
                translation=Translation(text="Încă o dată?", status="approved"),
            ),
        ],
    )
    manifest.save(paths.manifest)

    from dubio import cli as cli_module

    cli_module.load_config = lambda path=None: Config(tts=EngineCfg(engine="fake"))

    result = CliRunner().invoke(
        app,
        ["synthesize", "ep1", "--projects-root", str(tmp_path), "--utterance", "utt_000001"],
    )

    assert result.exit_code == 0, result.output
    updated = Manifest.load(paths.manifest)
    assert updated.get_utterance("utt_000001").tts.file is not None
    assert updated.get_utterance("utt_000002").tts.file is None
    assert (paths.tts_dir / "utt_000001.wav").exists()
    assert not (paths.tts_dir / "utt_000002.wav").exists()


def test_synthesize_project_continues_after_failure_and_persists_success(tmp_path, monkeypatch):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="spa"),
        characters={"SPEAKER_00": Character(name="Bugs", voice="voice_bugs")},
        voices={"voice_bugs": Voice(engine="fake", reference=None)},
        utterances=[
            Utterance(
                id="utt_000001",
                speaker="SPEAKER_00",
                source=SourceSpan(text="One", start=0.0, end=1.0),
                translation=Translation(text="Uno", status="approved"),
            ),
            Utterance(
                id="utt_000002",
                speaker="SPEAKER_00",
                source=SourceSpan(text="Two", start=1.0, end=2.0),
                translation=Translation(text="Dos", status="approved"),
            ),
        ],
    )
    manifest.save(paths.manifest)

    calls = []

    def fake_synthesize_utterance(manifest, utterance, tts, cache, paths, force=False):
        calls.append(utterance.id)
        if utterance.id == "utt_000001":
            raise RuntimeError("boom")
        utterance.tts.file = str(paths.tts_dir / f"{utterance.id}.wav")
        utterance.tts.engine = "fake"
        utterance.tts.voice = "voice_bugs"
        utterance.tts.engine_version = "0"
        utterance.tts.duration = 0.5
        paths.tts_dir.mkdir(parents=True, exist_ok=True)
        write_wav(paths.tts_dir / f"{utterance.id}.wav", __import__("numpy").zeros(24000), 48000)

    monkeypatch.setattr("dubio.pipeline.synthesize.synthesize_utterance", fake_synthesize_utterance)

    with pytest.raises(RuntimeError, match=r"TTS synthesis failed for 1 utterance\(s\)"):
        synthesize_project(paths, FakeTTS(out_dir=paths.tts_dir), Config(hardware={"max_tts_workers": 2}), force=False)

    updated = Manifest.load(paths.manifest)
    assert set(calls) == {"utt_000001", "utt_000002"}
    assert updated.get_utterance("utt_000001").tts.file is None
    assert updated.get_utterance("utt_000002").tts.file is not None


def test_synthesize_utterance_uses_manifest_target_language(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="spa"),
        characters={"SPEAKER_00": Character(name="Bugs", voice="voice_bugs")},
        voices={"voice_bugs": Voice(engine="fake", reference=None)},
        utterances=[
            Utterance(
                id="utt_000001",
                speaker="SPEAKER_00",
                source=SourceSpan(text="What?", start=0.0, end=1.0),
                translation=Translation(text="Ce faci?", status="approved"),
            ),
        ],
    )
    utterance = manifest.utterances[0]

    observed = {}

    class RecordingTTS:
        engine_id = "fake"
        engine_version = "0"

        def synthesize(self, text, voice, language, instructions):
            observed["language"] = language
            out = paths.tts_dir / "recording.wav"
            paths.tts_dir.mkdir(parents=True, exist_ok=True)
            write_wav(out, __import__("numpy").zeros(24000), 48000)
            return SimpleNamespace(path=str(out), duration=0.5, engine_id=self.engine_id, engine_version=self.engine_version)

    synthesize_utterance(manifest, utterance, RecordingTTS(), Cache(paths.tts_dir / "_cache"), paths)

    assert observed["language"] == "spa"


def test_tts_cache_key_changes_when_voice_reference_changes():
    base = tts_cache_key(
        "fake",
        "0",
        "voice_bugs",
        "ron",
        "Ce faci?",
        {},
        {"pitch": 0, "speaking_rate": 1.0, "gain_db": 0},
    )
    changed = tts_cache_key(
        "fake",
        "0",
        "voice_bugs",
        "ron",
        "Ce faci?",
        {},
        {"pitch": 0, "speaking_rate": 1.0, "gain_db": 0, "reference": "voices/better.wav"},
    )

    assert base != changed


def test_synthesize_cli_passes_config_into_tts_builder(tmp_path, monkeypatch):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
        characters={"SPEAKER_00": Character(name="Bugs", voice="voice_bugs")},
        voices={"voice_bugs": Voice(engine="fake", reference=None)},
        utterances=[
            Utterance(
                id="utt_000001",
                speaker="SPEAKER_00",
                source=SourceSpan(text="What?", start=0.0, end=1.0),
                translation=Translation(text="Ce faci?", status="approved"),
            )
        ],
    )
    manifest.save(paths.manifest)

    from dubio import cli as cli_module

    cli_module.load_config = lambda path=None: Config(tts=EngineCfg(engine="fake", model="custom-model"), hardware={"device": "cpu", "max_tts_workers": 1})

    observed = {}

    def fake_build_tts(name, out_dir=None, **kw):
        observed["name"] = name
        observed["out_dir"] = out_dir
        observed["kw"] = kw
        return FakeTTS(out_dir=out_dir)

    monkeypatch.setattr(cli_module, "build_tts", fake_build_tts)

    result = CliRunner().invoke(
        app,
        ["synthesize", "ep1", "--projects-root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert observed["name"] == "fake"
    assert observed["kw"] == {"model_version": "custom-model"}


def test_synthesize_cli_exits_non_zero_on_partial_failure(tmp_path, monkeypatch):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
        characters={"SPEAKER_00": Character(name="Bugs", voice="voice_bugs")},
        voices={"voice_bugs": Voice(engine="fake", reference=None)},
        utterances=[
            Utterance(
                id="utt_000001",
                speaker="SPEAKER_00",
                source=SourceSpan(text="What?", start=0.0, end=1.0),
                translation=Translation(text="Ce faci?", status="approved"),
            )
        ],
    )
    manifest.save(paths.manifest)

    from dubio import cli as cli_module

    cli_module.load_config = lambda path=None: Config(tts=EngineCfg(engine="fake"), hardware={"device": "cpu", "max_tts_workers": 1})
    monkeypatch.setattr(cli_module, "build_tts", lambda name, out_dir=None, **kw: FakeTTS(out_dir=out_dir))

    def fail_once(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli_module, "synthesize_project", fail_once)

    result = CliRunner().invoke(
        app,
        ["synthesize", "ep1", "--projects-root", str(tmp_path)],
    )

    assert result.exit_code != 0
