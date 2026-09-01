import numpy as np
from pyloudnorm import Meter, normalize
from scipy.signal import butter, resample_poly, sosfilt


def remove_dc(x: np.ndarray) -> np.ndarray:
    return x - np.mean(x)


def high_pass(x: np.ndarray, sr: int, cutoff: float = 80.0) -> np.ndarray:
    sos = butter(2, cutoff / (sr / 2), btype="highpass", output="sos")
    return sosfilt(sos, x)


def apply_eq(x: np.ndarray, sr: int, bands: list[dict]) -> np.ndarray:
    y = x
    for band in bands:
        kind = band["type"]
        freq = band["freq"]
        if kind == "highpass":
            y = high_pass(y, sr, cutoff=freq)
        elif kind == "lowpass":
            sos = butter(2, freq / (sr / 2), btype="lowpass", output="sos")
            y = sosfilt(sos, y)
        elif kind == "peak":
            gain_db = band.get("gain_db", 0.0)
            q = band.get("q", 1.0)
            w0 = freq / (sr / 2)
            bw = max(w0 / q, 1e-4)
            low = max(w0 - bw / 2, 1e-4)
            high = min(w0 + bw / 2, 0.999)
            sos = butter(2, [low, high], btype="bandpass", output="sos")
            amount = 10 ** (gain_db / 20) - 1.0
            y = y + amount * sosfilt(sos, y)
        elif kind == "lowshelf":
            sos = butter(2, freq / (sr / 2), btype="lowpass", output="sos")
            y = y + band.get("gain_db", 0.0) / 24.0 * sosfilt(sos, y)
        elif kind == "highshelf":
            sos = butter(2, freq / (sr / 2), btype="highpass", output="sos")
            y = y + band.get("gain_db", 0.0) / 24.0 * sosfilt(sos, y)
    return y


def compress(x: np.ndarray, threshold_db: float = -18, ratio: float = 3.0, sr: int = 48000) -> np.ndarray:
    del sr
    threshold = 10 ** (threshold_db / 20)
    peak = np.abs(x)
    gain = np.ones_like(x)
    over = peak > threshold
    if np.any(over):
        compressed = threshold * (peak[over] / threshold) ** (1 / ratio)
        gain[over] = compressed / peak[over]
    return x * gain


def normalize_loudness(x: np.ndarray, sr: int, target_lufs: float = -16.0) -> np.ndarray:
    if len(x) == 0:
        return x
    meter = Meter(sr)
    analysis = x if len(x) >= sr else np.pad(x, (0, sr - len(x)))
    loudness = meter.integrated_loudness(analysis)
    if loudness == float("-inf"):
        return x
    return normalize.loudness(x, loudness, target_lufs)


def true_peak_limit(x: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    ceiling = 10 ** (ceiling_db / 20)
    if len(x) == 0:
        return x
    true_peak = np.max(np.abs(resample_poly(x, 4, 1)))
    if true_peak <= ceiling or true_peak == 0:
        return x
    return x * (ceiling / true_peak)


def gain_db(x: np.ndarray, db: float) -> np.ndarray:
    return x * (10 ** (db / 20))
