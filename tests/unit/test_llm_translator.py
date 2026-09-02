import json

import pytest

from dubio.engines.translation.base import TranslationRequest
from dubio.engines.translation.llm import LLMTranslator
from dubio.errors import DubError
from dubio.engines.translation.gemini import GeminiTranslator
from dubio.engines.translation.rate_limit import RateLimiter
from dubio.config import Config, EngineCfg
from dubio.cli import _build_translator


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


class _FakeGeminiChat:
    def __init__(self, content):
        self._content = content

    def send_message(self, prompt, config=None):
        return type("R", (), {"text": self._content})()


class _FakeGeminiClient:
    def __init__(self, content):
        self._content = content
        self.chats = self

    def create(self, **kw):
        self.kw = kw
        return _FakeGeminiChat(self._content)


def test_gemini_strips_code_fence_before_parsing(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    content = "```json\n{" + '"candidates":[{"text":"Ce faci?"}]}' + "\n```"
    t = GeminiTranslator(model="x")
    t.chat = _FakeGeminiChat(content)
    req = TranslationRequest("What are you doing?", "eng", "ron", 2.85, "agitated", "", "")
    cands = t.translate(req)
    assert cands[0].text == "Ce faci?"


def test_rate_limiter_waits_before_allowing_next_request(monkeypatch):
    limiter = RateLimiter(5)
    now = [100.0]
    slept = []

    monkeypatch.setattr("dubio.engines.translation.rate_limit.time.monotonic", lambda: now[0])
    monkeypatch.setattr("dubio.engines.translation.rate_limit.time.sleep", lambda seconds: slept.append(seconds))

    limiter.wait()
    now[0] += 5.0
    limiter.wait()

    assert slept == [7.0]


def test_rate_limiter_rejects_non_positive_rate():
    with pytest.raises(ValueError):
        RateLimiter(0)


def test_build_translator_passes_rate_limit_from_config(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    config = Config(translation=EngineCfg(engine="gemini", rate_limit_per_minute=9))
    t = _build_translator(config, None)
    assert isinstance(t, GeminiTranslator)
    assert t._rate_limiter is not None
    assert t._rate_limiter.min_interval == pytest.approx(60 / 9)
