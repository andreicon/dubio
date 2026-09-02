from __future__ import annotations

import json
import os

from dubio.engines.translation.base import Candidate, Translator
from dubio.engines.translation.duration import estimate_duration
from dubio.engines.translation.rate_limit import RateLimiter, wait_for_llm_slot
from dubio.errors import DubError
from dubio.utils.romanian import assert_diacritics_preserved, has_diacritics


_PROMPT = """You are a professional dubbing translator.
Translate the SOURCE line from {src} to {tgt} for an animated character.
Constraints:
- The spoken translation should fit about {dur:.2f} seconds.
- Preserve meaning and tone. Character context: {ctx}.
- Keep Romanian diacritics (ă â î ș ț) correct.
Previous line: {prev}
Following line: {nxt}
SOURCE: {text}
Return STRICT JSON: {{"candidates":[{{"text":"..."}}, ...]}} with {n} options
ranked from shortest to longest natural phrasing."""


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        if stripped.endswith("```"):
            stripped = stripped.rsplit("```", 1)[0]
    return stripped.strip()


class GeminiTranslator(Translator):
    def __init__(self, model: str | None = None, n_candidates: int = 3, temperature: float = 0.7, rate_limit_per_minute: int | None = None):
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise DubError("ENGINE-004", "Missing GEMINI_API_KEY", {}, "Set GEMINI_API_KEY in your .env or shell")

        self.client = genai.Client(api_key=api_key)
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        self.n = n_candidates
        self.temp = temperature
        self._rate_limiter = RateLimiter(rate_limit_per_minute) if rate_limit_per_minute is not None else None
        self.chat = self.client.chats.create(model=self.model)

    def translate(self, req):
        if self._rate_limiter is None:
            wait_for_llm_slot()
        else:
            self._rate_limiter.wait()
        prompt = _PROMPT.format(
            src=req.source_language,
            tgt=req.target_language,
            dur=req.available_duration,
            ctx=req.character_context or "neutral",
            prev=req.previous_text,
            nxt=req.following_text,
            text=req.source_text,
            n=self.n,
        )
        try:
            resp = self.chat.send_message(prompt, config={"temperature": self.temp})
            raw = _strip_markdown_fence(resp.text or "")
            data = json.loads(raw)
            items = data["candidates"]
            cands = []
            for item in items:
                text = item["text"]
                if req.target_language == "ron" and has_diacritics(req.source_text):
                    assert_diacritics_preserved(req.source_text, text)
                cands.append(Candidate(text, estimate_duration(text)))
        except Exception as e:
            raise DubError(
                "TRANS-001",
                f"Malformed Gemini translation output: {e}",
                {"raw": getattr(locals().get('resp', None), 'text', '')[:200]},
                "Retry or lower temperature",
            )
        if not cands:
            raise DubError("TRANS-002", "No candidates produced", {"text": req.source_text})
        return cands
