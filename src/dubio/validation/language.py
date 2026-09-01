from dubio.validation import CheckResult


def check_language(utt, asr, expected="ro") -> CheckResult:
    path = utt.tts.file
    detected = asr.detect_language(path)
    status = "pass" if detected == expected else "fail"
    return CheckResult(
        "language",
        status,
        1.0 if status == "pass" else 0.0,
        {"expected": expected, "detected": detected},
    )
