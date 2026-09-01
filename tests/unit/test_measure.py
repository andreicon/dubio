import numpy as np

from dub.audio.measure import duration_seconds, measure_loudness


def test_duration():
    sr = 48000
    samples = np.zeros(sr)
    assert abs(duration_seconds(samples, sr) - 1.0) < 1e-6


def test_loudness_of_sine_is_reasonable():
    sr = 48000
    t = np.arange(sr) / sr
    sine = 0.5 * np.sin(2 * np.pi * 440 * t)
    stats = measure_loudness(sine, sr)
    assert -30 < stats.integrated_lufs < -3
    assert stats.true_peak_db <= 0.5
    assert stats.rms_db < 0
