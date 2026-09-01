from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Word:
    word: str
    start: float
    end: float


@dataclass
class Segment:
    text: str
    start: float
    end: float
    words: list[Word] = field(default_factory=list)


@dataclass
class ASRResult:
    text: str
    language: str
    segments: list[Segment] = field(default_factory=list)


class ASREngine(Protocol):
    def transcribe(self, audio_path: str, language: str | None = None) -> ASRResult: ...

    def detect_language(self, audio_path: str) -> str: ...
