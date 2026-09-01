from pathlib import Path

from dubio.errors import DubError


def build_tts(name: str, out_dir: Path | None = None, **kw):
    if name == "fake":
        from dubio.engines.tts.fake import FakeTTS

        return FakeTTS(out_dir=out_dir or Path("result"), **kw)
    if name == "fish-s2-pro":
        from dubio.engines.tts.fish_s2 import FishS2TTS

        return FishS2TTS(out_dir=out_dir or Path("result"), **kw)
    raise DubError("ENGINE-001", f"Unknown TTS engine: {name}")


def build_asr(name: str, **kw):
    if name == "fake":
        from dubio.engines.asr.fake import FakeASR

        return FakeASR(**kw)
    if name == "whisper":
        from dubio.engines.asr.whisper import WhisperASR

        return WhisperASR(**kw)
    raise DubError("ENGINE-002", f"Unknown ASR engine: {name}")
