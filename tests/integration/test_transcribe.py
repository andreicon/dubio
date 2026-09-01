from dubio.engines.asr.base import ASRResult, Segment, Word
from dubio.pipeline.transcribe import transcribe_segments_to_utterances


def test_segments_become_utterances():
    result = ASRResult(
        text="What are you doing?",
        language="eng",
        segments=[
            Segment(
                "What are you doing?",
                12.43,
                15.87,
                [Word("What", 12.43, 12.71)],
            )
        ],
    )

    utterances = transcribe_segments_to_utterances(result)

    assert utterances[0].id == "utt_000001"
    assert utterances[0].source.start == 12.43 and utterances[0].source.end == 15.87
    assert utterances[0].source.words[0]["word"] == "What"
