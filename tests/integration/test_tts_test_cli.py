from typer.testing import CliRunner

from dubio.harness.tts_eval import app


def test_cli_fake_engine(tmp_path):
    runner = CliRunner()
    out = tmp_path / "result"
    r = runner.invoke(app, ["Ce faci, băiete?", "--engine", "fake", "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert (out / "metrics.json").exists()
