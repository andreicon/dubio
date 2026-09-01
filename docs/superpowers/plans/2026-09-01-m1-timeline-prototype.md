# Milestone 1 — Timeline Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `episode.mp4` into an authoritative `manifest.json` with accurate per-utterance timing, speaker IDs, and manual character mapping — no TTS.

**Architecture:** Introduce the pydantic manifest model and project paths, then FFmpeg media extraction, Whisper ASR (behind interface), diarization (behind interface), character mapping, and timeline assembly with overlap primitives. Real Whisper/pyannote are GPU-marked; logic verified with fakes.

**Tech Stack:** FFmpeg, faster-whisper, pyannote.audio, pydantic v2, Typer.

**Spec:** `PRD.md` (§7 data model, §8 extraction, §10 ASR, §11 diarization, §12 character mapping, §20–21 timing/overlap).

## Global Constraints

(See master plan.) M1 focus: manifest is authoritative and diacritic-safe; SPEAKER_xx kept separate from character names; no engine specifics in `pipeline/timing.py`; video stream never re-encoded during extraction.

**Interfaces produced in M0 that M1 consumes:** `dubio.config.load_config`, `dubio.errors.DubError`, `dubio.logging.get_logger`, `dubio.audio.measure.*`, `dubio.engines.asr.base.{ASREngine,ASRResult,Segment,Word}`, `dubio.engines.asr.fake.FakeASR`.

---

### Task 1: Manifest Model & Project Paths

**Files:**
- Create: `src/dubio/project/manifest.py`, `src/dubio/project/paths.py`, `src/dubio/project/__init__.py`
- Test: `tests/unit/test_manifest.py`

**Interfaces:**
- Produces: pydantic models `Project`, `Character`, `Voice`, `SourceSpan`, `Translation`, `TTSInfo`, `MixInfo`, `Validation`, `Utterance`, `Manifest`. `Manifest.load(path) -> Manifest`, `Manifest.save(path)`, `Manifest.get_utterance(id) -> Utterance`. `ProjectPaths(root, project_id)` with `.manifest`, `.audio_dir`, `.tts_dir`, `.processed_dir`, `.mix_dir`, `.validation_dir`, `.output_dir`.

- [ ] **Step 1: Write the failing test**

```python
from dubio.project.manifest import Manifest, Utterance, SourceSpan

def test_manifest_roundtrip_preserves_diacritics(tmp_path):
    m = Manifest(project={"id": "ep1", "source": "s.mp4",
                          "source_language": "eng", "target_language": "ron"})
    m.utterances.append(Utterance(id="utt_000001", speaker="speaker_00",
        source=SourceSpan(text="What are you doing?", start=12.43, end=15.87)))
    m.utterances[0].translation.text = "Ce faci, băiete?"
    p = tmp_path / "manifest.json"
    m.save(p)
    loaded = Manifest.load(p)
    assert loaded.utterances[0].translation.text == "Ce faci, băiete?"
    assert loaded.get_utterance("utt_000001").source.duration == 15.87 - 12.43
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest tests/unit/test_manifest.py -v` → FAIL.

- [ ] **Step 3: Implement `project/manifest.py`** (models mirror PRD §7)

