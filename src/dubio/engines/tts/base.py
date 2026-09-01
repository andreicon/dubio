from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class VoiceProfile:
    id: str
    engine: str
    reference: str | None = None
    pitch: float = 0.0
    speaking_rate: float = 1.0
    gain_db: float = 0.0
    style: dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioArtifact:
    path: str
    sample_rate: int
    duration: float
    engine_id: str
    engine_version: str
    metadata: dict[str, Any] = field(default_factory=dict)


class TTSEngine(Protocol):
    engine_id: str
    engine_version: str

    def synthesize(
        self,
        text: str,
        voice: VoiceProfile,
        language: str,
        instructions: dict,
    ) -> AudioArtifact: ...
