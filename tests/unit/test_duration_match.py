from dubio.config import TimingCfg
from dubio.project.manifest import SourceSpan, TTSInfo, Utterance

from dubio.pipeline.duration_match import evaluate_duration, next_correction_step


def test_evaluate_marks_fail_and_records_duration_diff():
    utt = Utterance(
        id="u",
        speaker="s",
        source=SourceSpan(text="x", start=0.0, end=2.80),
    )
    utt.tts = TTSInfo(duration=3.40)

    status = evaluate_duration(utt, TimingCfg())

    assert status == "fail"
    assert utt.validation.duration == "fail"
    assert round(utt.validation.measurements["duration_diff"], 2) == 0.60


def test_evaluate_treats_missing_tts_duration_as_fail():
    utt = Utterance(
        id="u",
        speaker="s",
        source=SourceSpan(text="x", start=0.0, end=2.80),
    )

    status = evaluate_duration(utt, TimingCfg())

    assert status == "fail"
    assert utt.validation.duration == "fail"
    assert "duration_diff" not in utt.validation.measurements


def test_next_correction_step_uses_brief_order():
    assert next_correction_step("fail", 0) == "speaking_rate"
    assert next_correction_step("warning", 1) == "retranslate"
    assert next_correction_step("fail", 2) == "time_stretch"
    assert next_correction_step("fail", 3) is None
    assert next_correction_step("pass", 0) is None
