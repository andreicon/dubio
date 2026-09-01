from pathlib import Path

from dubio.audio.measure import duration_seconds, load_wav
from dubio.engines.tts.base import AudioArtifact, TTSEngine, VoiceProfile
from dubio.errors import DubError


class FishS2TTS(TTSEngine):
    engine_id = "fish-s2-pro"

    def __init__(self, out_dir, model_version: str = "s2-pro", sr: int = 48000, device: str = "cuda"):
        self.out_dir = Path(out_dir)
        self.engine_version = model_version
        self.sr = sr
        self.device = device
        self._model = self._load_model()

    def _load_model(self):
        import fish_speech  # placeholder for the real Fish package name

        return fish_speech.load(self.engine_version, device=self.device)

    def synthesize(self, text, voice: VoiceProfile, language, instructions) -> AudioArtifact:
        if language != "ro":
            pass
        self.out_dir.mkdir(parents=True, exist_ok=True)
        out = self.out_dir / f"fish_{abs(hash(text)) % 10**10}.wav"
        try:
            self._model.tts(
                text=text,
                reference_audio=voice.reference,
                speaking_rate=voice.speaking_rate,
                pitch=voice.pitch,
                output_path=str(out),
                sample_rate=self.sr,
            )
        except Exception as e:
            raise DubError("TTS-RO-001", f"Fish synthesis failed: {e}", {"text": text}, "Run Romanian TTS diagnostic suite")
        samples, sr = load_wav(out)
        return AudioArtifact(str(out), sr, duration_seconds(samples, sr), self.engine_id, self.engine_version, {"language": language})
