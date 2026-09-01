from dubio.utils.scheduler import run_jobs


def test_failure_isolation_retries_and_failed_item_association():
    calls = {"x": 0}

    def worker(n):
        if n == 3:
            raise ValueError("boom")
        if n == 2:
            calls["x"] += 1
            if calls["x"] < 2:
                raise RuntimeError("transient")
        return n * 10

    report = run_jobs([1, 2, 3, 4], worker, max_workers=2, retries=2)

    assert set(report.succeeded) == {10, 20, 40}
    assert len(report.failed) == 1
    assert report.failed[0][0] == 3
    assert isinstance(report.failed[0][1], ValueError)
    assert calls["x"] == 2
