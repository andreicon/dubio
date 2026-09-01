class WhisperASR:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def transcribe(self, audio_path: str, language: str | None = None):
        raise NotImplementedError("WhisperASR is not implemented in M0")

    def detect_language(self, audio_path: str) -> str:
        raise NotImplementedError("WhisperASR is not implemented in M0")
