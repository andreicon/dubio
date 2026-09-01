# Milestone 5 — Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make validation a first-class stage: per-utterance checks for duration, overlap, loudness, true-peak, target-language, and re-ASR text match, combined into a composite quality score with raw measurements retained, emitted as `validation/report.json`.

**Architecture:** Independent, pure validator functions each return a check result; `pipeline/validate.py` runs them per utterance, writes each result into the manifest `validation` block plus `measurements`, computes a weighted score, and produces a report. Language/text validators use the ASR interface (fake in tests, Whisper in production). Errors are surfaced, never silently repaired (PRD §5.4).

**Tech Stack:** existing manifest/timing/measure/similarity modules, ASR interface.

**Spec:** `PRD.md` (§21 overlap, §26 validation, §27 text validation, §28 language validation, §30 quality score).

## Global Constraints

(See master plan.) M5 focus: raw measurements retained so score can be recomputed; punctuation-tolerant text match flags real lexical drift; intentional overlaps (`overlap_allowed`) excluded from failures; language mismatch is a failure.

**Consumes:** M1 `timing.{find_overlaps,duration_status,target_duration}`, `Manifest/Utterance`; M0 `text_similarity`, `measure_loudness`, ASR interface + `FakeASR`; M4 stored loudness measurements.

---

### Task 1: Numeric Validators (duration, overlap, loudness, peak)

**Files:**
- Create: `src/dubio/validation/__init__.py`, `duration.py`, `overlap.py`, `loudness.py`, `peak.py`
- Test: `tests/unit/test_validators_numeric.py`

**Interfaces:**
- Produces: `CheckResult(name: str, status: "pass"|"warning"|"fail", score: float, detail: dict)`;
  `check_duration(utt, cfg) -> CheckResult`; `check_overlaps(utterances) -> list[CheckResult]` (one per offending pair, keyed by ids, respects `overlap_allowed`); `check_loudness(utt, target_lufs, tol=2.0) -> CheckResult`; `check_peak(utt, ceiling_db=-1.0) -> CheckResult`.

- [ ] **Step 1: Write the failing test**

```python
from dubio.project.manifest import Utterance, SourceSpan, TTSInfo, Validation
from dubio.config import TimingCfg
from dubio.validation.duration import check_duration
from dubio.validation.overlap import check_overlaps
from dubio.validation.loudness import check_loudness
from dubio.validation.peak import check_peak

def _u(uid,s,e,dur=None,allow=False):
    u = Utterance(id=uid, speaker="s", source=SourceSpan(text="x", start=s, end=e))
    u.tts = TTSInfo(duration=dur if dur is not None else e-s)
    u.overlap_allowed = allow
    return u

def test_duration_pass():
    assert check_duration(_u("u",0,2.8,2.8), TimingCfg()).status == "pass"

def test_overlap_flags_unmarked_only():
    res = check_overlaps([_u("utt_001",10,13), _u("utt_002",12.5,14.2)])
    assert res and res[0].status in ("warning","fail")
    res2 = check_overlaps([_u("utt_001",10,13,allow=True), _u("utt_002",12.5,14.2,allow=True)])
    assert res2 == []

def test_loudness_within_tolerance():
    u = _u("u",0,1); u.validation = Validation(measurements={"loudness":{"integrated_lufs":-16.4}})
    assert check_loudness(u, target_lufs=-16.0, tol=2.0).status == "pass"

def test_peak_fail_when_hot():
    u = _u("u",0,1); u.validation = Validation(measurements={"loudness":{"true_peak_db":-0.2}})
    assert check_peak(u, ceiling_db=-1.0).status == "fail"
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `validation/__init__.py`** (`CheckResult` dataclass) and the four validators.

```python
# __init__.py
from dataclasses import dataclass, field
@dataclass
class CheckResult:
    name: str; status: str; score: float; detail: dict = field(default_factory=dict)
# duration.py
from dubio.validation import CheckResult
from dubio.pipeline.timing import duration_status, target_duration
def check_duration(utt, cfg) -> CheckResult:
    t = target_duration(utt); g = utt.tts.duration or 0.0
    st = duration_status(t, g, cfg)
    score = {"pass":1.0,"warning":0.7,"fail":0.0}[st]
    return CheckResult("duration", st, score, {"target": t, "generated": g, "diff": round(g-t,3)})
# overlap.py
from dubio.validation import CheckResult
from dubio.pipeline.timing import find_overlaps
def check_overlaps(utterances) -> list[CheckResult]:
    out = []
    for ov in find_overlaps(utterances):
        st = "fail" if ov.seconds > 0.3 else "warning"
        out.append(CheckResult("overlap", st, 0.0 if st=="fail" else 0.6,
                   {"a": ov.a_id, "b": ov.b_id, "seconds": ov.seconds}))
    return out
