import pytest


pytest.importorskip("pyannote.audio")


@pytest.mark.gpu
@pytest.mark.model
def test_pyannote_adapter_smoke():
    from dubio.engines.diarization.pyannote import PyannoteDiarizer

    diarizer = PyannoteDiarizer()
    assert diarizer is not None
