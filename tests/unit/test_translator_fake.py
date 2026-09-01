from dubio.engines.translation.base import Candidate, TranslationRequest
from dubio.engines.translation.fake import FakeTranslator


def test_fake_returns_candidates():
    t = FakeTranslator({"What are you doing?": ["Ce faci?", "Ce naiba faci acolo?"]})
    req = TranslationRequest("What are you doing?", "eng", "ron", 2.85, "agitated", "", "")
    cands = t.translate(req)
    assert cands[0].text == "Ce faci?"
    assert all(isinstance(c, Candidate) and c.estimated_duration > 0 for c in cands)
