from dub.engines.asr.base import ASREngine, ASRResult, Segment


class FakeASR(ASREngine):
    def __init__(self, scripted: dict[str, tuple[str, str]] | None = None):
        self.scripted = scripted or {}

    def transcribe(self, audio_path, language=None) -> ASRResult:
        text, lang = self.scripted.get(audio_path, ("", language or "ro"))
        return ASRResult(text, lang, [Segment(text, 0.0, 1.0)] if text else [])

    def detect_language(self, audio_path) -> str:
        return self.scripted.get(audio_path, ("", "ro"))[1]
