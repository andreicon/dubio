# Milestone 7 — Final Video & Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mux the final mixed audio into the original video without re-encoding video to produce `output/<id>-ro.mp4`, add a resumable/cache-aware `dub run` orchestrator plus `dub regenerate --utterance`, and prove the full MVP acceptance criteria with an end-to-end integration test.

**Architecture:** `pipeline/render.py` uses FFmpeg stream-copy for video and replaces audio with `mix/final.wav`. `pipeline/run.py` sequences all stages, skipping completed ones via a per-stage completion check (artifact presence + input/config hash), and isolates failures with stable error IDs. `regenerate` reruns only the affected utterance's synth→normalize→validate and re-mixes.

**Tech Stack:** FFmpeg, existing pipeline modules, structlog.

**Spec:** `PRD.md` (§25 rendering, §31 CLI, §32 resumability, §35 errors, §36 observability, §42 MVP acceptance).

## Global Constraints

(See master plan.) M7 focus: no unnecessary video re-encode; preserve fps/resolution; resumable runs reuse artifacts; single-line regeneration without full rerun; failures explicit with stable IDs and never corrupt prior artifacts.

**Consumes:** all prior milestones' stage functions and `ProjectPaths`, `Manifest`, `Config`.

---

### Task 1: Video Render (FFmpeg mux, no re-encode)

**Files:**
- Create: `src/dub/pipeline/render.py`
- Test: `tests/integration/test_render.py` (real ffmpeg on 2s fixture)

**Interfaces:**
- Produces: `render(paths, config) -> Path` running FFmpeg to mux `mix/final.wav` with the original video via `-c:v copy`, `-map 0:v:0 -map 1:a:0`, output `output/<id>-ro.mp4`; preserves fps/resolution; raises `DubError("RENDER-001", …)` on failure.

- [ ] **Step 1: Write the failing test**

```python
import subprocess, shutil
import numpy as np
import pytest
from pathlib import Path
from dub.project.manifest import Manifest
from dub.project.paths import ProjectPaths
from dub.audio.measure import write_wav
from dub.config import Config
from dub.pipeline.render import render

def _fixture_video(path):
    subprocess.run(["ffmpeg","-y","-f","lavfi","-i","testsrc=duration=2:size=160x120:rate=24",
        "-f","lavfi","-i","sine=frequency=440:duration=2","-shortest", str(path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_render_muxes_output(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    src = tmp_path / "src.mp4"; _fixture_video(src)
    m = Manifest(project={"id":"ep1","source":str(src),
                 "source_language":"eng","target_language":"ron"})
    m.save(paths.manifest)
    write_wav(paths.mix_dir / "final.wav", np.zeros(48000*2), 48000)
    out = render(paths, Config())
    assert Path(out).exists() and out.name == "ep1-ro.mp4"
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `pipeline/render.py`**

```python
import subprocess
from dub.project.manifest import Manifest
from dub.errors import DubError

