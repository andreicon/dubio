import numpy as np
import pytest

from dubio.errors import DubError
from dubio.pipeline.mix import mix_tracks, place_clip


def test_place_clip_at_offset():
    sr = 48000
    bus = np.zeros(sr)
    clip = np.ones(int(0.1 * sr)) * 0.5

    out = place_clip(bus, clip, start_s=0.5, sr=sr, fit=True)

    assert out[int(0.5 * sr)] == 0.5
    assert out[0] == 0.0


def test_place_clip_raises_when_clip_does_not_fit_and_fit_is_false():
    sr = 48000
    bus = np.zeros(10)
    clip = np.ones(4)

    with pytest.raises(DubError, match="overruns"):
        place_clip(bus, clip, start_s=0.75, sr=sr, fit=False)


def test_mix_tracks_sums_with_gain():
    d = np.ones(10) * 0.5
    m = np.ones(10) * 0.2
    s = np.zeros(10)

    out = mix_tracks(d, m, s, gains={"dialogue": 0.0, "music": -6.0, "sfx": 0.0})

    assert out[0] > 0.5
