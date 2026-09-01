from dubio.pipeline.timing import duration_status, target_duration

_CORRECTION_ORDER = ["speaking_rate", "retranslate", "time_stretch"]


def evaluate_duration(utt, cfg) -> str:
    target = target_duration(utt)
    generated = utt.tts.duration
    if generated is None:
        status = "fail"
        utt.validation.duration = status
        return status
    status = duration_status(target, generated, cfg)

    utt.validation.duration = status
    utt.validation.measurements["duration_diff"] = round(generated - target, 3)
    return status


def next_correction_step(status: str, attempts_done: int) -> str | None:
    if status == "pass":
        return None
    if attempts_done < len(_CORRECTION_ORDER):
        return _CORRECTION_ORDER[attempts_done]
    return None
