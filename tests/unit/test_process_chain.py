import numpy as np

from dubio.audio.measure import measure_loudness
from dubio.audio.process import gain_db, normalize_loudness, remove_dc, true_peak_limit


def test_remove_dc():
    x = np.ones(1000) * 0.3 + 0.1
    assert abs(np.mean(remove_dc(x))) < 1e-6


def test_normalize_hits_target():
    sr = 48000
    t = np.arange(2 * sr) / sr
    x = 0.05 * np.sin(2 * np.pi * 300 * t)
    y = normalize_loudness(x, sr, target_lufs=-16.0)
    assert abs(measure_loudness(y, sr).integrated_lufs - (-16.0)) < 1.5


def test_true_peak_limit_ceiling():
    x = np.array([0.0, 1.5, -1.4, 0.2])
    y = true_peak_limit(x, ceiling_db=-1.0)
    ceiling = 10 ** (-1.0 / 20)
    assert np.max(np.abs(y)) <= ceiling + 1e-6


def test_gain_db_doubles_at_6db():
    x = np.array([0.1, -0.1])
    assert np.allclose(gain_db(x, 6.0), x * (10 ** (6 / 20)))
