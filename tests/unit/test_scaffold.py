import dub
from dub.config import load_config
from dub.errors import DubError


def test_version_present():
    assert isinstance(dub.__version__, str) and dub.__version__


def test_duberror_has_stable_id():
    err = DubError("TTS-RO-001", "Language mismatch", {"utt": "utt_1"}, "Run diagnostic")
    assert err.code == "TTS-RO-001"
    assert "utt_1" in str(err)


def test_default_config_loads():
    cfg = load_config(None)
    assert cfg.audio.sample_rate == 48000
    assert cfg.audio.target_lufs == -16
    assert cfg.timing.max_duration_ratio == 1.15
