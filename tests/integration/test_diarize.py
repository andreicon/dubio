import json

from dubio.config import load_config
from dubio.engines.diarization.base import SpeakerTurn
from dubio.engines.diarization.fake import FakeDiarizer
from dubio.pipeline.diarize import assign_speakers
from dubio.pipeline.diarize import diarize
from dubio.project.manifest import SourceSpan, Utterance
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths


def test_assign_by_max_overlap():
    utterances = [
        Utterance(id="utt_000001", speaker="speaker_00", source=SourceSpan(text="hi", start=10.0, end=13.0))
    ]
    turns = [SpeakerTurn("SPEAKER_00", 9.0, 11.0), SpeakerTurn("SPEAKER_01", 11.0, 14.0)]

    assign_speakers(utterances, turns)

    assert utterances[0].speaker == "SPEAKER_01"


def test_diarize_updates_manifest_and_writes_turns(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(
            id="ep1",
            source=str(tmp_path / "clip.mp4"),
            source_language="eng",
            target_language="ron",
        ),
        utterances=[
            Utterance(
                id="utt_000001",
                speaker="speaker_00",
                source=SourceSpan(text="hi", start=10.0, end=13.0),
            )
        ],
    )
    manifest.save(paths.manifest)

    diarize(paths, FakeDiarizer([SpeakerTurn("SPEAKER_01", 11.0, 14.0)]), load_config(None))

    updated = Manifest.load(paths.manifest)
    turns = json.loads((paths.audio_dir / "diarization.json").read_text(encoding="utf-8"))

    assert updated.utterances[0].speaker == "SPEAKER_01"
    assert turns[0]["speaker"] == "SPEAKER_01"
