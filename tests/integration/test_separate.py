import numpy as np

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
