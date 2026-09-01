from dubio.pipeline.timing import duration_status, target_duration
from dubio.validation import CheckResult


def check_duration(utt, cfg) -> CheckResult:
    target = target_duration(utt)
    generated = utt.tts.duration or 0.0
    status = duration_status(target, generated, cfg)
    score = {"pass": 1.0, "warning": 0.7, "fail": 0.0}[status]
    return CheckResult(
        name="duration",
        status=status,
        score=score,
        detail={"target": target, "generated": generated, "diff": round(generated - target, 3)},
    )
