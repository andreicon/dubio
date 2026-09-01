import json
import shutil
from pathlib import Path

import typer

from dubio.audio.measure import load_wav, measure_loudness
from dubio.engines.tts.base import VoiceProfile
from dubio.utils.similarity import text_similarity


def evaluate(tts, asr, text: str, language: str, voice: VoiceProfile, out_dir: Path, expected_transcription: str | None = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    art = tts.synthesize(text, voice, language, {})
    audio_out = out_dir / "audio.wav"
    shutil.copyfile(art.path, audio_out)
    samples, sr = load_wav(audio_out)
    loud = measure_loudness(samples, sr)
    transcription = asr.transcribe(str(audio_out), language=language).text or text
    detected = asr.detect_language(str(audio_out)) if hasattr(asr, "detect_language") else language
    expected = expected_transcription or text
    metrics = {
        "engine": art.engine_id,
        "engine_version": art.engine_version,
        "language_expected": language,
        "language_detected": detected,
        "duration_seconds": round(art.duration, 3),
        "integrated_lufs": round(loud.integrated_lufs, 2),
        "true_peak_db": round(loud.true_peak_db, 2),
        "rms_db": round(loud.rms_db, 2),
        "transcription": transcription,
        "text_similarity": round(text_similarity(expected, transcription), 3),
    }
    (out_dir / "input.txt").write_text(text)
    (out_dir / "transcription.txt").write_text(transcription)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


app = typer.Typer(help="TTS evaluation harness")


@app.command()
def main(text: str, language: str = "ro", engine: str = "fake", reference: str = typer.Option(None), out: str = "result"):
    from dubio.harness.factory import build_asr, build_tts

    tts = build_tts(engine, out_dir=Path(out))
    asr = build_asr("fake" if engine == "fake" else "whisper")
    voice = VoiceProfile(id="cli", engine=engine, reference=reference)
    metrics = evaluate(tts, asr, text, language, voice, Path(out))
    typer.echo(json.dumps(metrics, ensure_ascii=False, indent=2))
