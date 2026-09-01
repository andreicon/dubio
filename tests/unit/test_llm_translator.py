import json

import pytest

from dubio.engines.translation.base import TranslationRequest
from dubio.engines.translation.llm import LLMTranslator
from dubio.errors import DubError


class _FakeResp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


class _FakeClient:
    def __init__(self, content):
        self._content = content
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, **kw):
        self.kw = kw
        return _FakeResp(self._content)


def test_llm_parses_candidates():
    content = json.dumps(
        {"candidates": [{"text": "Ce faci?"}, {"text": "Ce naiba faci acolo?"}]},
        ensure_ascii=False,
    )
    t = LLMTranslator(client=_FakeClient(content), model="x")
    req = TranslationRequest("What are you doing?", "eng", "ron", 2.85, "agitated", "", "")
    cands = t.translate(req)
    assert cands[0].text == "Ce faci?"
    assert cands[0].estimated_duration > 0


def test_llm_raises_on_malformed_output():
    t = LLMTranslator(client=_FakeClient("not json"), model="x")
    req = TranslationRequest("What are you doing?", "eng", "ron", 2.85, "agitated", "", "")
    with pytest.raises(DubError) as excinfo:
        t.translate(req)
    assert excinfo.value.code == "TRANS-001"


def test_llm_raises_on_empty_candidate_list():
    content = json.dumps({"candidates": []}, ensure_ascii=False)
    t = LLMTranslator(client=_FakeClient(content), model="x")
    req = TranslationRequest("What are you doing?", "eng", "ron", 2.85, "agitated", "", "")
    with pytest.raises(DubError) as excinfo:
        t.translate(req)
    assert excinfo.value.code == "TRANS-002"
