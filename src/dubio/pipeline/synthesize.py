from __future__ import annotations

from pathlib import Path
import shutil

from dubio.audio.measure import duration_seconds, load_wav
from dubio.engines.tts.base import TTSEngine
from dubio.project.manifest import Manifest
from dubio.project.voices import resolve_voice
from dubio.utils.cache import Cache, tts_cache_key


def _utterance_text(utterance) -> str:
    return utterance.translation.text or utterance.source.text


def synthesize_utterance(manifest, utterance, tts: TTSEngine, cache: Cache, paths, force: bool = False) -> None:
    voice = resolve_voice(manifest, utterance)
    text = _utterance_text(utterance)
    instructions = {}
    params = {"pitch": voice.pitch, "speaking_rate": voice.speaking_rate, "gain_db": voice.gain_db}
    language = getattr(manifest.project, "target_language", "ro")
    key = tts_cache_key(tts.engine_id, tts.engine_version, voice.id, language, text, instructions, params)

    dest = Path(paths.tts_dir) / f"{utterance.id}.wav"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cached = cache.path_for(key)

    if cached.exists() and not force:
        source = cached
        samples, sr = load_wav(source)
        duration = duration_seconds(samples, sr)
    else:
        artifact = tts.synthesize(text, voice, language, instructions)
        source = Path(artifact.path)
        shutil.copyfile(source, cached)
        duration = artifact.duration

    shutil.copyfile(source, dest)
    utterance.tts.engine = tts.engine_id
    utterance.tts.voice = voice.id
    utterance.tts.file = str(dest)
    utterance.tts.duration = round(duration, 3)
    utterance.tts.engine_version = tts.engine_version


def synthesize_project(paths, tts: TTSEngine, config, force: bool = False, utterance_id: str | None = None) -> None:
    manifest = Manifest.load(paths.manifest)
    cache = Cache(Path(paths.tts_dir) / "_cache")

    if utterance_id is not None:
        utterances = [manifest.get_utterance(utterance_id)]
    else:
        utterances = manifest.utterances

    for utterance in utterances:
        synthesize_utterance(manifest, utterance, tts, cache, paths, force=force)
        manifest.save(paths.manifest)

    manifest.save(paths.manifest)
