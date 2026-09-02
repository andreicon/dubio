from __future__ import annotations

from dubio.engines.diarization.base import DiarizationEngine, SpeakerTurn


class PyannoteDiarizer(DiarizationEngine):
    def __init__(self, pipeline=None):
        if pipeline is None:
            from pyannote.audio import Pipeline

            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
        self._pipeline = pipeline

    def diarize(self, audio_path):
        output = self._pipeline(audio_path)
        annotation = getattr(output, "speaker_diarization", output)
        turns = []
        if hasattr(annotation, "itertracks"):
            for segment, _, speaker in annotation.itertracks(yield_label=True):
                turns.append(SpeakerTurn(speaker, segment.start, segment.end))
        return turns
