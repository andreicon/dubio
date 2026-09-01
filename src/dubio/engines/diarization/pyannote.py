from __future__ import annotations

from dubio.engines.diarization.base import DiarizationEngine, SpeakerTurn


class PyannoteDiarizer(DiarizationEngine):
    def __init__(self, pipeline=None):
        if pipeline is None:
            from pyannote.audio import Pipeline

            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
        self._pipeline = pipeline

    def diarize(self, audio_path):
        turns = self._pipeline(audio_path)
        return [SpeakerTurn(turn.speaker, turn.start, turn.end) for turn in turns]
