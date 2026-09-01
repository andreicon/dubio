import pytest

from dubio.engines.asr.base import ASRResult, Segment, Word


pytest.importorskip("faster_whisper")


@pytest.mark.gpu
@pytest.mark.model
def test_whisper_adapter_smoke(monkeypatch):
    from dubio.engines.asr.whisper import WhisperASR
    import faster_whisper

    class StubWhisperModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_path, language=None, word_timestamps=True):
            segment = Segment("What are you doing?", 12.43, 15.87, [Word("What", 12.43, 12.71)])
            return [segment], type("Info", (), {"language": language or "eng"})()

    monkeypatch.setattr(faster_whisper, "WhisperModel", StubWhisperModel)

    asr = WhisperASR()
    result = asr.transcribe("/tmp/sample.wav")

    assert isinstance(result, ASRResult)
    assert result.text
    assert result.segments[0].words[0].word == "What"