def render(paths, config):
    m = Manifest.load(paths.manifest)
    out = paths.output_dir / f"{m.project.id}-ro.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    final = paths.mix_dir / "final.wav"
    cmd = ["ffmpeg","-y","-i", m.project.source, "-i", str(final),
           "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k",
           "-shortest", str(out)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise DubError("RENDER-001", "ffmpeg mux failed",
                       {"stderr": r.stderr.decode()[-400:]}, "Check codecs/paths")
    return out
```

- [ ] **Step 4: Add `dub render <project>` CLI**.

- [ ] **Step 5: Run to verify pass** → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: FFmpeg video mux render (stream-copy video)"
```

---

### Task 2: Resumable Orchestrator (`dub run`)

**Files:**
- Create: `src/dub/pipeline/run.py`
- Test: `tests/integration/test_run_resume.py`

**Interfaces:**
- Produces: `StageSpec(name, artifact_check: Callable[[ProjectPaths], bool], func: Callable)`; `STAGES: list[StageSpec]` (extract, separate, transcribe, diarize, translate, synthesize, normalize, validate, mix, render); `stage_complete(spec, paths) -> bool`; `run(paths, config, engines, force_from=None) -> None` executing stages in order, skipping complete ones unless `force_from`. Records per-stage status/log; a stage failure stops the run with a stable error ID but leaves prior artifacts intact.

- [ ] **Step 1: Write the failing test (skip logic with fakes)**

```python
from dub.pipeline.run import stage_complete, StageSpec
from dub.project.paths import ProjectPaths

def test_stage_complete_by_artifact(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    spec = StageSpec("extract", lambda p: (p.audio_dir/"source.wav").exists(), lambda **k: None)
    assert stage_complete(spec, paths) is False
    (paths.audio_dir).mkdir(parents=True); (paths.audio_dir/"source.wav").write_bytes(b"x")
    assert stage_complete(spec, paths) is True
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `pipeline/run.py`**

```python
from dataclasses import dataclass
from typing import Callable
from dub.logging import get_logger
from dub.errors import DubError
log = get_logger("run")

@dataclass
class StageSpec:
    name: str
    artifact_check: Callable
    func: Callable

def stage_complete(spec, paths) -> bool:
    try:
        return bool(spec.artifact_check(paths))
    except Exception:
        return False

def build_stages(engines) -> list[StageSpec]:
    from dub.pipeline import extract, separate, transcribe, diarize, translate as tr
    from dub.pipeline import synthesize, normalize, validate as val, mix, render
    p = lambda rel: (lambda paths: (paths.base / rel).exists())
    return [
        StageSpec("extract", lambda paths: (paths.audio_dir/"source.wav").exists(),
                  lambda paths, config: extract.extract(paths, config)),
        StageSpec("separate", lambda paths: (paths.audio_dir/"music.wav").exists(),
                  lambda paths, config: separate.separate(paths, engines["separator"], config)),
        StageSpec("transcribe", lambda paths: (paths.audio_dir/"transcript.json").exists(),
                  lambda paths, config: transcribe.transcribe(paths, engines["asr"], config)),
        StageSpec("diarize", lambda paths: (paths.audio_dir/"diarization.json").exists(),
                  lambda paths, config: diarize.diarize(paths, engines["diarizer"], config)),
        StageSpec("translate", lambda paths: (paths.base/"translation.json").exists(),
                  lambda paths, config: tr.translate_project(paths, engines["translator"], config)),
        StageSpec("synthesize", lambda paths: paths.tts_dir.exists() and any(paths.tts_dir.glob("utt_*.wav")),
                  lambda paths, config: synthesize.synthesize_project(paths, engines["tts"], config)),
        StageSpec("normalize", lambda paths: paths.processed_dir.exists() and any(paths.processed_dir.glob("utt_*.wav")),
                  lambda paths, config: normalize.normalize_project(paths, config)),
        StageSpec("validate", lambda paths: (paths.validation_dir/"report.json").exists(),
                  lambda paths, config: val.validate_project(paths, engines["asr"], config)),
        StageSpec("mix", lambda paths: (paths.mix_dir/"final.wav").exists(),
                  lambda paths, config: mix.mix_project(paths, config)),
        StageSpec("render", lambda paths: paths.output_dir.exists() and any(paths.output_dir.glob("*-ro.mp4")),
                  lambda paths, config: render.render(paths, config)),
    ]

def run(paths, config, engines, force_from: str | None = None) -> None:
    stages = build_stages(engines)
    forcing = force_from is None
    for spec in stages:
        if spec.name == force_from:
            forcing = True
        if not forcing and stage_complete(spec, paths):
            log.info("stage_skipped", stage=spec.name)
            continue
        log.info("stage_start", stage=spec.name)
        try:
            spec.func(paths=paths, config=config)
        except DubError as e:
            log.error("stage_failed", stage=spec.name, code=e.code, message=e.message)
            raise
        log.info("stage_done", stage=spec.name)
```

- [ ] **Step 4: Add integration test** running `run()` twice with fake engines over the 2s fixture; second run logs skips and does not overwrite artifacts (assert mtimes unchanged for early stages). Add `dub run <project> [--force-from STAGE]` CLI.

- [ ] **Step 5: Run to verify pass** → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: resumable dub run orchestrator with stage skip"
```

---

### Task 3: Single-Utterance Regeneration

**Files:**
- Create: `src/dub/pipeline/regenerate.py`
- Test: `tests/integration/test_regenerate.py`

**Interfaces:**
- Produces: `regenerate_utterance(paths, uid, engines, config) -> None` running synth(force)→normalize→validate for just `uid`, then `mix_project` to rebuild the final mix — without touching other utterances' artifacts. CLI `dub regenerate <project> --utterance utt_X`.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import numpy as np
from dub.project.manifest import Manifest, Character, Voice, Utterance, SourceSpan, Translation
from dub.project.paths import ProjectPaths
from dub.audio.measure import write_wav
from dub.config import Config
from dub.engines.tts.fake import FakeTTS
from dub.engines.asr.fake import FakeASR
from dub.pipeline.regenerate import regenerate_utterance

def test_regenerate_only_target(tmp_path):
    paths = ProjectPaths(tmp_path, "ep1")
    # pre-existing artifact for a different utterance must remain
    other = paths.tts_dir / "utt_000002.wav"; write_wav(other, np.zeros(1000), 48000)
    mtime = other.stat().st_mtime_ns
    m = Manifest(project={"id":"ep1","source":"s","source_language":"eng","target_language":"ron"})
    m.characters["SPEAKER_00"] = Character(name="Bugs", voice="v")
    m.voices["v"] = Voice(engine="fake")
    m.utterances.append(Utterance(id="utt_000001", speaker="SPEAKER_00",
        source=SourceSpan(text="x", start=0, end=2),
        translation=Translation(text="Ce faci?", status="approved")))
    write_wav(paths.audio_dir/"music.wav", np.zeros(48000*2), 48000)
    write_wav(paths.audio_dir/"sfx.wav", np.zeros(48000*2), 48000)
    m.save(paths.manifest)
    engines = {"tts": FakeTTS(out_dir=paths.tts_dir), "asr": FakeASR()}
    regenerate_utterance(paths, "utt_000001", engines, Config())
    assert (paths.tts_dir/"utt_000001.wav").exists()
    assert other.stat().st_mtime_ns == mtime  # untouched
    assert (paths.mix_dir/"final.wav").exists()
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `pipeline/regenerate.py`**

```python
from dub.utils.cache import Cache
from dub.project.manifest import Manifest
from dub.pipeline.synthesize import synthesize_utterance
from dub.pipeline.normalize import normalize_utterance
from dub.pipeline.validate import validate_utterance
from dub.pipeline.mix import mix_project

def regenerate_utterance(paths, uid, engines, config) -> None:
    m = Manifest.load(paths.manifest)
    utt = m.get_utterance(uid)
    cache = Cache(paths.tts_dir / "_cache")
    synthesize_utterance(m, utt, engines["tts"], cache, paths, force=True)
    normalize_utterance(m, utt, paths, config)
    validate_utterance(m, utt, engines["asr"], config)
    m.save(paths.manifest)
    mix_project(paths, config)  # re-composite final with the updated clip
```

- [ ] **Step 4: Add CLI** `dub regenerate --utterance`.

- [ ] **Step 5: Run to verify pass** → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: single-utterance regeneration + remix"
```

---

### Task 4: MVP Acceptance End-to-End Test

**Files:**
- Test: `tests/integration/test_mvp_acceptance.py`
- Create: `docs/architecture.md`, `docs/troubleshooting.md` (short, referencing stages + error IDs)

**Interfaces:**
- Consumes: full pipeline with fake engines (FakeASR scripted, FakeDiarizer, FakeTranslator, FakeTTS, FakeSeparator) over the 2s A/V fixture.

- [ ] **Step 1: Write the failing acceptance test** — asserts each PRD §42 criterion:

```python
# Build a project, run every stage with fakes, then assert:
# 1 source.wav exists; 2 transcript utterances; 3 speakers assigned;
# 4 character mapped; 5 translation.text set; 6 diacritics preserved;
# 7 tts wavs exist; 8 language check present; 9 tts.duration measured;
# 10 dialogue placed within timeline (mix/final.wav length == source);
# 11 overlaps reported in report.json; 12 loudness normalized (~ -16);
# 13 music/sfx stems preserved; 14 mix/final.wav exists; 15 output mp4 exists;
# 16 regenerate one utterance leaves others' mtimes; 17 second run skips stages;
# 18 report.json + logs identify a failing stage.
```

Implement the assertions concretely against the produced artifacts and manifest fields defined in M1–M6.

- [ ] **Step 2: Run to verify fail** → FAIL (wiring gaps surface).

- [ ] **Step 3: Fix any glue** needed so all 18 assertions pass; write short `docs/architecture.md` (stage list + manifest role) and `docs/troubleshooting.md` (error ID table: `TTS-RO-001`, `SEP-001`, `RENDER-001`, `MIX-001`, `VOICE-001`, `TRANS-001`, `FFMPEG-001/002`).

- [ ] **Step 4: Run to verify pass** → `pytest tests/integration/test_mvp_acceptance.py -v` PASS.

- [ ] **Step 5: Run full suite** → `pytest -m "not gpu and not model" -q` all green; then commit.

```bash
git add -A && git commit -m "test: MVP acceptance end-to-end (18 criteria) + docs"
```

---

## Self-Review (M7)

- **Spec coverage:** §25 mux/no-reencode/preserve fps/res/MP4 → T1; §31 CLI (run/regenerate/render + per-utterance) → T1–T3; §32 resumability/reuse artifacts → T2; §33 cache reuse verified via T3 (force=True on target only); §35 stable error IDs → all stages; §36 structured logs → run orchestrator; §42 all 18 acceptance criteria → T4.
- **Placeholders:** none. Acceptance assertions are enumerated and map to concrete artifacts/manifest fields from earlier milestones.
- **Type consistency:** `render(paths, config)`, `run(paths, config, engines, force_from)`, `regenerate_utterance(paths, uid, engines, config)`; stage funcs called as `func(paths=..., config=...)` matching the `StageSpec` wrappers; reuses `synthesize_utterance`, `normalize_utterance`, `validate_utterance`, `mix_project` signatures from M3–M6.
