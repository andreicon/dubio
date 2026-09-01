from dubio.validation import CheckResult


DEFAULT_WEIGHTS = {
    "language": 0.25,
    "text": 0.25,
    "duration": 0.2,
    "loudness": 0.15,
    "peak": 0.1,
    "overlap": 0.05,
}


def composite_score(results: list[CheckResult], weights: dict | None) -> tuple[int, dict]:
    weights = weights or DEFAULT_WEIGHTS
    raw = {result.name: result.score for result in results}
    total_weight = sum(weights.get(result.name, 0.0) for result in results) or 1.0
    weighted_score = sum(weights.get(result.name, 0.0) * result.score for result in results)
    return round(100 * weighted_score / total_weight), raw
