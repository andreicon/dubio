from __future__ import annotations

from dubio.engines.translation.base import Candidate, Translator
from dubio.engines.translation.duration import estimate_duration


class FakeTranslator(Translator):
    def __init__(self, mapping: dict[str, list[str]] | None = None):
        self.mapping = mapping or {}

    def translate(self, req):
        texts = self.mapping.get(req.source_text, [req.source_text])
        return [Candidate(text, estimate_duration(text)) for text in texts]
