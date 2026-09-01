from dataclasses import dataclass
from typing import Protocol


@dataclass
class SpeakerTurn:
    speaker: str
    start: float
    end: float


class DiarizationEngine(Protocol):
    def diarize(self, audio_path: str) -> list[SpeakerTurn]:
        ...
