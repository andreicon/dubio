from __future__ import annotations

from pathlib import Path

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
            source_audio = sources[0]
            dialogue_audio = source_audio[0].cpu().numpy()
            music_audio = source_audio[1].cpu().numpy() if len(source_audio) > 1 else dialogue_audio * 0
            sfx_audio = source_audio[2].cpu().numpy() if len(source_audio) > 2 else dialogue_audio * 0

            from dubio.audio.measure import write_wav

            write_wav(dialogue, dialogue_audio, model.samplerate)
            write_wav(music, music_audio, model.samplerate)
            write_wav(sfx, sfx_audio, model.samplerate)
            return Stems(dialogue=dialogue, music=music, sfx=sfx)
        except DubError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DubError("SEP-001", f"Separation failed: {exc}", {"source": str(source_wav)}) from exc
