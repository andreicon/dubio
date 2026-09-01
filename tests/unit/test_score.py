from dubio.validation import CheckResult
from dubio.validation.score import composite_score


def test_composite_score_returns_bounded_integer_and_raw_map():
    results = [
        CheckResult("language", "pass", 1.0),
        CheckResult("text", "pass", 0.97),
        CheckResult("duration", "warning", 0.7),
        CheckResult("loudness", "pass", 1.0),
    ]

    score, raw = composite_score(results, weights=None)

    assert 0 <= score <= 100
    assert raw["text"] == 0.97


def test_composite_score_penalizes_language_fail():
    results = [
        CheckResult("language", "pass", 1.0),
        CheckResult("text", "pass", 0.97),
        CheckResult("duration", "warning", 0.7),
        CheckResult("loudness", "pass", 1.0),
    ]
    score_ok, _ = composite_score(results, weights=None)

    fail = [CheckResult("language", "fail", 0.0)] + results[1:]
    score_fail, _ = composite_score(fail, weights=None)

    assert score_fail < score_ok
