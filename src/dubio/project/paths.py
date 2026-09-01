from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    project_id: str

    @property
    def base(self) -> Path:
        return self.root / self.project_id

    @property
    def manifest(self) -> Path:
        return self.base / "manifest.json"

    @property
    def audio_dir(self) -> Path:
        return self.base / "audio"

    @property
    def tts_dir(self) -> Path:
        return self.audio_dir / "tts"

    @property
    def processed_dir(self) -> Path:
        return self.audio_dir / "processed"

    @property
    def mix_dir(self) -> Path:
        return self.base / "mix"

    @property
    def validation_dir(self) -> Path:
        return self.base / "validation"

    @property
    def output_dir(self) -> Path:
        return self.base / "output"
