from __future__ import annotations

from dubio.project.manifest import Character, Voice


def map_character(
    manifest,
    speaker_id: str,
    name: str,
    voice: str | None = None,
    reference: str | None = None,
    engine: str | None = None,
    parameters: dict | None = None,
) -> None:
    manifest.characters[speaker_id] = Character(name=name, voice=voice)
    if voice and (reference is not None or engine is not None or parameters is not None):
        existing = manifest.voices.get(voice)
        manifest.voices[voice] = Voice(
            engine=engine or (existing.engine if existing else "fake"),
            reference=reference,
            pitch=(parameters or {}).get("pitch", existing.pitch if existing else 0),
            gain_db=(parameters or {}).get("gain_db", existing.gain_db if existing else 0),
            speaking_rate=(parameters or {}).get("speaking_rate", existing.speaking_rate if existing else 1.0),
        )