# loudness.py
from dubio.validation import CheckResult
def check_loudness(utt, target_lufs, tol=2.0) -> CheckResult:
    lufs = utt.validation.measurements.get("loudness", {}).get("integrated_lufs")
    if lufs is None:
        return CheckResult("loudness", "fail", 0.0, {"reason": "no measurement"})
    diff = abs(lufs - target_lufs)
    st = "pass" if diff <= tol else ("warning" if diff <= 2*tol else "fail")
    return CheckResult("loudness", st, max(0.0, 1.0 - diff/(2*tol)), {"lufs": lufs, "diff": round(diff,2)})
# peak.py
from dubio.validation import CheckResult
def check_peak(utt, ceiling_db=-1.0) -> CheckResult:
    tp = utt.validation.measurements.get("loudness", {}).get("true_peak_db")
    if tp is None:
        return CheckResult("peak", "fail", 0.0, {"reason": "no measurement"})
    st = "pass" if tp <= ceiling_db else "fail"
    return CheckResult("peak", st, 1.0 if st=="pass" else 0.0, {"true_peak_db": tp})
```

- [ ] **Step 4: Run to verify pass** → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: numeric validators (duration, overlap, loudness, peak)"
```

---

### Task 2: Language & Re-ASR Text Validators

**Files:**
- Create: `src/dubio/validation/language.py`, `src/dubio/validation/text.py`
- Test: `tests/unit/test_validators_asr.py`

**Interfaces:**
- Consumes: ASR interface (`transcribe`, `detect_language`), `text_similarity`.
- Produces: `check_language(utt, asr, expected="ro") -> CheckResult` (fail on mismatch, PRD §28); `check_text(utt, asr, sim_threshold=0.80) -> CheckResult` (re-ASR processed clip, punctuation-tolerant compare vs `translation.text`, flags lexical drift, PRD §27). Both read the processed/tts clip path.

- [ ] **Step 1: Write the failing test**

```python
from dubio.project.manifest import Utterance, SourceSpan, TTSInfo, Translation
from dubio.engines.asr.fake import FakeASR
from dubio.validation.language import check_language
from dubio.validation.text import check_text

def _u(path, text):
    u = Utterance(id="u", speaker="s", source=SourceSpan(text="x", start=0, end=2),
                  translation=Translation(text=text, status="approved"),
                  tts=TTSInfo(file=path, duration=2.0))
    return u

def test_language_mismatch_fails():
    u = _u("a.wav", "Ce faci, băiete?")
    asr = FakeASR(scripted={"a.wav": ("Ce faci, băiete?", "en")})
    assert check_language(u, asr, expected="ro").status == "fail"

def test_text_match_tolerates_punctuation():
    u = _u("a.wav", "Ce faci, băiete?")
    asr = FakeASR(scripted={"a.wav": ("Ce faci băiete", "ro")})
    assert check_text(u, asr).status == "pass"

def test_text_flags_drift():
    u = _u("a.wav", "Ce faci acolo?")
    asr = FakeASR(scripted={"a.wav": ("Unde mergi mâine", "ro")})
    assert check_text(u, asr).status == "fail"
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `validation/language.py` and `validation/text.py`**

```python
# language.py
from dubio.validation import CheckResult
def check_language(utt, asr, expected="ro") -> CheckResult:
    path = utt.tts.file
    detected = asr.detect_language(path)
    st = "pass" if detected == expected else "fail"
    return CheckResult("language", st, 1.0 if st=="pass" else 0.0,
                       {"expected": expected, "detected": detected})
# text.py
from dubio.validation import CheckResult
from dubio.utils.similarity import text_similarity
def check_text(utt, asr, sim_threshold=0.80) -> CheckResult:
    expected = utt.translation.text or utt.source.text
    got = asr.transcribe(utt.tts.file, language="ro").text
    sim = text_similarity(expected, got)
    st = "pass" if sim >= sim_threshold else ("warning" if sim >= 0.6 else "fail")
    return CheckResult("text", st, sim, {"expected": expected, "transcribed": got,
                                         "similarity": round(sim, 3)})
```

- [ ] **Step 4: Run to verify pass** → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: language + re-ASR text validators"
```

---

### Task 3: Composite Score + Validate Stage + Report

**Files:**
- Create: `src/dubio/validation/score.py`, `src/dubio/pipeline/validate.py`
- Test: `tests/unit/test_score.py`, `tests/integration/test_validate_stage.py`

