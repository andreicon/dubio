import json

from typer.testing import CliRunner

from dubio.cli import app
from dubio.config import Config, EngineCfg, load_config
from dubio.engines.asr.fake import FakeASR
from dubio.pipeline.validate import validate_project
from dubio.project.manifest import Manifest, Project, SourceSpan, TTSInfo, Translation, Utterance, Validation
from dubio.project.paths import ProjectPaths


def _manifest_with_two_utterances():
    return Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
        utterances=[
            Utterance(
                id="utt_1",
                speaker="SPEAKER_00",
                source=SourceSpan(text="What are you doing?", start=0.0, end=2.0),
                translation=Translation(text="Ce faci?"),
                tts=TTSInfo(file="audio/utt_1.wav", duration=1.9),
                validation=Validation(measurements={"loudness": {"integrated_lufs": -15.9, "true_peak_db": -1.2}}),
            ),
            Utterance(
                id="utt_2",
                speaker="SPEAKER_00",
                source=SourceSpan(text="What are you doing there?", start=1.5, end=4.0),
                translation=Translation(text="Ce faci acolo?"),
                tts=TTSInfo(file="audio/utt_2.wav", duration=2.4),
                validation=Validation(measurements={"loudness": {"integrated_lufs": -18.1, "true_peak_db": -0.5}}),
            ),
        ],
    )


def test_validate_stage_writes_report_and_updates_manifest(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = _manifest_with_two_utterances()
    manifest.save(paths.manifest)

    asr = FakeASR(
        {
            "audio/utt_1.wav": ("Ce faci?", "ro"),
            "audio/utt_2.wav": ("Ce faci acolo?", "ro"),
        }
    )
    config = load_config(None)

    report = validate_project(paths, asr, config)

    report_path = paths.validation_dir / "report.json"
    assert report_path.exists()
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    updated = Manifest.load(paths.manifest)

    assert report["project"] == "ep1"
    assert saved["utterances"][0]["score"] is not None
    assert saved["utterances"][0]["checks"]["text"] >= 0.0
    assert updated.get_utterance("utt_1").validation.score is not None
    assert updated.get_utterance("utt_1").validation.measurements["checks"]["text"]["similarity"] >= 0.0
    assert updated.get_utterance("utt_1").validation.overlap in ("warning", "fail")


def test_validate_cli_supports_single_utterance(tmp_path, monkeypatch):
    paths = ProjectPaths(tmp_path, "ep1")
    _manifest_with_two_utterances().save(paths.manifest)

    monkeypatch.setattr("dubio.cli.load_config", lambda path=None: Config(asr=EngineCfg(engine="fake")))

    result = CliRunner().invoke(app, ["validate", "ep1", "--projects-root", str(tmp_path), "--utterance", "utt_1"])
    assert result.exit_code == 0, result.output
