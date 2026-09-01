from __future__ import annotations

import os

import pytest

from dubio.engines.translation.base import TranslationRequest
from dubio.engines.translation.llm import LLMTranslator


pytestmark = pytest.mark.model


openai = pytest.importorskip("openai")


@pytest.mark.skipif(
    not (os.getenv("DUBIO_LLM_BASE_URL") and os.getenv("DUBIO_LLM_API_KEY")),
    reason="requires DUBIO_LLM_BASE_URL and DUBIO_LLM_API_KEY",
)
def test_llm_real_smoke():
    client = openai.OpenAI(
        base_url=os.environ["DUBIO_LLM_BASE_URL"],
        api_key=os.environ["DUBIO_LLM_API_KEY"],
    )
    translator = LLMTranslator(client=client, model=os.getenv("DUBIO_LLM_MODEL", "gpt-4o-mini"))
    req = TranslationRequest("Ce faci, băiete?", "ron", "ron", 1.5, "neutral", "", "")
    cands = translator.translate(req)
    assert cands
    assert any("ă" in cand.text or "â" in cand.text or "î" in cand.text or "ș" in cand.text or "ț" in cand.text for cand in cands)
