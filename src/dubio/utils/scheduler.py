from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


@dataclass
class SchedulerReport:
    succeeded: list = field(default_factory=list)
    failed: list = field(default_factory=list)


def _attempt(item, worker_fn, retries: int):
    last_error = None
    for _ in range(retries + 1):
        try:
            return True, worker_fn(item)
        except Exception as exc:  # noqa: BLE001 - isolation is intentional
            last_error = exc
    return False, last_error


def run_jobs(items, worker_fn, max_workers, retries: int = 2) -> SchedulerReport:
    report = SchedulerReport()
    items = list(items)
    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as executor:
        futures = [executor.submit(_attempt, item, worker_fn, retries) for item in items]
        for item, future in zip(items, futures, strict=True):
            ok, result = future.result()
            if ok:
                report.succeeded.append(result)
            else:
                report.failed.append((item, result))
    return report
