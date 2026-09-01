from dubio.engines.asr.fake import FakeASR
from dubio.project.manifest import SourceSpan, TTSInfo, Translation, Utterance
from dubio.validation.language import check_language
from dubio.validation.text import check_text


def _u(path, text):
    return Utterance(
        id="u",
        speaker="s",
        source=SourceSpan(text="x", start=0, end=2),
        translation=Translation(text=text, status="approved"),
        tts=TTSInfo(file=path, duration=2.0),
    )


def test_language_mismatch_fails():
    u = _u("a.wav", "Ce faci, băiete?")
    asr = FakeASR(scripted={"a.wav": ("Ce faci, băiete?", "en")})

    assert check_language(u, asr, expected="ro").status == "fail"


def test_text_match_tolerates_punctuation():
    u = _u("a.wav", "Ce faci, băiete?")
    asr = FakeASR(scripted={"a.wav": ("Ce faci băiete", "ro")})

    assert check_text(u, asr).status == "pass"


def test_text_flags_drift():
    u = _u("a.wav", "Ce faci acolo?")
    asr = FakeASR(scripted={"a.wav": ("Unde mergi mâine", "ro")})

    assert check_text(u, asr).status == "fail"
