from __future__ import annotations

from dubio.engines.asr.base import ASREngine, ASRResult, Segment, Word


class WhisperASR(ASREngine):
    def __init__(self, model: str = "large-v3", device: str = "cuda", compute_type: str = "float16"):
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model, device=device, compute_type=compute_type)

    @staticmethod
    def _normalize_language(language: str | None) -> str | None:
        if language == "eng":
            return "en"
        if language == "ron":
            return "ro"
        return language

    def transcribe(self, audio_path, language=None) -> ASRResult:
        segments, info = self._model.transcribe(
            audio_path,
            language=self._normalize_language(language),
            word_timestamps=True,
        )
        output = []
        for segment in segments:
            words = [Word(word.word, word.start, word.end) for word in (segment.words or [])]
            output.append(Segment(segment.text.strip(), segment.start, segment.end, words))
        return ASRResult(" ".join(segment.text for segment in output).strip(), info.language, output)

    def detect_language(self, audio_path) -> str:
        _, info = self._model.transcribe(audio_path, language=None)
        return info.language
