from __future__ import annotations

import shutil
import os
from pathlib import Path

from dubio.audio.measure import duration_seconds, load_wav
from dubio.engines.tts.base import AudioArtifact, TTSEngine, VoiceProfile
from dubio.errors import DubError


class DelusionTTS(TTSEngine):
    engine_id = "delusion"

    def __init__(self, out_dir, model_version: str = "omnivoice", quant: str = "q8_0"):
        self.out_dir = Path(out_dir)
        self.engine_version = model_version
        self.quant = quant
        self._audio = None

    def _load_model(self):
        from delusion.audio.cpp import AudioCPP, OmniVoice

        return AudioCPP(model=OmniVoice(quant=self.quant).download())

    def _ensure_cli(self):
        audiocpp_path = os.environ.get("AUDIOCPP_PATH")
        if audiocpp_path:
            cli = Path(audiocpp_path)
            if cli.is_file() and os.access(cli, os.X_OK):
                return

        if shutil.which("audiocpp_cli") is None:
            raise DubError(
                "ENGINE-005",
                "Missing audiocpp_cli",
                {},
                "Set AUDIOCPP_PATH to the audiocpp_cli binary or run ./install_audiocpp_cli.sh from the repo root so audiocpp_cli is available on PATH",
            )

    @property
    def audio(self):
        if self._audio is None:
            self._ensure_cli()
            self._audio = self._load_model()
        return self._audio

    def synthesize(self, text, voice: VoiceProfile, language, instructions) -> AudioArtifact:
        self._ensure_cli()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        out = self.out_dir / f"delusion_{abs(hash((voice.id, text))) % 10**10}.wav"
        try:
            speak = self.audio.tts(text=text, reference=voice.reference)
            out.write_bytes(speak.wav)
        except Exception as e:
            raise DubError("TTS-RO-001", f"Delusion synthesis failed: {e}", {"text": text}, "Check Delusion/audio.cpp model availability")
        samples, sr = load_wav(out)
        return AudioArtifact(str(out), sr, duration_seconds(samples, sr), self.engine_id, self.engine_version, {"language": language})
