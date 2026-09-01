from dubio.engines.asr.base import ASREngine, ASRResult, Segment


class FakeASR(ASREngine):
    def __init__(self, scripted: dict[str, tuple] | None = None):
        self.scripted = scripted or {}

    def transcribe(self, audio_path, language=None) -> ASRResult:
        scripted = self.scripted.get(audio_path)
        if scripted is None:
            return ASRResult("", language or "ro", [])

        text, lang = scripted[0], scripted[1]
        start = scripted[2] if len(scripted) > 2 else 0.0
        end = scripted[3] if len(scripted) > 3 else 1.0
        words = scripted[4] if len(scripted) > 4 else []
        return ASRResult(text, lang, [Segment(text, start, end, words)] if text else [])

    def detect_language(self, audio_path) -> str:
        scripted = self.scripted.get(audio_path)
        return scripted[1] if scripted is not None else "ro"
