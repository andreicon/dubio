from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from dubio.audio.measure import load_wav, write_wav

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
    source_wav = paths.audio_dir / "source.wav"
    result = asr.transcribe(str(source_wav), language=manifest.project.source_language)
    samples, sr = load_wav(source_wav)
    utterances = transcribe_segments_to_utterances(result)
    paths.audio_dir.mkdir(parents=True, exist_ok=True)
    for utterance in utterances:
        start = max(0, int(round(utterance.source.start * sr)))
        end = min(len(samples), int(round(utterance.source.end * sr)))
        clip_path = paths.audio_dir / "reference" / f"{utterance.id}.wav"
        write_wav(clip_path, samples[start:end], sr)
        utterance.reference_audio = str(Path("audio") / "reference" / f"{utterance.id}.wav")
    manifest.utterances = utterances
    (paths.audio_dir / "transcript.json").write_text(
        json.dumps(
            {
                "language": result.language,
                "segments": [asdict(segment) for segment in result.segments],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest.save(paths.manifest)
