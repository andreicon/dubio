from __future__ import annotations

import numpy as np

from dubio.errors import DubError
from dubio.audio.measure import load_wav, write_wav
from dubio.engines.separation.base import Stems


def separate(paths, separator, config, fallback_to_source: bool = True) -> Stems:
    source = paths.audio_dir / "source.wav"
    out_dir = paths.audio_dir

    try:
        return separator.separate(source, out_dir)
    except Exception as exc:
        if not fallback_to_source:
            raise DubError("SEP-001", f"Separation failed: {exc}", {"source": str(source)}) from exc

        out_dir.mkdir(parents=True, exist_ok=True)
        samples, sr = load_wav(source)
        dialogue = source
        music = out_dir / "music.wav"
        sfx = out_dir / "sfx.wav"
        write_wav(music, np.zeros_like(samples), sr)
        write_wav(sfx, np.zeros_like(samples), sr)
        return Stems(dialogue=dialogue, music=music, sfx=sfx)
