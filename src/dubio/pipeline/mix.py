from __future__ import annotations

from pathlib import Path

import numpy as np

from dubio.audio.measure import load_wav, write_wav
from dubio.audio.process import gain_db
from dubio.errors import DubError
from dubio.logging import get_logger
from dubio.project.manifest import Manifest


def _pad_to_length(samples: np.ndarray, length: int) -> np.ndarray:
    if len(samples) >= length:
        return samples
    if samples.ndim == 1:
        return np.pad(samples, (0, length - len(samples)))
    return np.pad(samples, ((0, length - len(samples)), (0, 0)))


def place_clip(bus: np.ndarray, clip: np.ndarray, start_s: float, sr: int, fit: bool) -> np.ndarray:
    start = int(start_s * sr)
    end = start + len(clip)
    if start < 0:
        raise DubError("MIX-001", "Clip starts before the bus", {"start_s": start_s})
    if start >= len(bus):
        if not fit:
            raise DubError("MIX-001", "Clip starts after the bus", {"start_s": start_s})
        return bus.copy()
    if end > len(bus):
        if not fit:
            raise DubError("MIX-001", "Clip overruns available interval", {"start_s": start_s})
        clip = clip[: len(bus) - start]
        end = len(bus)

    out = bus.copy()
    out[start:end] += clip
    return out


def build_dialogue_bus(manifest, paths, sr: int, total_samples: int) -> tuple[np.ndarray, list[str]]:
    bus = np.zeros(total_samples)
    failed: list[str] = []

    utterances = sorted(manifest.utterances, key=lambda utterance: utterance.source.start)
    for index, utterance in enumerate(utterances):
        clip_path = Path(paths.processed_dir) / f"{utterance.id}.wav"
        if not clip_path.exists():
            continue

        clip, clip_sr = load_wav(clip_path)
        if clip_sr != sr:
            raise DubError("MIX-002", "Processed clip sample rate mismatch", {"utterance_id": utterance.id, "sr": clip_sr})

        start = int(utterance.source.start * sr)
        next_start = total_samples
        if index + 1 < len(utterances):
            next_start = int(utterances[index + 1].source.start * sr)

        available = max(next_start - start, 0)
        if len(clip) > available:
            failed.append(utterance.id)
            utterance.validation.duration = "fail"
            if available == 0:
                continue
            clip = clip[:available]

        bus = place_clip(bus, clip, utterance.source.start, sr, fit=True)

    return bus, failed


def mix_tracks(dialogue: np.ndarray, music: np.ndarray, sfx: np.ndarray, gains: dict) -> np.ndarray:
    n = max(len(dialogue), len(music), len(sfx))
    dialogue = _pad_to_length(gain_db(dialogue, gains.get("dialogue", 0.0)), n)
    music = _pad_to_length(gain_db(music, gains.get("music", 0.0)), n)
    sfx = _pad_to_length(gain_db(sfx, gains.get("sfx", 0.0)), n)
    return dialogue + music + sfx


def mix_project(paths, config) -> None:
    manifest = Manifest.load(paths.manifest)

    music_path = Path(paths.audio_dir) / "music.wav"
    sfx_path = Path(paths.audio_dir) / "sfx.wav"
    music, music_sr = load_wav(music_path)
    sfx, sfx_sr = load_wav(sfx_path)
    if music_sr != sfx_sr:
        raise DubError("MIX-003", "Stem sample rate mismatch", {"music_sr": music_sr, "sfx_sr": sfx_sr})

    sr = getattr(config.audio, "sample_rate", music_sr) or music_sr
    if sr != music_sr:
        raise DubError("MIX-004", "Configured sample rate does not match stems", {"configured": sr, "stems": music_sr})

    last_end = max((int(utterance.source.end * sr) for utterance in manifest.utterances), default=0)
    total_samples = max(len(music), len(sfx), last_end)
    dialogue, failed = build_dialogue_bus(manifest, paths, sr, total_samples)
    final = mix_tracks(dialogue, music, sfx, {"dialogue": 0.0, "music": 0.0, "sfx": 0.0})

    paths.mix_dir.mkdir(parents=True, exist_ok=True)
    write_wav(paths.mix_dir / "dialogue.wav", dialogue, sr)
    write_wav(paths.mix_dir / "music.wav", music, sr)
    write_wav(paths.mix_dir / "sfx.wav", sfx, sr)
    write_wav(paths.mix_dir / "final.wav", final, sr)

    if failed:
        get_logger("mix").warning("dialogue_clips_failed", ids=failed)

    manifest.save(paths.manifest)
