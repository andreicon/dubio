from dubio.validation import CheckResult


def check_loudness(utt, target_lufs, tol=2.0) -> CheckResult:
    loudness = utt.validation.measurements.get("loudness", {})
    lufs = loudness.get("integrated_lufs")
    if lufs is None:
        return CheckResult("loudness", "fail", 0.0, {"reason": "no measurement"})

    diff = abs(lufs - target_lufs)
    if diff <= tol:
        status = "pass"
    elif diff <= 2 * tol:
        status = "warning"
    else:
        status = "fail"

    return CheckResult(
        "loudness",
        status,
        max(0.0, 1.0 - diff / (2 * tol)),
        {"lufs": lufs, "diff": round(diff, 2)},
    )
