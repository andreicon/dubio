import pytest


pytest.importorskip("demucs")


@pytest.mark.gpu
@pytest.mark.model
def test_demucs_separator_smoke(monkeypatch, tmp_path):
    from dubio.engines.separation.demucs import DemucsSeparator
    import demucs.apply
    import demucs.pretrained

    class StubTensor:
        def cpu(self):
            return self

        def numpy(self):
            return [0.0]

    class StubModel:
        samplerate = 48000

    def fake_apply_model(model, audio_file, device=None):
        return [[StubTensor(), StubTensor(), StubTensor()]]

    monkeypatch.setattr(demucs.pretrained, "get_model", lambda name="htdemucs": StubModel())
    monkeypatch.setattr(demucs.apply, "apply_model", fake_apply_model)

    source = tmp_path / "source.wav"
    source.write_bytes(b"stub")

    stems = DemucsSeparator().separate(source, tmp_path)

    assert stems.dialogue.exists()
    assert stems.music.exists()
    assert stems.sfx.exists()
