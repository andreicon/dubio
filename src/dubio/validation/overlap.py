from dubio.pipeline.timing import find_overlaps
from dubio.validation import CheckResult


def check_overlaps(utterances) -> list[CheckResult]:
    results = []
    for ov in find_overlaps(utterances):
        status = "fail" if ov.seconds > 0.3 else "warning"
        results.append(
            CheckResult(
                name="overlap",
                status=status,
                score=0.0 if status == "fail" else 0.6,
                detail={"a": ov.a_id, "b": ov.b_id, "seconds": ov.seconds},
            )
        )
    return results
