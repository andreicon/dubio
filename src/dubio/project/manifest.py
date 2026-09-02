from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, computed_field

from dubio.errors import DubError


class Project(BaseModel):
    id: str
    source: str
    source_language: str
    target_language: str


class Character(BaseModel):
    name: str
    voice: str | None = None


class Voice(BaseModel):
    engine: str
    reference: str | None = None
    pitch: float = 0
    gain_db: float = 0
    speaking_rate: float = 1.0


class SourceSpan(BaseModel):
    text: str
    start: float
    end: float
    words: list[dict] = Field(default_factory=list)

    @computed_field
    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)


class Translation(BaseModel):
    text: str = ""
    status: str = "pending"
    candidates: list[dict] = Field(default_factory=list)


class TTSInfo(BaseModel):
    engine: str | None = None
    voice: str | None = None
    file: str | None = None
    duration: float | None = None
    engine_version: str | None = None


class MixInfo(BaseModel):
    gain_db: float = 0
    pan: float = 0


class Validation(BaseModel):
    language: str | None = None
    transcription: str | None = None
    duration: str | None = None
    loudness: str | None = None
    overlap: str | None = None
    score: float | None = None
    measurements: dict = Field(default_factory=dict)


class Utterance(BaseModel):
    id: str
    speaker: str
    source: SourceSpan
    reference_audio: str | None = None
    translation: Translation = Field(default_factory=Translation)
    tts: TTSInfo = Field(default_factory=TTSInfo)
    mix: MixInfo = Field(default_factory=MixInfo)
    validation: Validation = Field(default_factory=Validation)
    overlap_allowed: bool = False


class Manifest(BaseModel):
    project: Project
    characters: dict[str, Character] = Field(default_factory=dict)
    voices: dict[str, Voice] = Field(default_factory=dict)
    utterances: list[Utterance] = Field(default_factory=list)

    @classmethod
    def load(cls, path) -> "Manifest":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def save(self, path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_utterance(self, uid: str) -> Utterance:
        for utterance in self.utterances:
            if utterance.id == uid:
                return utterance
        raise DubError("MANIFEST-001", f"Utterance not found: {uid}")
