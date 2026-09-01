from __future__ import annotations

import re


def estimate_duration(text: str, chars_per_second: float = 14.0) -> float:
    core = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return round(max(0.3, len(core) / chars_per_second), 3)
