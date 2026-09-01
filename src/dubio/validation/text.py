from dubio.utils.similarity import text_similarity
from dubio.validation import CheckResult


def check_text(utt, asr, sim_threshold=0.80) -> CheckResult:
    expected = utt.translation.text
    transcribed = asr.transcribe(utt.tts.file, language="ro").text
    similarity = text_similarity(expected, transcribed)
    status = "pass" if similarity >= sim_threshold else "fail"
    return CheckResult(
        "text",
        status,
        similarity,
        {
            "expected": expected,
            "transcribed": transcribed,
            "similarity": round(similarity, 3),
        },
    )
