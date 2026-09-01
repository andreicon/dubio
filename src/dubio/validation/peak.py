from dubio.validation import CheckResult


def check_peak(utt, ceiling_db=-1.0) -> CheckResult:
    loudness = utt.validation.measurements.get("loudness", {})
    true_peak_db = loudness.get("true_peak_db")
    if true_peak_db is None:
        return CheckResult("peak", "fail", 0.0, {"reason": "no measurement"})

    status = "pass" if true_peak_db <= ceiling_db else "fail"
    return CheckResult("peak", status, 1.0 if status == "pass" else 0.0, {"true_peak_db": true_peak_db})
