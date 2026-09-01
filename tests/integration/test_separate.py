import numpy as np
import pytest

from dubio.errors import DubError
from dubio.audio.measure import write_wav
from dubio.engines.separation.fake import FakeSeparator
from dubio.pipeline.separate import separate
from dubio.project.paths import ProjectPaths


def test_fake_separator_writes_three_stems(tmp_path):
    src = tmp_path / "source.wav"
    write_wav(src, np.zeros(48000), 48000)

    stems = FakeSeparator().separate(src, tmp_path)

    assert stems.dialogue.exists()
    assert stems.music.exists()
    assert stems.sfx.exists()


def test_separate_falls_back_to_source(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    source = paths.audio_dir / "source.wav"
    write_wav(source, np.ones(48000), 48000)

    stems = separate(paths, separator=object(), config=None, fallback_to_source=True)

    assert stems.dialogue == source
    assert stems.music.exists()
    assert stems.sfx.exists()


def test_separate_normalizes_failure_when_not_falling_back(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    source = paths.audio_dir / "source.wav"
    write_wav(source, np.ones(48000), 48000)

    class BrokenSeparator:
        def separate(self, source_wav, out_dir):
            raise ValueError("boom")

    with pytest.raises(DubError) as excinfo:
        separate(paths, separator=BrokenSeparator(), config=None, fallback_to_source=False)

    assert excinfo.value.code == "SEP-001"
    assert excinfo.value.context["source"] == str(source)