```python
from pathlib import Path
from pydantic import BaseModel, Field, computed_field

class Project(BaseModel):
    id: str; source: str; source_language: str; target_language: str
class Character(BaseModel):
    name: str; voice: str | None = None
class Voice(BaseModel):
    engine: str; reference: str | None = None
    pitch: float = 0; gain_db: float = 0; speaking_rate: float = 1.0
class SourceSpan(BaseModel):
    text: str; start: float; end: float
    words: list[dict] = Field(default_factory=list)
    @computed_field
    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)
class Translation(BaseModel):
    text: str = ""; status: str = "pending"
    candidates: list[dict] = Field(default_factory=list)
class TTSInfo(BaseModel):
    engine: str | None = None; voice: str | None = None
    file: str | None = None; duration: float | None = None
    engine_version: str | None = None
class MixInfo(BaseModel):
    gain_db: float = 0; pan: float = 0
class Validation(BaseModel):
    language: str | None = None; transcription: str | None = None
    duration: str | None = None; loudness: str | None = None
    overlap: str | None = None; score: float | None = None
    measurements: dict = Field(default_factory=dict)
class Utterance(BaseModel):
    id: str; speaker: str
    source: SourceSpan
    translation: Translation = Field(default_factory=Translation)
    tts: TTSInfo = Field(default_factory=TTSInfo)
    mix: MixInfo = Field(default_factory=MixInfo)
    validation: Validation = Field(default_factory=Validation)
    overlap_allowed: bool = False
class Manifest(BaseModel):
    project: Project
    characters: dict[str, Character] = Field(default_factory=dict)
    voices: dict[str, Voice] = Field(default_factory=dict)
    utterances: list[Utterance] = Field(default_factory=list)
    @classmethod
    def load(cls, path) -> "Manifest":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
    def save(self, path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")
    def get_utterance(self, uid: str) -> Utterance:
        for u in self.utterances:
            if u.id == uid:
                return u
        from dubio.errors import DubError
        raise DubError("MANIFEST-001", f"Utterance not found: {uid}")
```

- [ ] **Step 4: Implement `project/paths.py`**

```python
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ProjectPaths:
    root: Path
    project_id: str
    @property
    def base(self) -> Path: return self.root / self.project_id
    @property
    def manifest(self) -> Path: return self.base / "manifest.json"
    @property
    def audio_dir(self) -> Path: return self.base / "audio"
    @property
    def tts_dir(self) -> Path: return self.audio_dir / "tts"
    @property
    def processed_dir(self) -> Path: return self.audio_dir / "processed"
    @property
    def mix_dir(self) -> Path: return self.base / "mix"
    @property
    def validation_dir(self) -> Path: return self.base / "validation"
    @property
    def output_dir(self) -> Path: return self.base / "output"
```

- [ ] **Step 5: Run to verify pass**

Run: `pytest tests/unit/test_manifest.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: pydantic manifest model and project paths"
```

---

### Task 2: `dubio init` and CLI Skeleton

**Files:**
- Create: `src/dubio/cli.py`
- Test: `tests/integration/test_cli_init.py`

**Interfaces:**
- Produces: Typer `app` with `dubio init <project> --source <path> [--source-lang eng --target-lang ron]` creating project dir + minimal manifest. Later tasks/milestones add subcommands (`extract`, `transcribe`, …).

- [ ] **Step 1: Write the failing test**

```python
from typer.testing import CliRunner
from dubio.cli import app
from dubio.project.manifest import Manifest

def test_init_creates_manifest(tmp_path):
    r = CliRunner().invoke(app, ["init", "ep1", "--source", "s.mp4",
                                 "--projects-root", str(tmp_path)])
    assert r.exit_code == 0, r.output
    m = Manifest.load(tmp_path / "ep1" / "manifest.json")
    assert m.project.id == "ep1" and m.project.target_language == "ron"
```

- [ ] **Step 2: Run to verify fail** → `pytest tests/integration/test_cli_init.py -v` FAIL.

- [ ] **Step 3: Implement `cli.py`**

```python
from pathlib import Path
import typer
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths

app = typer.Typer(help="Video Dubbing Pipeline")

@app.command()
def init(project: str, source: str = typer.Option(...),
         source_lang: str = "eng", target_lang: str = "ron",
         projects_root: str = "projects"):
    paths = ProjectPaths(Path(projects_root), project)
    m = Manifest(project=Project(id=project, source=source,
                 source_language=source_lang, target_language=target_lang))
    m.save(paths.manifest)
    typer.echo(f"Initialized {paths.manifest}")
```

