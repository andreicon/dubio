from dubio.engines.diarization.base import SpeakerTurn
from dubio.pipeline.diarize import assign_speakers
from dubio.project.manifest import SourceSpan, Utterance


def test_assign_by_max_overlap():
    utterances = [
        Utterance(id="utt_000001", speaker="speaker_00", source=SourceSpan(text="hi", start=10.0, end=13.0))
    ]
    turns = [SpeakerTurn("SPEAKER_00", 9.0, 11.0), SpeakerTurn("SPEAKER_01", 11.0, 14.0)]

    assign_speakers(utterances, turns)

    assert utterances[0].speaker == "SPEAKER_01"
