from __future__ import annotations

import json

from dubio.engines.translation.base import TranslationRequest
from dubio.pipeline.timing import target_duration
from dubio.project.manifest import Manifest


def select_candidate(cands, target: float, max_ratio: float = 1.15):
    ceiling = target * max_ratio
    fitting = [c for c in cands if c.estimated_duration <= ceiling]
    if fitting:
        return max(fitting, key=lambda c: c.estimated_duration)
    return min(cands, key=lambda c: c.estimated_duration)


def translate_project(paths, translator, config) -> None:
    manifest = Manifest.load(paths.manifest)
    dump = []
    for index, utterance in enumerate(manifest.utterances):
        ctx = manifest.characters.get(utterance.speaker).name if utterance.speaker in manifest.characters else ""
        prev = manifest.utterances[index - 1].source.text if index > 0 else ""
        nxt = manifest.utterances[index + 1].source.text if index + 1 < len(manifest.utterances) else ""
        duration = target_duration(utterance)
        req = TranslationRequest(
            utterance.source.text,
            manifest.project.source_language,
            manifest.project.target_language,
            duration,
            ctx,
            prev,
            nxt,
        )
        cands = translator.translate(req)
        chosen = select_candidate(cands, duration, config.timing.max_duration_ratio)
        utterance.translation.text = chosen.text
        utterance.translation.candidates = [
            {"text": c.text, "estimated_duration": c.estimated_duration} for c in cands
        ]
        utterance.translation.status = "translated"
        dump.append({"id": utterance.id, "chosen": chosen.text, "candidates": utterance.translation.candidates})
    (paths.base / "translation.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest.save(paths.manifest)