**Interfaces:**
- Produces: `composite_score(results: list[CheckResult], weights: dict|None) -> tuple[int, dict]` (0–100 + per-check raw map, PRD §30); `validate_utterance(m, utt, asr, config) -> dict` writing statuses into `utt.validation.*`, storing raw `measurements["checks"]` and `validation.score`; `validate_project(paths, asr, config) -> dict` writing `validation/report.json`. CLI `dub validate <project> [--utterance utt_X]`.

- [ ] **Step 1: Write the failing test**

```python
from dubio.validation import CheckResult
from dubio.validation.score import composite_score

def test_score_weights_and_range():
    results = [CheckResult("language","pass",1.0), CheckResult("text","pass",0.97),
               CheckResult("duration","warning",0.7), CheckResult("loudness","pass",1.0)]
    score, raw = composite_score(results, weights=None)
    assert 0 <= score <= 100 and raw["text"] == 0.97
    # A language fail should heavily reduce score
    fail = [CheckResult("language","fail",0.0)] + results[1:]
    score2, _ = composite_score(fail, weights=None)
    assert score2 < score
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `validation/score.py`**

```python
DEFAULT_WEIGHTS = {"language": 0.25, "text": 0.25, "duration": 0.2,
                   "loudness": 0.15, "peak": 0.1, "overlap": 0.05}

def composite_score(results, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    raw = {r.name: r.score for r in results}
    total_w = sum(weights.get(r.name, 0.0) for r in results) or 1.0
    weighted = sum(weights.get(r.name, 0.0) * r.score for r in results)
    return round(100 * weighted / total_w), raw
```

- [ ] **Step 4: Implement `pipeline/validate.py`**

```python
import json
from dubio.validation.duration import check_duration
from dubio.validation.overlap import check_overlaps
from dubio.validation.loudness import check_loudness
from dubio.validation.peak import check_peak
from dubio.validation.language import check_language
from dubio.validation.text import check_text
from dubio.validation.score import composite_score
from dubio.project.manifest import Manifest

def validate_utterance(m, utt, asr, config) -> dict:
    results = [
        check_duration(utt, config.timing),
        check_loudness(utt, config.audio.target_lufs),
        check_peak(utt, config.audio.true_peak_db),
    ]
    if utt.tts.file:
        results.append(check_language(utt, asr, expected="ro"))
        results.append(check_text(utt, asr))
    score, raw = composite_score(results)
    utt.validation.duration = next((r.status for r in results if r.name=="duration"), None)
    utt.validation.loudness = next((r.status for r in results if r.name=="loudness"), None)
    utt.validation.language = next((r.status for r in results if r.name=="language"), None)
    utt.validation.transcription = next((r.status for r in results if r.name=="text"), None)
    utt.validation.score = score
    utt.validation.measurements["checks"] = {r.name: r.detail for r in results}
    return {"id": utt.id, "score": score, "checks": raw}

def validate_project(paths, asr, config) -> dict:
    m = Manifest.load(paths.manifest)
    reports = [validate_utterance(m, u, asr, config) for u in m.utterances]
    overlaps = [c.detail for c in check_overlaps(m.utterances)]
    for u in m.utterances:
        u.validation.overlap = "fail" if any(
            o["a"]==u.id or o["b"]==u.id for o in overlaps) else "pass"
    report = {"project": m.project.id, "utterances": reports, "overlaps": overlaps}
    (paths.validation_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2))
    m.save(paths.manifest)
    return report
```

- [ ] **Step 5: Add integration test** over a 2-utterance manifest with `FakeASR` + a processed clip, asserting `report.json` exists, scores present, overlap flagged. Add CLI `dub validate`.

- [ ] **Step 6: Run to verify pass** → PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: composite score + validate stage + report.json"
```

---

## Self-Review (M5)

- **Spec coverage:** §21 overlap incl. intentional → T1; §26 per-utterance report → T3; §27 punctuation-tolerant text match, lexical drift flags → T2; §28 language mismatch fail → T2; §30 composite score + raw measurements retained → T3 (`measurements["checks"]` + `raw`). §29 voice-embedding similarity deferred (documented future).
- **Placeholders:** none. Optional HTML report is explicitly out of MVP (PRD §41 M5 note) and can be added later from `report.json`.
- **Type consistency:** `CheckResult(name,status,score,detail)`, `check_*` signatures, `composite_score(results, weights)`, `validate_utterance(m, utt, asr, config)` consistent; reuses `find_overlaps`, `duration_status`, `text_similarity`, M4 loudness measurement keys.
