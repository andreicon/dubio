from typer.testing import CliRunner

from dubio.cli import app
from dubio.project.manifest import Manifest


def test_init_creates_manifest(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "init",
            "ep1",
            "--source",
            "s.mp4",
            "--projects-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output

    manifest = Manifest.load(tmp_path / "ep1" / "manifest.json")
    assert manifest.project.id == "ep1"
    assert manifest.project.target_language == "ron"
