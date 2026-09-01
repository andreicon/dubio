import pytest

from dubio.engines.diarization.base import SpeakerTurn


pytest.importorskip("pyannote.audio")


@pytest.mark.gpu
@pytest.mark.model
def test_pyannote_adapter_smoke(monkeypatch):
    from dubio.engines.diarization.pyannote import PyannoteDiarizer
    import pyannote.audio

    class StubSegment:
        def __init__(self, start, end):
            self.start = start
            self.end = end

    class StubAnnotation:
        def itertracks(self, yield_label=True):
            yield StubSegment(0.0, 1.0), None, "SPEAKER_00"

    class StubPipeline:
        def __call__(self, audio_path):
            return StubAnnotation()

    monkeypatch.setattr(pyannote.audio.Pipeline, "from_pretrained", lambda *args, **kwargs: StubPipeline())

    diarizer = PyannoteDiarizer()
    turns = diarizer.diarize("/tmp/sample.wav")

    assert turns
    assert turns[0].speaker == "SPEAKER_00"
