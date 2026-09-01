import hashlib
from pathlib import Path

import numpy as np

from dubio.audio.measure import write_wav
from dubio.engines.tts.base import AudioArtifact, TTSEngine, VoiceProfile


class FakeTTS(TTSEngine):
    engine_id = "fake"
    engine_version = "0"

    def __init__(self, out_dir, chars_per_second: float = 15.0, sr: int = 48000):
        self.out_dir = Path(out_dir)
        self.cps = chars_per_second
        self.sr = sr

    def synthesize(self, text, voice: VoiceProfile, language, instructions) -> AudioArtifact:
        dur = max(0.2, len(text) / self.cps) / max(voice.speaking_rate, 0.1)
        n = int(dur * self.sr)
        t = np.arange(n) / self.sr
        tone = 0.1 * np.sin(2 * np.pi * 220 * t)
        name = hashlib.sha1(text.encode()).hexdigest()[:12] + ".wav"
        path = self.out_dir / name
        write_wav(path, tone, self.sr)
        return AudioArtifact(
            str(path),
            self.sr,
            dur,
            self.engine_id,
            self.engine_version,
            {"language": language, "text": text},
        )
