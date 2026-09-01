from __future__ import annotations

from dubio.pipeline.mix import mix_project
from dubio.pipeline.normalize import normalize_utterance
from dubio.pipeline.synthesize import synthesize_utterance
from dubio.pipeline.validate import validate_utterance
from dubio.project.manifest import Manifest
from dubio.utils.cache import Cache


def regenerate_utterance(paths, uid, engines, config) -> None:
    manifest = Manifest.load(paths.manifest)
    utterance = manifest.get_utterance(uid)
    cache = Cache(paths.tts_dir / "_cache")

    synthesize_utterance(manifest, utterance, engines["tts"], cache, paths, force=True)
    normalize_utterance(manifest, utterance, paths, config)
    validate_utterance(manifest, utterance, engines["asr"], config)
    manifest.save(paths.manifest)
    mix_project(paths, config)
