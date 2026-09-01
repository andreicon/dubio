from __future__ import annotations

from dubio.project.manifest import Character


def map_character(manifest, speaker_id: str, name: str, voice: str | None = None) -> None:
    manifest.characters[speaker_id] = Character(name=name, voice=voice)
