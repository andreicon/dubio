from __future__ import annotations

import numpy as np

from dubio.audio import process as dsp
from dubio.audio.measure import load_wav, measure_loudness, write_wav
from dubio.project.manifest import Manifest
from dubio.project.voices import resolve_voice


def _resample_to(samples: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    if source_sr == target_sr:
        return samples
    if len(samples) == 0:
        return samples
    from scipy.signal import resample_poly

    return resample_poly(samples, target_sr, source_sr)

def process_clip(samples, sr, chain_cfg, target_lufs, true_peak_db) -> np.ndarray:
    x = samples if samples.ndim == 1 else samples.mean(axis=1)
    x = dsp.remove_dc(x)
    x = dsp.high_pass(x, sr, chain_cfg.get("high_pass_hz", 80.0))

    eq_bands = chain_cfg.get("eq_bands") or []
    if eq_bands:
        x = dsp.apply_eq(x, sr, eq_bands)

    compress_cfg = chain_cfg.get("compress") or {}
    x = dsp.compress(
        x,
        threshold_db=compress_cfg.get("threshold_db", -18.0),
        ratio=compress_cfg.get("ratio", 3.0),
        sr=sr,
    )
    x = dsp.normalize_loudness(x, sr, target_lufs)
    x = dsp.true_peak_limit(x, true_peak_db)
    return x


def normalize_utterance(m, utt, paths, config) -> None:
    if not utt.tts.file:
        return

    samples, sr = load_wav(utt.tts.file)
    processed = process_clip(
        samples,
        sr,
        config.audio.normalize_chain,
        config.audio.target_lufs,
        config.audio.true_peak_db,
    )

    processed = _resample_to(processed, sr, config.audio.sample_rate)
    sr = config.audio.sample_rate

    voice_gain_db = resolve_voice(m, utt).gain_db
    total_gain_db = voice_gain_db + utt.mix.gain_db
    if total_gain_db:
        processed = dsp.gain_db(processed, total_gain_db)

    processed = dsp.true_peak_limit(processed, config.audio.true_peak_db)

    out = paths.processed_dir / f"{utt.id}.wav"
    write_wav(out, processed, sr)

    written_samples, written_sr = load_wav(out)
    stats = measure_loudness(written_samples, written_sr)
    utt.validation.measurements["loudness"] = {
        "integrated_lufs": round(stats.integrated_lufs, 2),
        "true_peak_db": round(stats.true_peak_db, 2),
        "rms_db": round(stats.rms_db, 2),
    }


def normalize_project(paths, config) -> None:
    manifest = Manifest.load(paths.manifest)
    for utt in manifest.utterances:
        normalize_utterance(manifest, utt, paths, config)
    manifest.save(paths.manifest)
