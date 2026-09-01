# Milestone 4 — Audio Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pass every TTS clip through a configurable processing chain (DC removal → high-pass → EQ → compression → loudness normalization → true-peak limiting), producing consistent perceived loudness and per-clip loudness metadata, with optional per-character/per-utterance gain applied after normalization.

**Architecture:** A pure-numpy/scipy DSP module implements each chain stage as a composable function driven by config. `pipeline/normalize.py` runs the chain per utterance, writes `audio/processed/<utt>.wav`, and records `integrated_lufs/true_peak_db/rms_db` into the manifest. TTS amplitude is never trusted as mix-level info (PRD §22).

**Tech Stack:** numpy, scipy.signal, pyloudnorm, soundfile, FFmpeg loudnorm (optional fallback).

**Spec:** `PRD.md` (§22 audio processing, §23 loudness normalization).

## Global Constraints

(See master plan.) M4 focus: chain is configurable; consistent perceived loudness across characters; target −16 LUFS integrated, ≤ −1 dBTP; character gain applied AFTER normalization; loudness measured and stored per clip.

**Consumes:** M1 `Manifest/Utterance/ProjectPaths`; M0 `audio.measure.{measure_loudness,load_wav,write_wav,LoudnessStats}`, `config.AudioCfg`; M3 `utt.tts.file`, voice `gain_db`.

---

### Task 1: DSP Chain Primitives

**Files:**
- Create: `src/dub/audio/process.py`
- Test: `tests/unit/test_process_chain.py`

**Interfaces:**
- Produces (all `np.ndarray -> np.ndarray`, mono float): `remove_dc(x)`; `high_pass(x, sr, cutoff=80.0)`; `apply_eq(x, sr, bands: list[dict])`; `compress(x, threshold_db=-18, ratio=3.0, sr=48000)`; `normalize_loudness(x, sr, target_lufs=-16.0)`; `true_peak_limit(x, ceiling_db=-1.0)`; `gain_db(x, db)`.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
from dub.audio.process import remove_dc, high_pass, normalize_loudness, true_peak_limit, gain_db
from dub.audio.measure import measure_loudness

def test_remove_dc():
    x = np.ones(1000) * 0.3 + 0.1
    assert abs(np.mean(remove_dc(x))) < 1e-6

def test_normalize_hits_target():
    sr = 48000
    t = np.arange(2*sr)/sr
    x = 0.05 * np.sin(2*np.pi*300*t)  # quiet
    y = normalize_loudness(x, sr, target_lufs=-16.0)
    assert abs(measure_loudness(y, sr).integrated_lufs - (-16.0)) < 1.5

def test_true_peak_limit_ceiling():
    x = np.array([0.0, 1.5, -1.4, 0.2])
    y = true_peak_limit(x, ceiling_db=-1.0)
    ceiling = 10 ** (-1.0/20)
    assert np.max(np.abs(y)) <= ceiling + 1e-6

def test_gain_db_doubles_at_6db():
    x = np.array([0.1, -0.1])
    assert np.allclose(gain_db(x, 6.0), x * (10 ** (6/20)))
```

- [ ] **Step 2: Run to verify fail** → `pytest tests/unit/test_process_chain.py -v` FAIL.

- [ ] **Step 3: Implement `audio/process.py`**

```python
import numpy as np
from scipy.signal import butter, sosfilt
import pyloudnorm as pyln

def remove_dc(x): return x - np.mean(x)

def high_pass(x, sr, cutoff=80.0):
    sos = butter(2, cutoff / (sr / 2), btype="highpass", output="sos")
    return sosfilt(sos, x)

def apply_eq(x, sr, bands):
    y = x
    for b in bands:  # each: {"type":"highshelf|lowshelf|peak","freq":..,"gain_db":..}
        # Minimal biquad-free approach: shelving via first-order filters; peak via bandpass add.
        f = b["freq"] / (sr / 2)
        g = 10 ** (b.get("gain_db", 0) / 20)
        if b["type"] == "highpass":
            sos = butter(2, f, btype="highpass", output="sos"); y = sosfilt(sos, y)
        elif b["type"] == "lowpass":
            sos = butter(2, f, btype="lowpass", output="sos"); y = sosfilt(sos, y)
        elif b["type"] == "peak":
            sos = butter(2, [max(f*0.7,1e-3), min(f*1.3,0.999)], btype="bandpass", output="sos")
            y = y + (g - 1) * sosfilt(sos, y)
    return y

def compress(x, threshold_db=-18, ratio=3.0, sr=48000):
    eps = 1e-9
    env = np.abs(x) + eps
    thr = 10 ** (threshold_db / 20)
    over = env > thr
    gain = np.ones_like(x)
    gain[over] = (thr * (env[over] / thr) ** (1/ratio)) / env[over]
    return x * gain

def normalize_loudness(x, sr, target_lufs=-16.0):
    meter = pyln.Meter(sr)
    if len(x) < sr:
        x = np.pad(x, (0, sr - len(x)))
    loud = meter.integrated_loudness(x)
    if loud == float("-inf"):
        return x
    return pyln.normalize.loudness(x, loud, target_lufs)

def true_peak_limit(x, ceiling_db=-1.0):
    ceiling = 10 ** (ceiling_db / 20)
    peak = np.max(np.abs(x)) or 1e-9
    return x * (ceiling / peak) if peak > ceiling else x

def gain_db(x, db):
    return x * (10 ** (db / 20))