- [ ] **Step 4: Run to verify pass** → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: dub init command and CLI skeleton"
```

---

### Task 3: Media Extraction (FFmpeg)

**Files:**
- Create: `src/dubio/pipeline/extract.py`, `src/dubio/pipeline/__init__.py`, `src/dubio/utils/ffmpeg.py`
- Test: `tests/integration/test_extract.py` (uses a tiny generated mp4)

**Interfaces:**
- Produces: `MediaInfo(sample_rate, channels, duration, fps, width, height, video_codec)`; `probe(path) -> MediaInfo`; `extract_audio(source, out_wav, sr=48000) -> Path`; `extract(paths: ProjectPaths, config) -> MediaInfo` writing `audio/source.wav` and recording media info. Video never re-encoded (PRD §8).

- [ ] **Step 1: Write the failing test**

```python
import subprocess, shutil
import pytest
from pathlib import Path
from dubio.pipeline.extract import probe, extract_audio

def _make_fixture(path: Path):
    subprocess.run(["ffmpeg","-y","-f","lavfi","-i","testsrc=duration=2:size=160x120:rate=24",
                    "-f","lavfi","-i","sine=frequency=440:duration=2",
                    "-shortest", str(path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_probe_and_extract(tmp_path):
    mp4 = tmp_path / "clip.mp4"; _make_fixture(mp4)
    info = probe(mp4)
    assert abs(info.duration - 2.0) < 0.3 and info.fps == 24
    wav = extract_audio(mp4, tmp_path / "source.wav", sr=48000)
    assert wav.exists()
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `utils/ffmpeg.py`** (thin `run()` wrapper raising `DubError("FFMPEG-001", …)` on non-zero).

- [ ] **Step 4: Implement `pipeline/extract.py`**

```python
import json, subprocess
from dataclasses import dataclass
from pathlib import Path
from dubio.errors import DubError

@dataclass
class MediaInfo:
    sample_rate: int; channels: int; duration: float
    fps: float; width: int; height: int; video_codec: str

def probe(path) -> MediaInfo:
    out = subprocess.run(["ffprobe","-v","quiet","-print_format","json",
        "-show_streams","-show_format", str(path)], capture_output=True, text=True)
    if out.returncode != 0:
        raise DubError("FFMPEG-002", "ffprobe failed", {"path": str(path)})
    data = json.loads(out.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), {})
    num, den = (v.get("r_frame_rate","0/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den) else 0.0
    return MediaInfo(int(a.get("sample_rate", 0)), int(a.get("channels", 0)),
        float(data["format"]["duration"]), round(fps, 3),
        int(v.get("width", 0)), int(v.get("height", 0)), v.get("codec_name", ""))

def extract_audio(source, out_wav, sr: int = 48000) -> Path:
    out_wav = Path(out_wav); out_wav.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg","-y","-i", str(source),"-vn","-ac","1",
        "-ar", str(sr), str(out_wav)], capture_output=True)
    if r.returncode != 0:
        raise DubError("FFMPEG-001", "audio extraction failed", {"source": str(source)})
    return out_wav

def extract(paths, config) -> MediaInfo:
    from dubio.project.manifest import Manifest
    m = Manifest.load(paths.manifest)
    info = probe(m.project.source)
    extract_audio(m.project.source, paths.audio_dir / "source.wav",
                  sr=config.audio.sample_rate)
    return info
```

- [ ] **Step 5: Add `dub extract` command** wiring `extract()` and storing `MediaInfo` in a sidecar `audio/media_info.json`.

- [ ] **Step 6: Run to verify pass** → PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: FFmpeg media probe + audio extraction (no video re-encode)"
```

---

### Task 4: Whisper ASR Adapter + Transcribe Stage

**Files:**
- Create: `src/dubio/engines/asr/whisper.py`, `src/dubio/pipeline/transcribe.py`
- Test: `tests/integration/test_transcribe.py` (fake ASR), `tests/unit/test_whisper_marked.py` (GPU/model)

**Interfaces:**
- Consumes: `ASREngine`, `ASRResult`, `Segment`, `Word`, `Manifest`, `ProjectPaths`.
- Produces: `WhisperASR(model="large-v3", device="cuda")` implementing `transcribe`/`detect_language`; `transcribe(paths, asr, config)` writing `audio/transcript.json` and populating manifest utterances (`utt_000001…`, `source.{text,start,end,words}`).

- [ ] **Step 1: Write the failing integration test (fake ASR)**

```python
from dubio.pipeline.transcribe import transcribe_segments_to_utterances
from dubio.engines.asr.base import ASRResult, Segment, Word

def test_segments_become_utterances():
    res = ASRResult(text="What are you doing?", language="eng", segments=[
        Segment("What are you doing?", 12.43, 15.87,
                [Word("What",12.43,12.71)])])
    utts = transcribe_segments_to_utterances(res)
    assert utts[0].id == "utt_000001"
    assert utts[0].source.start == 12.43 and utts[0].source.end == 15.87
    assert utts[0].source.words[0]["word"] == "What"
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `pipeline/transcribe.py`**

```python
from dubio.project.manifest import Utterance, SourceSpan, Manifest

def transcribe_segments_to_utterances(res) -> list[Utterance]:
    utts = []
    for i, seg in enumerate(res.segments, start=1):
        utts.append(Utterance(
            id=f"utt_{i:06d}", speaker="speaker_00",
            source=SourceSpan(text=seg.text, start=seg.start, end=seg.end,
                words=[{"word": w.word, "start": w.start, "end": w.end}
                       for w in seg.words])))
    return utts

def transcribe(paths, asr, config) -> None:
    m = Manifest.load(paths.manifest)
    res = asr.transcribe(str(paths.audio_dir / "source.wav"),
                         language=m.project.source_language)
    m.utterances = transcribe_segments_to_utterances(res)
    (paths.audio_dir / "transcript.json").write_text(
        __import__("json").dumps({"language": res.language,
            "segments": [s.__dict__ for s in res.segments]}, ensure_ascii=False))
    m.save(paths.manifest)
```

- [ ] **Step 4: Implement `engines/asr/whisper.py`** (GPU-marked usage)

```python
from dubio.engines.asr.base import ASREngine, ASRResult, Segment, Word

class WhisperASR(ASREngine):
    def __init__(self, model: str = "large-v3", device: str = "cuda", compute_type: str = "float16"):
        from faster_whisper import WhisperModel
        self._m = WhisperModel(model, device=device, compute_type=compute_type)
    def transcribe(self, audio_path, language=None) -> ASRResult:
        segs, info = self._m.transcribe(audio_path, language=language,
                                        word_timestamps=True)
        out = []
        for s in segs:
            words = [Word(w.word, w.start, w.end) for w in (s.words or [])]
            out.append(Segment(s.text.strip(), s.start, s.end, words))
        return ASRResult(" ".join(s.text for s in out).strip(), info.language, out)
    def detect_language(self, audio_path) -> str:
        _, info = self._m.transcribe(audio_path, language=None)
        return info.language
```

- [ ] **Step 5: Add GPU-marked test** in `tests/unit/test_whisper_marked.py` transcribing the Task-3 fixture and asserting a non-empty result (skipped by default). Add `dub transcribe` command.

- [ ] **Step 6: Run to verify pass** → `pytest tests/integration/test_transcribe.py -v` PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: Whisper ASR adapter + transcribe stage"
```

---

### Task 5: Diarization Interface, Fake, pyannote Adapter + Stage

**Files:**
- Create: `src/dubio/engines/diarization/{base,fake,pyannote}.py`, `src/dubio/pipeline/diarize.py`
- Test: `tests/integration/test_diarize.py` (fake), `tests/unit/test_pyannote_marked.py` (GPU/model)

**Interfaces:**
- Produces: `SpeakerTurn(speaker, start, end)`; `DiarizationEngine.diarize(audio_path) -> list[SpeakerTurn]`; `FakeDiarizer(turns)`; `assign_speakers(utterances, turns) -> None` (max-overlap assignment, keeps `SPEAKER_xx` ids distinct from character names per §11).

- [ ] **Step 1: Write the failing test**

```python
from dubio.project.manifest import Utterance, SourceSpan
from dubio.engines.diarization.base import SpeakerTurn
from dubio.pipeline.diarize import assign_speakers

def test_assign_by_max_overlap():
    utts = [Utterance(id="utt_000001", speaker="speaker_00",
            source=SourceSpan(text="hi", start=10.0, end=13.0))]
    turns = [SpeakerTurn("SPEAKER_00",9.0,11.0), SpeakerTurn("SPEAKER_01",11.0,14.0)]
    assign_speakers(utts, turns)
    assert utts[0].speaker == "SPEAKER_01"  # 2.0s overlap vs 1.0s
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `engines/diarization/base.py` + `fake.py`**

```python
# base.py
from dataclasses import dataclass
from typing import Protocol
@dataclass
class SpeakerTurn:
    speaker: str; start: float; end: float
class DiarizationEngine(Protocol):
    def diarize(self, audio_path: str) -> list["SpeakerTurn"]: ...
# fake.py
from dubio.engines.diarization.base import DiarizationEngine, SpeakerTurn
class FakeDiarizer(DiarizationEngine):
    def __init__(self, turns): self._turns = turns
    def diarize(self, audio_path): return list(self._turns)
```

- [ ] **Step 4: Implement `pipeline/diarize.py`**

```python
def _overlap(a0,a1,b0,b1): return max(0.0, min(a1,b1) - max(a0,b0))

def assign_speakers(utterances, turns) -> None:
    for u in utterances:
        best, best_ov = u.speaker, 0.0
        for t in turns:
            ov = _overlap(u.source.start, u.source.end, t.start, t.end)
            if ov > best_ov:
                best, best_ov = t.speaker, ov
        u.speaker = best

def diarize(paths, diarizer, config) -> None:
    from dubio.project.manifest import Manifest
    m = Manifest.load(paths.manifest)
    turns = diarizer.diarize(str(paths.audio_dir / "source.wav"))
    assign_speakers(m.utterances, turns)
    (paths.audio_dir / "diarization.json").write_text(
        __import__("json").dumps([t.__dict__ for t in turns]))
    m.save(paths.manifest)
```

- [ ] **Step 5: Implement `engines/diarization/pyannote.py`** (GPU-marked): wrap `pyannote.audio.Pipeline`, convert to `SpeakerTurn`. Add `dub diarize` command + GPU-marked test.

- [ ] **Step 6: Run to verify pass** → PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: diarization interface, fake, pyannote adapter + stage"
```

---

### Task 6: Character Mapping

**Files:**
- Create: `src/dubio/pipeline/voices.py` (mapping portion; TTS voice-profile portion added in M3)
- Test: `tests/unit/test_character_map.py`

**Interfaces:**
- Produces: `map_character(manifest, speaker_id, name, voice=None) -> None` populating `manifest.characters[speaker_id]`; ids like `SPEAKER_00` stay separate from names (PRD §12). `dub voices <project> --map SPEAKER_00=Bugs`.

- [ ] **Step 1: Write the failing test**

```python
from dubio.project.manifest import Manifest
from dubio.pipeline.voices import map_character

def test_map_character_persists():
    m = Manifest(project={"id":"ep1","source":"s.mp4",
                 "source_language":"eng","target_language":"ron"})
    map_character(m, "SPEAKER_00", "Bugs")
    assert m.characters["SPEAKER_00"].name == "Bugs"
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement mapping in `pipeline/voices.py`**

```python
from dubio.project.manifest import Character

def map_character(manifest, speaker_id: str, name: str, voice: str | None = None) -> None:
    manifest.characters[speaker_id] = Character(name=name, voice=voice)
```

- [ ] **Step 4: Add `dub voices --map SPEAKER_00=Bugs` command** parsing pairs, loading/saving manifest.

- [ ] **Step 5: Run to verify pass** → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: manual speaker→character mapping"
```

---

### Task 7: Timeline Assembly & Overlap Primitives

**Files:**
- Create: `src/dubio/pipeline/timing.py`
- Test: `tests/unit/test_timing.py`

**Interfaces:**
- Produces (engine-agnostic, no ML imports): `find_overlaps(utterances) -> list[Overlap]` where `Overlap(a_id, b_id, seconds)`; `duration_status(target, generated, cfg) -> "pass"|"warning"|"fail"` (PRD §19 thresholds); `target_duration(utt) -> float`. These are reused by M3 (duration matching) and M5 (overlap validation).

- [ ] **Step 1: Write the failing test**

```python
from dubio.project.manifest import Utterance, SourceSpan
from dubio.config import TimingCfg
from dubio.pipeline.timing import find_overlaps, duration_status

def _u(uid,s,e): return Utterance(id=uid,speaker="s",source=SourceSpan(text="x",start=s,end=e))

def test_overlap_detected():
    ov = find_overlaps([_u("utt_001",10.0,13.0), _u("utt_002",12.5,14.2)])
    assert ov[0].seconds == 0.5 and ov[0].a_id == "utt_001"

def test_duration_thresholds():
    cfg = TimingCfg(max_duration_ratio=1.15, warning_duration_ratio=1.05)
    assert duration_status(2.80, 2.80, cfg) == "pass"
    assert duration_status(2.80, 2.80*1.10, cfg) == "warning"
    assert duration_status(2.80, 2.80*1.20, cfg) == "fail"
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `pipeline/timing.py`**

```python
from dataclasses import dataclass

@dataclass
class Overlap:
    a_id: str; b_id: str; seconds: float

def target_duration(utt) -> float:
    return round(utt.source.end - utt.source.start, 3)

def find_overlaps(utterances) -> list[Overlap]:
    ordered = sorted(utterances, key=lambda u: u.source.start)
    out = []
    for i in range(len(ordered) - 1):
        a, b = ordered[i], ordered[i+1]
        ov = round(a.source.end - b.source.start, 3)
        if ov > 0 and not (a.overlap_allowed and b.overlap_allowed):
            out.append(Overlap(a.id, b.id, ov))
    return out

def duration_status(target: float, generated: float, cfg) -> str:
    if generated <= target * cfg.warning_duration_ratio:
        return "pass"
    if generated <= target * cfg.max_duration_ratio:
        return "warning"
    return "fail"
```

- [ ] **Step 4: Run to verify pass** → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: timeline overlap detection + duration status"
```

---

### Task 8: M1 End-to-End Integration (fake engines)

**Files:**
- Test: `tests/integration/test_m1_pipeline.py`

- [ ] **Step 1: Write the failing test** — init → extract (real ffmpeg on 2s fixture) → transcribe (FakeASR scripted) → diarize (FakeDiarizer) → map character → assert manifest has utterances with speakers + character name and diacritics preserved.

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Wire any missing CLI glue** so the flow runs via functions.

- [ ] **Step 4: Run to verify pass** → PASS. Deliverable proven: `episode.mp4 → manifest.json` with accurate timing.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "test: M1 timeline prototype end-to-end with fake engines"
```

---

## Self-Review (M1)

- **Spec coverage:** §7 → T1; §8 → T3; §10 (segments/words/language) → T4; §11 (SPEAKER_xx separate) → T5; §12 (persisted mapping) → T6; §20–21 primitives → T7; deliverable → T8.
- **Placeholders:** none — all steps carry real code/tests. Real Whisper/pyannote internals are isolated in adapters and covered by opt-in GPU tests.
- **Type consistency:** `Manifest`, `Utterance`, `SourceSpan`, `SpeakerTurn`, `duration_status(target, generated, cfg)`, `find_overlaps` names consistent and reused by M3/M5.
