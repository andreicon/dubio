from dubio.engines.diarization.base import DiarizationEngine, SpeakerTurn


class FakeDiarizer(DiarizationEngine):
    def __init__(self, turns):
        self._turns = turns

    def diarize(self, audio_path):
        return list(self._turns)
