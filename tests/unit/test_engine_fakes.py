from pathlib import Path

import pytest

from dubio.engines.asr.fake import FakeASR
from dubio.engines.tts.base import VoiceProfile
from dubio.engines.tts.delusion import DelusionTTS
from dubio.engines.tts.fake import FakeTTS
from dubio.errors import DubError


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


def test_delusion_requires_audiocpp_cli(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda name: None)
    tts = DelusionTTS(out_dir=tmp_path)
    voice = VoiceProfile(id="v", engine="delusion")

    with pytest.raises(DubError) as excinfo:
        tts.synthesize("Ce faci?", voice, "ro", {})

    assert excinfo.value.code == "ENGINE-005"


def test_delusion_accepts_audiocpp_path(monkeypatch, tmp_path):
    cli = tmp_path / "audiocpp_cli"
    cli.write_text("#!/usr/bin/env bash\nexit 0\n")
    cli.chmod(0o755)
    monkeypatch.setenv("AUDIOCPP_PATH", str(cli))
    monkeypatch.setattr("shutil.which", lambda name: None)

    tts = DelusionTTS(out_dir=tmp_path)

    assert tts._ensure_cli() is None
