from tests.fixtures.romanian_lines import ROMANIAN_TEST_LINES

from dub.utils.romanian import has_diacritics
from dub.utils.similarity import text_similarity


def test_fixture_lines_have_diacritics():
    assert any(has_diacritics(l) for l in ROMANIAN_TEST_LINES)
    assert "Ține minte ce ți-am spus." in ROMANIAN_TEST_LINES


def test_similarity_ignores_punctuation():
    assert text_similarity("Ce faci, băiete?", "Ce faci băiete") > 0.95


def test_similarity_flags_lexical_drift():
    assert text_similarity("Ce faci acolo?", "Unde mergi mâine?") < 0.5
