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


@pytest.mark.gpu
@pytest.mark.model
def test_demucs_separator_collapses_non_vocals_to_music(monkeypatch, tmp_path):
    from dubio.engines.separation.demucs import DemucsSeparator
    import demucs.apply
    import demucs.pretrained

    class StubTensor:
        def __init__(self, values):
            self._values = values

        def cpu(self):
            return self

        def numpy(self):
            return self._values

    class StubModel:
        samplerate = 44100
        sources = ["vocals", "drums", "bass", "other"]

    def fake_apply_model(model, audio_file, device=None):
        return [[
            StubTensor([1.0, 1.0]),
            StubTensor([2.0, 2.0]),
            StubTensor([3.0, 3.0]),
            StubTensor([4.0, 4.0]),
        ]]

    written = {}

    def fake_write_wav(path, samples, sr):
        written[path.name] = (list(samples), sr)

    monkeypatch.setattr(demucs.pretrained, "get_model", lambda name="htdemucs": StubModel())
    monkeypatch.setattr(demucs.apply, "apply_model", fake_apply_model)
    monkeypatch.setattr("dubio.audio.measure.write_wav", fake_write_wav)

    source = tmp_path / "source.wav"
    source.write_bytes(b"stub")

    stems = DemucsSeparator().separate(source, tmp_path)

    assert written["dialogue.wav"] == ([1.0, 1.0], 48000)
    assert written["music.wav"] == ([9.0, 9.0], 48000)
    assert written["sfx.wav"] == ([4.0, 4.0], 48000)
    assert stems.dialogue.exists()
    assert stems.music.exists()
    assert stems.sfx.exists()
