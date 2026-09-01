from __future__ import annotations

from pathlib import Path

from dubio.utils.hashing import stable_hash


def tts_cache_key(
    engine_id,
    engine_version,
    voice_id,
    language,
    text,
    instructions,
    params,
) -> str:
    return stable_hash(engine_id, engine_version, voice_id, language, text, instructions, params)


class Cache:
    def __init__(self, directory) -> None:
        self.dir = Path(directory)

    def path_for(self, key, ext="wav") -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        return self.dir / f"{key}.{ext}"

    def has(self, key, ext="wav") -> bool:
        return self.path_for(key, ext).exists()
