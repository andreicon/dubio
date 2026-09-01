from __future__ import annotations

from pathlib import Path

import numpy as np

from dubio.errors import DubError
from dubio.engines.separation.base import Stems


class DemucsSeparator:
    def __init__(self, model: str = "htdemucs"):
        self.model = model

    def separate(self, source_wav: str | Path, out_dir: str | Path) -> Stems:
        try:
            import torch
            from demucs.apply import apply_model
            from demucs.audio import AudioFile
            from demucs.pretrained import get_model
        except Exception as exc:  # noqa: BLE001
            raise DubError("SEP-001", f"Demucs unavailable: {exc}", {"source": str(source_wav)}) from exc

        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)

        try:
            model = get_model(name=self.model)
            sources = apply_model(
                model,
                AudioFile(str(source_wav)),
                device="cuda" if torch.cuda.is_available() else "cpu",
            )
            dialogue = out / "dialogue.wav"
            music = out / "music.wav"
            sfx = out / "sfx.wav"
            stems = {name: stem.cpu().numpy() for name, stem in zip(model.sources, sources[0], strict=False)}
            dialogue_audio = stems.get("vocals")
            if dialogue_audio is None:
                raise DubError("SEP-001", "Demucs did not produce vocals stem", {"source": str(source_wav)})

            non_vocal_stems = [stem for name, stem in stems.items() if name != "vocals"]
            if non_vocal_stems:
                music_audio = np.sum(non_vocal_stems, axis=0)
                sfx_audio = stems.get("other", np.zeros_like(dialogue_audio))
            else:
                music_audio = np.zeros_like(dialogue_audio)
                sfx_audio = np.zeros_like(dialogue_audio)

            from dubio.audio.measure import write_wav

            write_wav(dialogue, dialogue_audio, 48000)
            write_wav(music, music_audio, 48000)
            write_wav(sfx, sfx_audio, 48000)
            return Stems(dialogue=dialogue, music=music, sfx=sfx)
        except DubError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DubError("SEP-001", f"Separation failed: {exc}", {"source": str(source_wav)}) from exc
