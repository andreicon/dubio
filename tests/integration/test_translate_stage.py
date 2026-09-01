import json

from typer.testing import CliRunner

from dubio.cli import app
from dubio.config import Config, EngineCfg, load_config
from dubio.engines.translation.base import Candidate
from dubio.engines.translation.fake import FakeTranslator
from dubio.pipeline.translate import select_candidate, translate_project
from dubio.project.manifest import Manifest, Project, SourceSpan, Utterance
from dubio.project.paths import ProjectPaths


def test_select_candidate_prefers_best_fit_under_tolerance():
    cands = [
        Candidate("Ce faci?", 1.72),
        Candidate("Ce naiba faci?", 2.31),
        Candidate("Ce naiba faci acolo?", 2.94),
    ]
    chosen = select_candidate(cands, target=2.85, max_ratio=1.15)
    assert chosen.text == "Ce naiba faci acolo?"


def test_select_candidate_falls_back_to_shortest_when_all_too_long():
    cands = [Candidate("foarte lung text aici", 5.0), Candidate("lung", 4.0)]
    chosen = select_candidate(cands, target=2.0, max_ratio=1.15)
    assert chosen.text == "lung"


def test_translate_stage_persists_candidates_and_status(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
        utterances=[
            Utterance(id="utt_1", speaker="SPEAKER_00", source=SourceSpan(text="What are you doing?", start=0.0, end=2.0)),
            Utterance(id="utt_2", speaker="SPEAKER_00", source=SourceSpan(text="What are you doing, băiete?", start=2.0, end=4.0)),
        ],
    )
    manifest.save(paths.manifest)

    translator = FakeTranslator(
        {
            "What are you doing?": ["Ce faci?", "Ce naiba faci acolo?"],
            "What are you doing, băiete?": ["Ce faci, băiete?", "Ce naiba faci, băiete?"],
        }
    )
    config = load_config(None)
    translate_project(paths, translator, config)

    updated = Manifest.load(paths.manifest)
    data = json.loads((paths.base / "translation.json").read_text(encoding="utf-8"))
    assert updated.utterances[0].translation.status == "translated"
    assert updated.utterances[0].translation.text == "Ce naiba faci acolo?"
    assert updated.utterances[1].translation.text == "Ce naiba faci, băiete?"
    assert updated.utterances[1].translation.candidates[0]["text"].endswith("băiete?")
    assert data[1]["chosen"] == "Ce naiba faci, băiete?"


def test_translate_cli_edit_and_approve(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
        utterances=[Utterance(id="utt_1", speaker="SPEAKER_00", source=SourceSpan(text="Ce faci?", start=0.0, end=1.0))],
    ).save(paths.manifest)

    runner = CliRunner()
    result = runner.invoke(app, ["translate", "ep1", "--projects-root", str(tmp_path), "--utterance", "utt_1", "--set", "Ce faci, băiete?"])
    assert result.exit_code == 0, result.output
    manifest = Manifest.load(paths.manifest)
    assert manifest.get_utterance("utt_1").translation.text == "Ce faci, băiete?"
    assert manifest.get_utterance("utt_1").translation.status == "edited"

    result = runner.invoke(app, ["translate", "ep1", "--projects-root", str(tmp_path), "--utterance", "utt_1", "--approve"])
    assert result.exit_code == 0, result.output
    manifest = Manifest.load(paths.manifest)
    assert manifest.get_utterance("utt_1").translation.status == "approved"


def test_translate_cli_batch_uses_stage(tmp_path, monkeypatch):
    paths = ProjectPaths(tmp_path, "ep1")
    Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
        utterances=[
            Utterance(id="utt_1", speaker="SPEAKER_00", source=SourceSpan(text="What are you doing?", start=0.0, end=2.0)),
        ],
    ).save(paths.manifest)

    monkeypatch.setattr("dubio.cli.load_config", lambda path=None: Config(translation=EngineCfg(engine="fake")))
    monkeypatch.setattr(
        "dubio.cli._build_translator",
        lambda config, paths: FakeTranslator({"What are you doing?": ["Ce faci?", "Ce naiba faci acolo?"]}),
    )

    result = CliRunner().invoke(app, ["translate", "ep1", "--projects-root", str(tmp_path)])
    assert result.exit_code == 0, result.output

    manifest = Manifest.load(paths.manifest)
    assert manifest.get_utterance("utt_1").translation.status == "translated"
    assert manifest.get_utterance("utt_1").translation.text == "Ce naiba faci acolo?"
