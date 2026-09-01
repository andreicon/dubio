from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Candidate:
    text: str
    estimated_duration: float


@dataclass
class TranslationRequest:
    source_text: str
    source_language: str
    target_language: str
    available_duration: float
    character_context: str = ""
    previous_text: str = ""
    following_text: str = ""


class Translator(Protocol):
    def translate(self, req: "TranslationRequest") -> list["Candidate"]:
        ...
