from typer.testing import CliRunner

from dubio.cli import app
from dubio.engines.separation.base import Stems


def test_separate_command_uses_no_separate_fallback(tmp_path, monkeypatch):
    calls = {}

    def fake_separate(paths, separator, config, fallback_to_source=True):
        calls["fallback_to_source"] = fallback_to_source
        calls["separator"] = separator
        return Stems(paths.audio_dir / "source.wav", paths.audio_dir / "music.wav", paths.audio_dir / "sfx.wav")

    monkeypatch.setattr("dubio.cli.separate", fake_separate)

    result = CliRunner().invoke(
        app,
        ["separate", "ep1", "--projects-root", str(tmp_path), "--no-separate"],
    )

    assert result.exit_code == 0, result.output
    assert calls["fallback_to_source"] is True
