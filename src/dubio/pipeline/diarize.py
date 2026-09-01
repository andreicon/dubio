from __future__ import annotations

import json

from dubio.project.manifest import Manifest


def _overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def assign_speakers(utterances, turns) -> None:
    for utterance in utterances:
        best = utterance.speaker
        best_overlap = 0.0
        for turn in turns:
            overlap = _overlap(utterance.source.start, utterance.source.end, turn.start, turn.end)
            if overlap > best_overlap:
                best = turn.speaker
                best_overlap = overlap
        utterance.speaker = best


def diarize(paths, diarizer, config) -> None:
    manifest = Manifest.load(paths.manifest)
    turns = diarizer.diarize(str(paths.audio_dir / "source.wav"))
    assign_speakers(manifest.utterances, turns)
    paths.audio_dir.mkdir(parents=True, exist_ok=True)
    (paths.audio_dir / "diarization.json").write_text(
        json.dumps([turn.__dict__ for turn in turns]), encoding="utf-8"
    )
    manifest.save(paths.manifest)
