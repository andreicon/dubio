from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, requests_per_minute: int):
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self.min_interval = 60.0 / requests_per_minute
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed_at - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.monotonic()
            self._next_allowed_at = now + self.min_interval


def make_rate_limiter(requests_per_minute: int) -> RateLimiter:
    return RateLimiter(requests_per_minute)


_LLM_RATE_LIMITER = RateLimiter(5)


def wait_for_llm_slot() -> None:
    _LLM_RATE_LIMITER.wait()
