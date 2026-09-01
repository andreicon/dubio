from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf


@dataclass
class LoudnessStats:
    integrated_lufs: float
    true_peak_db: float
    rms_db: float


def duration_seconds(samples: np.ndarray, sr: int) -> float:
    return len(samples) / sr


def _mono(samples: np.ndarray) -> np.ndarray:
    if samples.ndim == 1:
        return samples
    return samples.mean(axis=1)


def measure_loudness(samples: np.ndarray, sr: int) -> LoudnessStats:
    mono = _mono(samples)
    meter = pyln.Meter(sr)
    integrated = float(meter.integrated_loudness(mono)) if len(mono) >= sr else -70.0
    peak = float(np.max(np.abs(mono))) or 1e-9
    true_peak_db = 20 * np.log10(peak)
    rms = float(np.sqrt(np.mean(mono**2))) or 1e-9
    rms_db = 20 * np.log10(rms)
    return LoudnessStats(integrated, true_peak_db, rms_db)


def load_wav(path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path))
    return data, sr


def write_wav(path, samples: np.ndarray, sr: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), samples, sr)
