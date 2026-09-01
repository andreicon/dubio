from dubio.pipeline.voices import map_character
from dubio.project.manifest import Manifest, Project


def test_map_character_persists():
    manifest = Manifest(
        project=Project(
            id="ep1",
            source="s.mp4",
            source_language="eng",
            target_language="ron",
        )
    )

    map_character(manifest, "SPEAKER_00", "Bugs")

    assert manifest.characters["SPEAKER_00"].name == "Bugs"


def test_map_character_can_set_voice():
    manifest = Manifest(
        project=Project(
            id="ep1",
            source="s.mp4",
            source_language="eng",
            target_language="ron",
        )
    )

    map_character(manifest, "SPEAKER_00", "Bugs", voice="voice_01")

    assert manifest.characters["SPEAKER_00"].voice == "voice_01"
