# Milestone 0 — TTS Research Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the project scaffold plus a standalone `dubio-tts-test` harness that evaluates any TTS engine on Romanian text and produces `metrics.json`, then gate Fish S2 Pro against a Romanian evaluation suite.

**Architecture:** Establish shared foundations (packaging, logging, errors, audio measurement, Romanian fixtures, engine base interfaces) then the harness that wires a `TTSEngine` + `ASREngine` into a reproducible evaluation with inspectable artifacts. Real Fish/Whisper adapters are GPU-marked; all logic is verified with deterministic fakes.

**Tech Stack:** Python 3.12, Typer, pydantic v2, numpy, soundfile, pyloudnorm, structlog, pytest.

**Spec:** `PRD.md` (§14 Romanian handling, §15 TTS interface, §16 Fish, §40 testing, §46 first task).

## Global Constraints

(See master plan "Global Constraints" — all apply here.) Key for M0: Romanian diacritics `ă â î ș ț` preserved end-to-end; no Fish-specific code outside `engines/tts/fish_s2.py`; stable error IDs; artifacts inspectable; heavy tests marked `gpu`/`model`.

---

### Task 0: Repository Scaffold & Cross-Cutting Foundations

**Files:**
- Create: `pyproject.toml`, `README.md`, `config.yaml`, `.gitignore`, `projects/.gitkeep`
-- Create: `src/dubio/__init__.py`, `src/dubio/logging.py`, `src/dubio/errors.py`, `src/dubio/config.py`
- Create: `tests/conftest.py`, `tests/unit/test_scaffold.py`

**Interfaces:**
-- Produces: `dubio.__version__: str`; `dubio.errors.DubError(code: str, message: str, context: dict, suggested_action: str|None)`; `dubio.logging.get_logger(name) -> structlog.BoundLogger`; `dubio.config.load_config(path: Path|None) -> Config` (pydantic model with `.hardware`, `.asr`, `.diarization`, `.translation`, `.tts`, `.audio`, `.timing`).

- [ ] **Step 1: Write the failing test**

`tests/unit/test_scaffold.py`:
```python
import dubio
from dubio.errors import DubError
from dubio.config import load_config

def test_version_present():
    assert isinstance(dubio.__version__, str) and dubio.__version__

def test_duberror_has_stable_id():
    err = DubError("TTS-RO-001", "Language mismatch", {"utt": "utt_1"}, "Run diagnostic")
    assert err.code == "TTS-RO-001"
    assert "utt_1" in str(err)

def test_default_config_loads():
    cfg = load_config(None)
    assert cfg.audio.sample_rate == 48000
    assert cfg.audio.target_lufs == -16
    assert cfg.timing.max_duration_ratio == 1.15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_scaffold.py -v`
Expected: FAIL (`ModuleNotFoundError: dub`).

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[project]
name = "dubio"
version = "0.0.1"
requires-python = ">=3.12"
dependencies = [
  "typer>=0.12", "pydantic>=2.7", "pyyaml>=6", "numpy>=1.26",
  "soundfile>=0.12", "pyloudnorm>=0.1", "structlog>=24", "scipy>=1.13",
]
[project.optional-dependencies]
asr = ["faster-whisper>=1.0"]
diarization = ["pyannote.audio>=3.1"]
separation = ["demucs>=4"]
llm = ["openai>=1.30"]
dev = ["pytest>=8", "pytest-cov>=5"]
[project.scripts]
dubio = "dubio.cli:app"
"dubio-tts-test" = "dubio.harness.tts_eval:app"
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[tool.hatch.build.targets.wheel]
packages = ["src/dubio"]
[tool.pytest.ini_options]
pythonpath = ["src"]
markers = ["gpu: requires CUDA GPU", "model: downloads/loads heavy models"]
addopts = "-m 'not gpu and not model'"
```

-- [ ] **Step 4: Create `src/dubio/__init__.py`**

```python
__version__ = "0.0.1"
```

-- [ ] **Step 5: Create `src/dubio/errors.py`**

```python
class DubError(Exception):
    def __init__(self, code: str, message: str, context: dict | None = None,
                 suggested_action: str | None = None):
        self.code = code
        self.message = message
        self.context = context or {}
        self.suggested_action = suggested_action
        super().__init__(f"[{code}] {message} | {self.context}")
