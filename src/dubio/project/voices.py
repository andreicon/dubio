from __future__ import annotations

from pathlib import Path

import yaml

from dubio.engines.tts.base import VoiceProfile
from dubio.errors import DubError


def load_voice_profile(path) -> VoiceProfile:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    parameters = data.get("parameters") or {}

    return VoiceProfile(
        id=data["id"],
        engine=data["engine"],
        reference=data.get("reference"),
        pitch=parameters.get("pitch", 0),
        speaking_rate=parameters.get("speaking_rate", 1.0),
        gain_db=parameters.get("gain_db", 0),
        style=data.get("style") or {},
    )


def resolve_voice(manifest, utterance) -> VoiceProfile:
    character = manifest.characters.get(utterance.speaker)
    if not character or not character.voice:
        raise DubError(
            "VOICE-001",
            f"No voice for speaker {utterance.speaker}",
            {"utt": utterance.id},
            "Assign a character voice via dubio voices",
        )

    voice = manifest.voices.get(character.voice)
    if not voice:
        raise DubError("VOICE-002", f"Voice profile missing: {character.voice}")

    return VoiceProfile(
        id=character.voice,
        engine=voice.engine,
        reference=voice.reference,
        pitch=voice.pitch,
        speaking_rate=voice.speaking_rate,
        gain_db=voice.gain_db,
    )
