import pytest


pytest.importorskip("faster_whisper")


@pytest.mark.gpu
@pytest.mark.model
def test_whisper_adapter_smoke():
    from dubio.engines.asr.whisper import WhisperASR

    asr = WhisperASR()
    assert asr is not None
