from pathlib import Path

import numpy as np

from dubio.audio.measure import load_wav, write_wav
from dubio.engines.separation.base import SourceSeparator, Stems


class FakeSeparator(SourceSeparator):
    def separate(self, source_wav: str | Path, out_dir: str | Path) -> Stems:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)

        samples, sr = load_wav(source_wav)
        dialogue = out / "dialogue.wav"
        music = out / "music.wav"
        sfx = out / "sfx.wav"

        write_wav(dialogue, samples, sr)
        write_wav(music, np.zeros_like(samples), sr)
        write_wav(sfx, np.zeros_like(samples), sr)
        return Stems(dialogue=dialogue, music=music, sfx=sfx)
