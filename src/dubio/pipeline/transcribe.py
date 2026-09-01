from __future__ import annotations

import json

from dubio.project.manifest import Manifest, SourceSpan, Utterance


def transcribe_segments_to_utterances(res) -> list[Utterance]:
    utterances = []
    for index, segment in enumerate(res.segments, start=1):
        utterances.append(
            Utterance(
                id=f"utt_{index:06d}",
                speaker="speaker_00",
                source=SourceSpan(
                    text=segment.text,
                    start=segment.start,
                    end=segment.end,
                    words=[{"word": word.word, "start": word.start, "end": word.end} for word in segment.words],
                ),
            )
        )
    return utterances


def transcribe(paths, asr, config) -> None:
    manifest = Manifest.load(paths.manifest)
    result = asr.transcribe(str(paths.audio_dir / "source.wav"), language=manifest.project.source_language)
    manifest.utterances = transcribe_segments_to_utterances(result)
    (paths.audio_dir / "transcript.json").write_text(
        json.dumps(
            {
                "language": result.language,
                "segments": [segment.__dict__ for segment in result.segments],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest.save(paths.manifest)
