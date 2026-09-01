from __future__ import annotations

import json

from dubio.engines.translation.base import Candidate, Translator
from dubio.engines.translation.duration import estimate_duration
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


class LLMTranslator(Translator):
    def __init__(self, client, model: str, n_candidates: int = 3, temperature: float = 0.7):
        self.client = client
        self.model = model
        self.n = n_candidates
        self.temp = temperature

    def translate(self, req):
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
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temp,
        )
        raw = resp.choices[0].message.content
        try:
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
                f"Malformed LLM translation output: {e}",
                {"raw": raw[:200]},
                "Retry or lower temperature",
            )
        if not cands:
            raise DubError("TRANS-002", "No candidates produced", {"text": req.source_text})
        return cands
