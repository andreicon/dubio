from typer.testing import CliRunner

from dubio.cli import app
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths


def test_voices_command_updates_manifest(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    Manifest(
        project=Project(
            id="ep1",
            source="s.mp4",
            source_language="eng",
            target_language="ron",
        )
    ).save(paths.manifest)

    result = CliRunner().invoke(
        app,
        ["voices", "ep1", "--map", "SPEAKER_00=Bugs", "--projects-root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    updated = Manifest.load(paths.manifest)
    assert updated.characters["SPEAKER_00"].name == "Bugs"


def test_voices_command_enrolls_delusion_reference(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    Manifest(
        project=Project(
            id="ep1",
            source="s.mp4",
            source_language="eng",
            target_language="ron",
        )
    ).save(paths.manifest)

    result = CliRunner().invoke(
        app,
        [
            "voices",
            "ep1",
            "--projects-root",
            str(tmp_path),
            "--map",
            "SPEAKER_00=Bugs",
            "--voice",
            "SPEAKER_00=bugs_ro",
            "--reference",
            "voices/bugs.wav",
        ],
    )

    assert result.exit_code == 0, result.output
    updated = Manifest.load(paths.manifest)
    assert updated.characters["SPEAKER_00"].name == "Bugs"
    assert updated.characters["SPEAKER_00"].voice == "bugs_ro"
    assert updated.voices["bugs_ro"].engine == "delusion"
    assert updated.voices["bugs_ro"].reference == "voices/bugs.wav"
