from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Stems:
    dialogue: Path
    music: Path
    sfx: Path


class SourceSeparator(Protocol):
    def separate(self, source_wav: str | Path, out_dir: str | Path) -> Stems:
        ...
