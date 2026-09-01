from pathlib import Path

from dub.engines.asr.fake import FakeASR
from dub.engines.tts.base import VoiceProfile
from dub.engines.tts.fake import FakeTTS


def test_fake_tts_duration_scales_with_text(tmp_path):
    tts = FakeTTS(out_dir=tmp_path, chars_per_second=15.0)
    voice = VoiceProfile(id="v", engine="fake", reference=None)
    art = tts.synthesize("Ce faci, băiete?", voice, "ro", {})
    assert Path(art.path).exists()
    assert art.engine_id == "fake"
    assert abs(art.duration - len("Ce faci, băiete?") / 15.0) < 0.1


def test_fake_asr_echoes_and_detects(tmp_path):
    asr = FakeASR(scripted={"a.wav": ("Ce faci?", "ro")})
    res = asr.transcribe("a.wav")
    assert res.text == "Ce faci?" and res.language == "ro"
    assert asr.detect_language("a.wav") == "ro"
