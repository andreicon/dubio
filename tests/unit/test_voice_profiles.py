from dubio.pipeline.voices import map_character
from dubio.project.manifest import Character, Manifest, Project, SourceSpan, Utterance, Voice
from dubio.project.voices import load_voice_profile, resolve_voice


def test_load_yaml_profile(tmp_path):
    path = tmp_path / "bugs.yaml"
    path.write_text(
        "id: bugs\n"
        "engine: fish-s2-pro\n"
        "reference: voices/bugs.wav\n"
        "parameters:\n"
        "  pitch: 2\n"
        "  speaking_rate: 1.0\n"
        "  gain_db: -1.5\n"
        "style:\n"
        "  personality: mischievous\n"
        "  energy: high\n",
        encoding="utf-8",
    )

    voice_profile = load_voice_profile(path)

    assert voice_profile.id == "bugs"
    assert voice_profile.engine == "fish-s2-pro"
    assert voice_profile.reference == "voices/bugs.wav"
    assert voice_profile.pitch == 2
    assert voice_profile.speaking_rate == 1.0
    assert voice_profile.gain_db == -1.5
    assert voice_profile.style["personality"] == "mischievous"
    assert voice_profile.style["energy"] == "high"


def test_resolve_voice_via_character():
    manifest = Manifest(project={"id": "e", "source": "s", "source_language": "eng", "target_language": "ron"})
    manifest.characters["SPEAKER_00"] = Character(name="Bugs", voice="voice_bugs")
    manifest.voices["voice_bugs"] = Voice(engine="fish-s2-pro", reference="voices/bugs.wav", pitch=2)
    utterance = Utterance(
        id="utt_000001",
        speaker="SPEAKER_00",
        source=SourceSpan(text="hi", start=0, end=1),
    )

    voice_profile = resolve_voice(manifest, utterance)

    assert voice_profile.id == "voice_bugs"
    assert voice_profile.reference == "voices/bugs.wav"


def test_map_character_can_enroll_voice_profile():
    manifest = Manifest(project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"))

    map_character(
        manifest,
        "SPEAKER_00",
        "Bugs",
        voice="bugs_ro",
        reference="voices/bugs.wav",
        engine="delusion",
    )

    assert manifest.characters["SPEAKER_00"].voice == "bugs_ro"
    assert manifest.voices["bugs_ro"].engine == "delusion"
    assert manifest.voices["bugs_ro"].reference == "voices/bugs.wav"
