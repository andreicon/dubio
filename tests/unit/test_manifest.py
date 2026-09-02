from pathlib import Path

from dubio.project.manifest import Manifest, SourceSpan, Utterance
from dubio.project.paths import ProjectPaths


def test_manifest_roundtrip_preserves_diacritics(tmp_path):
    manifest = Manifest(
        project={
            "id": "ep1",
            "source": "s.mp4",
            "source_language": "eng",
            "target_language": "ron",
        }
    )
    manifest.utterances.append(
        Utterance(
            id="utt_000001",
            speaker="speaker_00",
            source=SourceSpan(text="What are you doing?", start=12.43, end=15.87),
        )
    )
    manifest.utterances[0].translation.text = "Ce faci, băiete?"

    path = tmp_path / "manifest.json"
    manifest.save(path)

    loaded = Manifest.load(path)

    assert loaded.utterances[0].translation.text == "Ce faci, băiete?"
    assert loaded.get_utterance("utt_000001").source.duration == 3.44


def test_utterance_reference_audio_round_trips(tmp_path):
    manifest = Manifest(
        project={
            "id": "ep1",
            "source": "s.mp4",
            "source_language": "eng",
            "target_language": "ron",
        }
    )
    manifest.utterances.append(
        Utterance(
            id="utt_000001",
            speaker="speaker_00",
            source=SourceSpan(text="What are you doing?", start=12.43, end=15.87),
            reference_audio="audio/reference/utt_000001.wav",
        )
    )

    path = tmp_path / "manifest.json"
    manifest.save(path)

    loaded = Manifest.load(path)

    assert loaded.utterances[0].reference_audio == "audio/reference/utt_000001.wav"


def test_project_paths_match_brief(tmp_path):
    paths = ProjectPaths(tmp_path, "episode-001")

    assert paths.manifest == tmp_path / "episode-001" / "manifest.json"
    assert paths.audio_dir == tmp_path / "episode-001" / "audio"
    assert paths.tts_dir == tmp_path / "episode-001" / "audio" / "tts"
    assert paths.processed_dir == tmp_path / "episode-001" / "audio" / "processed"
    assert paths.mix_dir == tmp_path / "episode-001" / "mix"
    assert paths.validation_dir == tmp_path / "episode-001" / "validation"
    assert paths.output_dir == tmp_path / "episode-001" / "output"