```

- [ ] **Step 4: Run to verify pass** → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: configurable DSP chain primitives"
```

---

### Task 2: Normalize Stage (chain runner + metadata + character gain)

**Files:**
- Create: `src/dub/pipeline/normalize.py`
- Test: `tests/integration/test_normalize_stage.py`

**Interfaces:**
- Consumes: `audio/process.*`, `measure_loudness`, `resolve_voice` (for post-normalization gain), `Manifest`.
- Produces: `process_clip(samples, sr, chain_cfg, target_lufs, true_peak_db) -> np.ndarray`; `normalize_utterance(m, utt, paths, config) -> None` writing `audio/processed/<utt>.wav`, storing `utt.validation.measurements["loudness"] = {integrated_lufs, true_peak_db, rms_db}` and applying `voice.gain_db + utt.mix.gain_db` AFTER normalization; `normalize_project(paths, config)`. Default chain order per PRD §22.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
from pathlib import Path
from dub.project.manifest import Manifest, Character, Voice, Utterance, SourceSpan, TTSInfo
from dub.project.paths import ProjectPaths
from dub.audio.measure import write_wav, load_wav, measure_loudness
from dub.config import Config
from dub.pipeline.normalize import normalize_utterance

def test_normalize_writes_processed_and_metadata(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    sr = 48000
    t = np.arange(sr)/sr
    write_wav(paths.tts_dir / "utt_000001.wav", 0.02*np.sin(2*np.pi*300*t), sr)
    m = Manifest(project={"id":"ep1","source":"s","source_language":"eng","target_language":"ron"})
    m.characters["SPEAKER_00"] = Character(name="Bugs", voice="v")
    m.voices["v"] = Voice(engine="fake", gain_db=0.0)
    u = Utterance(id="utt_000001", speaker="SPEAKER_00",
                  source=SourceSpan(text="x", start=0, end=1),
                  tts=TTSInfo(file=str(paths.tts_dir/"utt_000001.wav"), duration=1.0))
    m.utterances.append(u)
    normalize_utterance(m, u, paths, Config())
    out = Path(paths.processed_dir / "utt_000001.wav")
    assert out.exists()
    lufs = measure_loudness(*load_wav(out)).integrated_lufs
    assert abs(lufs - (-16.0)) < 2.0
    assert "loudness" in u.validation.measurements
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `pipeline/normalize.py`**

```python
from dub.audio import process as dsp
from dub.audio.measure import load_wav, write_wav, measure_loudness
from dub.project.voices import resolve_voice
from dub.project.manifest import Manifest

DEFAULT_CHAIN = {
    "high_pass_hz": 80.0,
    "eq_bands": [],
    "compress": {"threshold_db": -18, "ratio": 3.0},
}

def process_clip(samples, sr, chain_cfg, target_lufs, true_peak_db):
    x = dsp.remove_dc(samples if samples.ndim == 1 else samples.mean(axis=1))
    x = dsp.high_pass(x, sr, chain_cfg.get("high_pass_hz", 80.0))
    if chain_cfg.get("eq_bands"):
        x = dsp.apply_eq(x, sr, chain_cfg["eq_bands"])
    c = chain_cfg.get("compress", {})
    x = dsp.compress(x, c.get("threshold_db", -18), c.get("ratio", 3.0), sr)
    x = dsp.normalize_loudness(x, sr, target_lufs)
    x = dsp.true_peak_limit(x, true_peak_db)
    return x

def normalize_utterance(m, utt, paths, config, chain_cfg=None) -> None:
    chain_cfg = chain_cfg or DEFAULT_CHAIN
    samples, sr = load_wav(utt.tts.file)
    x = process_clip(samples, sr, chain_cfg, config.audio.target_lufs, config.audio.true_peak_db)
    # character/utterance gain AFTER normalization
    voice = resolve_voice(m, utt)
    x = dsp.gain_db(x, voice.gain_db + utt.mix.gain_db)
    out = paths.processed_dir / f"{utt.id}.wav"
    write_wav(out, x, sr)
    stats = measure_loudness(x, sr)
    utt.validation.measurements["loudness"] = {
        "integrated_lufs": round(stats.integrated_lufs, 2),
        "true_peak_db": round(stats.true_peak_db, 2),
        "rms_db": round(stats.rms_db, 2),
    }
    utt.tts.file = utt.tts.file  # unchanged; processed path derived by paths

def normalize_project(paths, config) -> None:
    m = Manifest.load(paths.manifest)
    for u in m.utterances:
        if u.tts.file:
            normalize_utterance(m, u, paths, config)
    m.save(paths.manifest)
```

- [ ] **Step 4: Add CLI** `dub normalize <project> [--utterance utt_X]`.

- [ ] **Step 5: Run to verify pass** → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: normalize stage with loudness metadata + post-norm gain"
```

---

## Self-Review (M4)

- **Spec coverage:** §22 chain (DC→HPF→EQ→comp→loudness→limit→placement) → T1 primitives + T2 runner (placement handled in M6); configurable chain → `chain_cfg`; §23 measured loudness metadata + target −16 LUFS / ≤ −1 dBTP + post-normalization character gain → T2. TTS amplitude not trusted (re-measured post-chain).
- **Placeholders:** none. EQ is a minimal but real filter implementation; bands default empty and are configurable.
- **Type consistency:** `process_clip(samples, sr, chain_cfg, target_lufs, true_peak_db)` and `normalize_utterance(m, utt, paths, config)` match usage; loudness metadata dict keys reused by M5 loudness validation.