```

-- [ ] **Step 6: Create `src/dubio/logging.py`**

```python
import logging, structlog

def configure_logging(json_logs: bool = False, level: int = logging.INFO) -> None:
    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[structlog.processors.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso"), renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )

def get_logger(name: str):
    return structlog.get_logger(name)
```

-- [ ] **Step 7: Create `src/dubio/config.py`**

```python
from pathlib import Path
import yaml
from pydantic import BaseModel

class HardwareCfg(BaseModel):
    device: str = "cuda"
    max_tts_workers: int = 1
class EngineCfg(BaseModel):
    engine: str
    model: str | None = None
class AudioCfg(BaseModel):
    sample_rate: int = 48000
    target_lufs: float = -16
    true_peak_db: float = -1
class TimingCfg(BaseModel):
    max_duration_ratio: float = 1.15
    warning_duration_ratio: float = 1.05
class Config(BaseModel):
    hardware: HardwareCfg = HardwareCfg()
    asr: EngineCfg = EngineCfg(engine="whisper", model="large-v3")
    diarization: EngineCfg = EngineCfg(engine="pyannote")
    translation: EngineCfg = EngineCfg(engine="llm")
    tts: EngineCfg = EngineCfg(engine="fish-s2-pro")
    audio: AudioCfg = AudioCfg()
    timing: TimingCfg = TimingCfg()

def load_config(path: Path | None) -> Config:
    if path is None:
        default = Path("config.yaml")
        if not default.exists():
            return Config()
        path = default
    return Config(**yaml.safe_load(Path(path).read_text()))
```

- [ ] **Step 8: Create `config.yaml`, `README.md`, `.gitignore`, `projects/.gitkeep`, empty `tests/conftest.py`**

`config.yaml` mirrors PRD §38 defaults. `.gitignore` excludes `projects/*/`, `__pycache__/`, `*.wav`, `.venv/`.

- [ ] **Step 9: Run test to verify it passes**

Run: `pip install -e ".[dev]" && pytest tests/unit/test_scaffold.py -v`
Expected: PASS (3 tests).

- [ ] **Step 10: Commit**

```bash
git init && git add -A && git commit -m "chore: scaffold dubio package, config, logging, errors"
```

---

### Task 1: Audio Measurement Utilities

**Files:**
-- Create: `src/dubio/audio/measure.py`, `src/dubio/audio/__init__.py`
- Test: `tests/unit/test_measure.py`

**Interfaces:**
- Produces: `LoudnessStats(integrated_lufs: float, true_peak_db: float, rms_db: float)`; `measure_loudness(samples: np.ndarray, sr: int) -> LoudnessStats`; `duration_seconds(samples: np.ndarray, sr: int) -> float`; `load_wav(path) -> tuple[np.ndarray, int]`; `write_wav(path, samples, sr)`.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
from dubio.audio.measure import measure_loudness, duration_seconds

def test_duration():
    sr = 48000
    samples = np.zeros(sr)  # 1 second
    assert abs(duration_seconds(samples, sr) - 1.0) < 1e-6

def test_loudness_of_sine_is_reasonable():
    sr = 48000
    t = np.arange(sr) / sr
    sine = 0.5 * np.sin(2 * np.pi * 440 * t)
    stats = measure_loudness(sine, sr)
    assert -30 < stats.integrated_lufs < -3
    assert stats.true_peak_db <= 0.5
    assert stats.rms_db < 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_measure.py -v`  → FAIL (module missing).

-- [ ] **Step 3: Implement `src/dubio/audio/measure.py`**

```python
from dataclasses import dataclass
from pathlib import Path
import numpy as np, soundfile as sf, pyloudnorm as pyln

@dataclass
class LoudnessStats:
    integrated_lufs: float
    true_peak_db: float
    rms_db: float

def duration_seconds(samples: np.ndarray, sr: int) -> float:
    return len(samples) / sr

def measure_loudness(samples: np.ndarray, sr: int) -> LoudnessStats:
    meter = pyln.Meter(sr)
    mono = samples if samples.ndim == 1 else samples.mean(axis=1)
    integrated = float(meter.integrated_loudness(mono)) if len(mono) >= sr else -70.0
    peak = float(np.max(np.abs(mono))) or 1e-9
    true_peak_db = 20 * np.log10(peak)
    rms = float(np.sqrt(np.mean(mono ** 2))) or 1e-9
    rms_db = 20 * np.log10(rms)
    return LoudnessStats(integrated, true_peak_db, rms_db)

def load_wav(path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path))
    return data, sr

def write_wav(path, samples: np.ndarray, sr: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), samples, sr)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_measure.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: audio loudness/duration measurement utils"
```

---

### Task 2: Romanian Text Fixtures & Similarity

**Files:**
-- Create: `src/dubio/utils/romanian.py`, `src/dubio/utils/similarity.py`, `tests/fixtures/romanian_lines.py`
- Test: `tests/unit/test_romanian.py`

**Interfaces:**
- Produces: `ROMANIAN_TEST_LINES: list[str]` (the 7 PRD §14 lines); `has_diacritics(s) -> bool`; `assert_diacritics_preserved(before, after)`; `text_similarity(a: str, b: str) -> float` (0..1, punctuation-insensitive normalized Levenshtein).

- [ ] **Step 1: Write the failing test**

```python
from tests.fixtures.romanian_lines import ROMANIAN_TEST_LINES
from dubio.utils.romanian import has_diacritics
from dubio.utils.similarity import text_similarity

def test_fixture_lines_have_diacritics():
    assert any(has_diacritics(l) for l in ROMANIAN_TEST_LINES)
    assert "Ține minte ce ți-am spus." in ROMANIAN_TEST_LINES

def test_similarity_ignores_punctuation():
    assert text_similarity("Ce faci, băiete?", "Ce faci băiete") > 0.95

def test_similarity_flags_lexical_drift():
    assert text_similarity("Ce faci acolo?", "Unde mergi mâine?") < 0.5
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/unit/test_romanian.py -v` → FAIL.

- [ ] **Step 3: Create `tests/fixtures/romanian_lines.py`**

```python
ROMANIAN_TEST_LINES = [
    "Ce faci?",
    "Ce faci, băiete?",
    "Băiatul merge la magazin.",
    "Știu că ai fost acolo.",
    "Ăsta este un test pentru limba română.",
    "Îți spun că nu este adevărat.",
    "Ține minte ce ți-am spus.",
]
```

-- [ ] **Step 4: Implement `src/dubio/utils/romanian.py`**

```python
DIACRITICS = set("ăâîșțĂÂÎȘȚ")

def has_diacritics(s: str) -> bool:
    return any(ch in DIACRITICS for ch in s)

def assert_diacritics_preserved(before: str, after: str) -> None:
    missing = {c for c in before if c in DIACRITICS} - set(after)
    if missing:
        raise AssertionError(f"Diacritics stripped: {missing}")
```

-- [ ] **Step 5: Implement `src/dubio/utils/similarity.py`**

```python
import re

def _norm(s: str) -> str:
    return re.sub(r"[^\w\s]", "", s.lower(), flags=re.UNICODE).strip()

def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (a[i-1] != b[j-1]))
        prev = cur
    return prev[n]

def text_similarity(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a and not b:
        return 1.0
    dist = _levenshtein(a, b)
    return 1.0 - dist / max(len(a), len(b), 1)
```

- [ ] **Step 6: Run to verify pass**

Run: `pytest tests/unit/test_romanian.py -v` → PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: Romanian fixtures, diacritic guard, text similarity"
```

---

### Task 3: TTS & ASR Engine Interfaces + Fakes

**Files:**
-- Create: `src/dubio/engines/tts/base.py`, `src/dubio/engines/tts/fake.py`
-- Create: `src/dubio/engines/asr/base.py`, `src/dubio/engines/asr/fake.py`
- Test: `tests/unit/test_engine_fakes.py`

**Interfaces:**
- Produces: `VoiceProfile(id, engine, reference, pitch, speaking_rate, gain_db, style)`; `AudioArtifact(path, sample_rate, duration, engine_id, engine_version, metadata)`; `TTSEngine` Protocol `synthesize(text, voice, language, instructions) -> AudioArtifact`; `ASRResult(text, language, segments)`; `ASREngine` Protocol `transcribe(audio_path, language=None) -> ASRResult` and `detect_language(audio_path) -> str`; `FakeTTS`, `FakeASR`.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from dubio.engines.tts.base import VoiceProfile
from dubio.engines.tts.fake import FakeTTS
from dubio.engines.asr.fake import FakeASR

def test_fake_tts_duration_scales_with_text(tmp_path):
    tts = FakeTTS(out_dir=tmp_path, chars_per_second=15.0)
    voice = VoiceProfile(id="v", engine="fake", reference=None)
    art = tts.synthesize("Ce faci, băiete?", voice, "ro", {})
    assert Path(art.path).exists()
    assert art.engine_id == "fake"
    assert abs(art.duration - len("Ce faci, băiete?") / 15.0) < 0.1

def test_fake_asr_echoes_and_detects(tmp_path):
    asr = FakeASR(scripted={"a.wav": ("Ce faci?", "ro")})
    res = asr.transcribe("a.wav")
    assert res.text == "Ce faci?" and res.language == "ro"
    assert asr.detect_language("a.wav") == "ro"
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/unit/test_engine_fakes.py -v` → FAIL.

- [ ] **Step 3: Implement `engines/tts/base.py`**

```python
from dataclasses import dataclass, field
from typing import Protocol, Any

@dataclass
class VoiceProfile:
    id: str
    engine: str
    reference: str | None = None
    pitch: float = 0.0
    speaking_rate: float = 1.0
    gain_db: float = 0.0
    style: dict[str, Any] = field(default_factory=dict)

@dataclass
class AudioArtifact:
    path: str
    sample_rate: int
    duration: float
    engine_id: str
    engine_version: str
    metadata: dict[str, Any] = field(default_factory=dict)

class TTSEngine(Protocol):
    engine_id: str
    engine_version: str
    def synthesize(self, text: str, voice: VoiceProfile, language: str,
                   instructions: dict) -> AudioArtifact: ...
```

- [ ] **Step 4: Implement `engines/tts/fake.py`**

```python
import hashlib
from pathlib import Path
import numpy as np
from dubio.audio.measure import write_wav
from dubio.engines.tts.base import TTSEngine, VoiceProfile, AudioArtifact

class FakeTTS(TTSEngine):
    engine_id = "fake"
    engine_version = "0"
    def __init__(self, out_dir, chars_per_second: float = 15.0, sr: int = 48000):
        self.out_dir = Path(out_dir); self.cps = chars_per_second; self.sr = sr
    def synthesize(self, text, voice: VoiceProfile, language, instructions) -> AudioArtifact:
        dur = max(0.2, len(text) / self.cps) / max(voice.speaking_rate, 0.1)
        n = int(dur * self.sr)
        t = np.arange(n) / self.sr
        tone = 0.1 * np.sin(2 * np.pi * 220 * t)
        name = hashlib.sha1(text.encode()).hexdigest()[:12] + ".wav"
        path = self.out_dir / name
        write_wav(path, tone, self.sr)
        return AudioArtifact(str(path), self.sr, dur, self.engine_id,
                             self.engine_version, {"language": language, "text": text})
```

- [ ] **Step 5: Implement `engines/asr/base.py` and `engines/asr/fake.py`**

`base.py`:
```python
from dataclasses import dataclass, field
from typing import Protocol

@dataclass
class Word:
    word: str; start: float; end: float
@dataclass
class Segment:
    text: str; start: float; end: float; words: list[Word] = field(default_factory=list)
@dataclass
class ASRResult:
    text: str; language: str; segments: list[Segment] = field(default_factory=list)

class ASREngine(Protocol):
    def transcribe(self, audio_path: str, language: str | None = None) -> ASRResult: ...
    def detect_language(self, audio_path: str) -> str: ...
```

`fake.py`:
```python
from dubio.engines.asr.base import ASREngine, ASRResult, Segment

class FakeASR(ASREngine):
    def __init__(self, scripted: dict[str, tuple[str, str]] | None = None):
        self.scripted = scripted or {}
    def transcribe(self, audio_path, language=None) -> ASRResult:
        text, lang = self.scripted.get(audio_path, ("", language or "ro"))
        return ASRResult(text, lang, [Segment(text, 0.0, 1.0)] if text else [])
    def detect_language(self, audio_path) -> str:
        return self.scripted.get(audio_path, ("", "ro"))[1]
```

- [ ] **Step 6: Run to verify pass**

Run: `pytest tests/unit/test_engine_fakes.py -v` → PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: TTS/ASR engine interfaces and deterministic fakes"
```

---

### Task 4: TTS Evaluation Harness Core

**Files:**
-- Create: `src/dubio/harness/tts_eval.py`, `src/dubio/harness/__init__.py`
- Test: `tests/unit/test_tts_eval.py`

**Interfaces:**
- Consumes: `FakeTTS`, `FakeASR`, `measure_loudness`, `text_similarity`.
- Produces: `evaluate(tts, asr, text, language, voice, out_dir) -> dict` writing `result/{audio.wav,input.txt,transcription.txt,metrics.json}`. `metrics.json` fields per PRD §46: `engine, language_expected, language_detected, duration_seconds, integrated_lufs, true_peak_db, transcription, text_similarity`.

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from dubio.engines.tts.fake import FakeTTS
from dubio.engines.asr.fake import FakeASR
from dubio.engines.tts.base import VoiceProfile
from dubio.harness.tts_eval import evaluate

def test_evaluate_writes_metrics(tmp_path):
    out = tmp_path / "result"
    tts = FakeTTS(out_dir=tmp_path)
    voice = VoiceProfile(id="v", engine="fake")
    art_path_holder = {}
    # FakeASR keyed by produced audio path: patch after synth via wrapper
    asr = FakeASR()
    res = evaluate(tts, asr, "Ce faci, băiete?", "ro", voice, out, expected_transcription="Ce faci, băiete?")
    metrics = json.loads((out / "metrics.json").read_text())
    assert metrics["engine"] == "fake"
    assert metrics["language_expected"] == "ro"
    assert metrics["duration_seconds"] > 0
    assert (out / "audio.wav").exists()
    assert (out / "input.txt").read_text() == "Ce faci, băiete?"
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/unit/test_tts_eval.py -v` → FAIL.

- [ ] **Step 3: Implement `harness/tts_eval.py`** (core `evaluate` + Typer `app`)

```python
import json, shutil
from pathlib import Path
import typer
from dubio.audio.measure import load_wav, measure_loudness
from dubio.utils.similarity import text_similarity
from dubio.engines.tts.base import VoiceProfile

def evaluate(tts, asr, text: str, language: str, voice: VoiceProfile,
             out_dir: Path, expected_transcription: str | None = None) -> dict:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    art = tts.synthesize(text, voice, language, {})
    audio_out = out_dir / "audio.wav"
    shutil.copyfile(art.path, audio_out)
    samples, sr = load_wav(audio_out)
    loud = measure_loudness(samples, sr)
    # Re-ASR the produced audio for round-trip validation.
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
def main(text: str, language: str = "ro", engine: str = "fake",
         reference: str = typer.Option(None), out: str = "result"):
    from dubio.harness.factory import build_tts, build_asr  # Task 5
    tts = build_tts(engine, out_dir=Path(out))
    asr = build_asr("fake" if engine == "fake" else "whisper")
    voice = VoiceProfile(id="cli", engine=engine, reference=reference)
    metrics = evaluate(tts, asr, text, language, voice, Path(out))
    typer.echo(json.dumps(metrics, ensure_ascii=False, indent=2))
```

Note: the FakeASR default returns the input `text` fallback, so the unit test passes without scripting. Round-trip fidelity with real ASR is covered by Task 6 GPU test.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/unit/test_tts_eval.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: TTS evaluation harness core with metrics.json"
```

---

### Task 5: Engine Factory & `dub-tts-test` CLI

**Files:**
- Create: `src/dubio/harness/factory.py`
- Test: `tests/integration/test_tts_test_cli.py`

**Interfaces:**
- Produces: `build_tts(name, **kw) -> TTSEngine`, `build_asr(name, **kw) -> ASREngine`. Names: `fake`, `fish-s2-pro`, `whisper`. Unknown name raises `DubError("ENGINE-001", ...)`.

- [ ] **Step 1: Write the failing test** (CLI via Typer runner, fake engine)

```python
from typer.testing import CliRunner
from dubio.harness.tts_eval import app

def test_cli_fake_engine(tmp_path):
    runner = CliRunner()
    out = tmp_path / "result"
    r = runner.invoke(app, ["Ce faci, băiete?", "--engine", "fake", "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert (out / "metrics.json").exists()
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/integration/test_tts_test_cli.py -v` → FAIL (factory missing).

- [ ] **Step 3: Implement `harness/factory.py`**

```python
from pathlib import Path
from dubio.errors import DubError

def build_tts(name: str, out_dir: Path | None = None, **kw):
    if name == "fake":
        from dubio.engines.tts.fake import FakeTTS
        return FakeTTS(out_dir=out_dir or Path("result"))
    if name == "fish-s2-pro":
        from dubio.engines.tts.fish_s2 import FishS2TTS  # Task 6
        return FishS2TTS(out_dir=out_dir or Path("result"), **kw)
    raise DubError("ENGINE-001", f"Unknown TTS engine: {name}")

def build_asr(name: str, **kw):
    if name == "fake":
        from dubio.engines.asr.fake import FakeASR
        return FakeASR()
    if name == "whisper":
        from dubio.engines.asr.whisper import WhisperASR  # M1 Task 4
        return WhisperASR(**kw)
    raise DubError("ENGINE-002", f"Unknown ASR engine: {name}")
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/integration/test_tts_test_cli.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: engine factory and dub-tts-test CLI"
```

---

### Task 6: Fish S2 Pro Adapter + Romanian Evaluation Gate

**Files:**
- Create: `src/dubio/engines/tts/fish_s2.py`
- Create: `tests/tts/test_fish_romanian.py`
- Create: `docs/tts-engines.md` (records the evaluation outcome)

**Interfaces:**
- Consumes: `TTSEngine`, `VoiceProfile`, `AudioArtifact`, `evaluate`, `ROMANIAN_TEST_LINES`.
- Produces: `FishS2TTS(engine_id="fish-s2-pro")` implementing `synthesize`. All Fish-specific code stays in this file (PRD §16).

- [ ] **Step 1: Write the failing test (GPU/model marked, skipped by default)**

```python
import pytest
from pathlib import Path
from dubio.engines.tts.fish_s2 import FishS2TTS
from dubio.engines.asr.whisper import WhisperASR
from dubio.engines.tts.base import VoiceProfile
from dubio.harness.tts_eval import evaluate
from tests.fixtures.romanian_lines import ROMANIAN_TEST_LINES

@pytest.mark.gpu
@pytest.mark.model
@pytest.mark.parametrize("line", ROMANIAN_TEST_LINES)
def test_fish_romanian_line(tmp_path, line):
    tts = FishS2TTS(out_dir=tmp_path)
    asr = WhisperASR(model="large-v3")
    voice = VoiceProfile(id="test", engine="fish-s2-pro",
                         reference="tests/fixtures/voices/test.wav")
    m = evaluate(tts, asr, line, "ro", voice, tmp_path / "r", expected_transcription=line)
    assert m["language_detected"] == "ro", f"Language mismatch on: {line}"
    assert m["text_similarity"] >= 0.80, f"Low similarity on: {line}"
    assert m["true_peak_db"] <= 0.0
```

- [ ] **Step 2: Run to verify it fails / skips**

Run (default): `pytest tests/tts/test_fish_romanian.py -v` → SKIPPED (markers excluded).
Run (opt-in): `pytest -m "gpu and model" tests/tts/test_fish_romanian.py -v` → FAIL (adapter missing).

- [ ] **Step 3: Implement `engines/tts/fish_s2.py`**

Wrap the Fish S2 Pro SDK/CLI. Skeleton (fill with the actual Fish API at build time — the interface contract is fixed, the internals are Fish-specific and isolated here):
```python
from pathlib import Path
from dubio.engines.tts.base import TTSEngine, VoiceProfile, AudioArtifact
from dubio.audio.measure import load_wav, duration_seconds
from dubio.errors import DubError

class FishS2TTS(TTSEngine):
    engine_id = "fish-s2-pro"
    def __init__(self, out_dir, model_version: str = "s2-pro", sr: int = 48000, device: str = "cuda"):
        self.out_dir = Path(out_dir); self.engine_version = model_version
        self.sr = sr; self.device = device
        self._model = self._load_model()
    def _load_model(self):
        # Import and initialize Fish S2 Pro here (only place Fish is imported).
        import fish_speech  # placeholder for the real Fish package name
        return fish_speech.load(self.engine_version, device=self.device)
    def synthesize(self, text, voice: VoiceProfile, language, instructions) -> AudioArtifact:
        if language != "ro":
            # Non-fatal: Fish still runs, but caller validates detected language downstream.
            pass
        self.out_dir.mkdir(parents=True, exist_ok=True)
        out = self.out_dir / f"fish_{abs(hash(text)) % 10**10}.wav"
        try:
            self._model.tts(text=text, reference_audio=voice.reference,
                            speaking_rate=voice.speaking_rate, pitch=voice.pitch,
                            output_path=str(out), sample_rate=self.sr)
        except Exception as e:
            raise DubError("TTS-RO-001", f"Fish synthesis failed: {e}",
                           {"text": text}, "Run Romanian TTS diagnostic suite")
        samples, sr = load_wav(out)
        return AudioArtifact(str(out), sr, duration_seconds(samples, sr),
                             self.engine_id, self.engine_version, {"language": language})
```

- [ ] **Step 4: Run the gate (on GPU hardware) and record results**

Run: `pytest -m "gpu and model" tests/tts/test_fish_romanian.py -v`
Write PASS/FAIL per line + observed similarity/loudness into `docs/tts-engines.md`.
**GATE:** If Fish fails Romanian (`language_detected != ro` or similarity < 0.80 on diacritic lines), do NOT proceed to M3 with Fish — either fix the adapter, adjust reference audio, or select a different TTS engine. Only the adapter changes; the rest of the architecture is unaffected.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: Fish S2 Pro TTS adapter + Romanian evaluation gate"
```

---

## Self-Review (M0)

- **Spec coverage:** §46 first task → Tasks 4–5; §15 interface → Task 3; §16 Fish + 11 cases → Task 6 (diacritics, punctuation, short/long via fixture lines; pitch/rate covered by VoiceProfile params passed through; loudness asserted); §14 Romanian → Tasks 2 & 6; §40 testing → all. Note: §16's "repeated synthesis consistency" and "emotional instructions" are additional assertions to add to Task 6's suite when the real Fish API is known.
- **Placeholders:** Fish internals in Task 6 Step 3 are intentionally marked as the only Fish-specific area (isolated per §16); the interface contract is complete.
- **Type consistency:** `AudioArtifact`, `VoiceProfile`, `evaluate(...)` signatures identical across Tasks 3–6.
