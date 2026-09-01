import json

from dubio.audio.measure import load_wav
from dubio.engines.asr.fake import FakeASR
from dubio.engines.tts.base import VoiceProfile
from dubio.engines.tts.fake import FakeTTS
from dubio.harness.tts_eval import evaluate


def test_evaluate_writes_metrics(tmp_path):
    out = tmp_path / "result"
    tts = FakeTTS(out_dir=tmp_path)
    voice = VoiceProfile(id="v", engine="fake")
    asr = FakeASR()
    evaluate(tts, asr, "Ce faci, băiete?", "ro", voice, out, expected_transcription="Ce faci, băiete?")
    metrics = json.loads((out / "metrics.json").read_text())
    assert metrics["engine"] == "fake"
    assert metrics["language_expected"] == "ro"
    assert metrics["duration_seconds"] > 0
    assert (out / "audio.wav").exists()
    assert (out / "input.txt").read_text() == "Ce faci, băiete?"
