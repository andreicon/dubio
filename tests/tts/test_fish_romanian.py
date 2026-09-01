import pytest

from dubio.engines.asr.whisper import WhisperASR
from dubio.engines.tts.base import VoiceProfile
from dubio.engines.tts.fish_s2 import FishS2TTS
from dubio.harness.tts_eval import evaluate
from tests.fixtures.romanian_lines import ROMANIAN_TEST_LINES


@pytest.mark.gpu
@pytest.mark.model
@pytest.mark.parametrize("line", ROMANIAN_TEST_LINES)
def test_fish_romanian_line(tmp_path, line):
    tts = FishS2TTS(out_dir=tmp_path)
    asr = WhisperASR(model="large-v3")
    voice = VoiceProfile(id="test", engine="fish-s2-pro", reference="tests/fixtures/voices/test.wav")
    m = evaluate(tts, asr, line, "ro", voice, tmp_path / "r", expected_transcription=line)
    assert m["language_detected"] == "ro", f"Language mismatch on: {line}"
    assert m["text_similarity"] >= 0.80, f"Low similarity on: {line}"
    assert m["true_peak_db"] <= 0.0
