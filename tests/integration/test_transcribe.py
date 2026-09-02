import json
from pathlib import Path

import numpy as np

from dubio.audio.measure import load_wav, write_wav

from dubio.config import load_config
from dubio.engines.asr.base import ASRResult, Segment, Word
from dubio.pipeline.transcribe import transcribe, transcribe_segments_to_utterances
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths


class StubASR:
    def transcribe(self, audio_path, language=None):
        return ASRResult(
            text="What are you doing?",
            language=language or "eng",
            segments=[
                Segment(
                    "What are you doing?",
                    12.43,
                    15.87,
                    [Word("What", 12.43, 12.71)],
                )
            ],
        )


def test_segments_become_utterances():
    result = ASRResult(
        text="What are you doing?",
        language="eng",
        segments=[
            Segment(
                "What are you doing?",
                12.43,
                15.87,
                [Word("What", 12.43, 12.71)],
            )
        ],
    )

    utterances = transcribe_segments_to_utterances(result)

    assert utterances[0].id == "utt_000001"
    assert utterances[0].source.start == 12.43 and utterances[0].source.end == 15.87
    assert utterances[0].source.words[0]["word"] == "What"


def test_transcribe_writes_transcript_and_manifest(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    Manifest(
        project=Project(
            id="ep1",
            source=str(tmp_path / "clip.mp4"),
            source_language="eng",
            target_language="ron",
        )
    ).save(paths.manifest)

    transcribe(paths, StubASR(), load_config(None))

    transcript = json.loads((paths.audio_dir / "transcript.json").read_text(encoding="utf-8"))
    manifest = Manifest.load(paths.manifest)

    assert transcript["segments"][0]["words"][0]["word"] == "What"
    assert manifest.utterances[0].id == "utt_000001"
    assert manifest.utterances[0].source.start == 12.43


def test_transcribe_writes_exact_reference_clip(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    source_sr = 48_000
    source = np.arange(19 * source_sr, dtype=np.float32) / float(19 * source_sr)
    write_wav(paths.audio_dir / "source.wav", source, source_sr)
    Manifest(
        project=Project(
            id="ep1",
            source=str(tmp_path / "clip.mp4"),
            source_language="eng",
            target_language="ron",
        )
    ).save(paths.manifest)

    transcribe(paths, StubASR(), load_config(None))

    manifest = Manifest.load(paths.manifest)
    clip_path = paths.base / Path(manifest.utterances[0].reference_audio)
    clip, sr = load_wav(clip_path)

    assert manifest.utterances[0].reference_audio == "audio/reference/utt_000001.wav"
    assert sr == 48000
    assert len(clip) == int(round((15.87 - 12.43) * sr))
    np.testing.assert_allclose(
        clip,
        source[int(round(12.43 * sr)):int(round(15.87 * sr))],
        atol=5e-5,
        rtol=0,
    )
