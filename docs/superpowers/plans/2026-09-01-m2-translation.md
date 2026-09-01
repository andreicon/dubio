# Milestone 2 — Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce natural, duration-aware Romanian translations with multiple candidates per utterance, select the best-fitting candidate, and support manual editing/approval — all persisted in the manifest.

**Architecture:** A `Translator` interface returns ranked candidates with estimated durations. A deterministic `FakeTranslator` drives tests; an `LLMTranslator` behind a pluggable OpenAI-compatible endpoint is the production adapter (prompt includes source, languages, available duration, character context, and neighbor lines per PRD §13). A Romanian duration estimator scores candidates.

**Tech Stack:** OpenAI-compatible LLM client, pydantic v2, existing manifest/timing modules.

**Spec:** `PRD.md` (§13 translation, §14 Romanian, §41 M2).

## Global Constraints

(See master plan.) M2 focus: diacritics preserved through translation; translator is engine-swappable and lives only under `engines/translation/`; translation change must (later, M3) invalidate TTS cache; the selected candidate becomes the TTS source text.

**Consumes from M1:** `Manifest`, `Utterance`, `Translation`, `ProjectPaths`, `timing.target_duration`. **From M0:** `DubError`, `assert_diacritics_preserved`.

---

### Task 1: Translator Interface + Fake

**Files:**
- Create: `src/dubio/engines/translation/base.py`, `src/dubio/engines/translation/fake.py`
- Test: `tests/unit/test_translator_fake.py`

**Interfaces:**
- Produces: `Candidate(text: str, estimated_duration: float)`; `TranslationRequest(source_text, source_language, target_language, available_duration, character_context, previous_text, following_text)`; `Translator.translate(req) -> list[Candidate]`; `FakeTranslator(mapping: dict[str,list[str]])`.

- [ ] **Step 1: Write the failing test**

```python
from dubio.engines.translation.base import TranslationRequest, Candidate
from dubio.engines.translation.fake import FakeTranslator

def test_fake_returns_candidates():
    t = FakeTranslator({"What are you doing?": ["Ce faci?", "Ce naiba faci acolo?"]})
    req = TranslationRequest("What are you doing?", "eng", "ron", 2.85, "agitated", "", "")
    cands = t.translate(req)
    assert cands[0].text == "Ce faci?"
    assert all(isinstance(c, Candidate) and c.estimated_duration > 0 for c in cands)
```

- [ ] **Step 2: Run to verify fail** → `pytest tests/unit/test_translator_fake.py -v` FAIL.

- [ ] **Step 3: Implement `engines/translation/base.py`**

```python
from dataclasses import dataclass, field
from typing import Protocol

@dataclass
class Candidate:
    text: str; estimated_duration: float
@dataclass
class TranslationRequest:
    source_text: str; source_language: str; target_language: str
    available_duration: float; character_context: str = ""
    previous_text: str = ""; following_text: str = ""
class Translator(Protocol):
    def translate(self, req: "TranslationRequest") -> list["Candidate"]: ...
```

- [ ] **Step 4: Implement `engines/translation/fake.py`** (uses Task-2 estimator)

```python
from dubio.engines.translation.base import Translator, Candidate
from dubio.engines.translation.duration import estimate_duration

class FakeTranslator(Translator):
    def __init__(self, mapping): self.mapping = mapping
    def translate(self, req):
        texts = self.mapping.get(req.source_text, [req.source_text])
        return [Candidate(t, estimate_duration(t)) for t in texts]
```

- [ ] **Step 5: Run to verify pass** → PASS (after Task 2 estimator exists; if running strictly TDD, implement estimator stub first or reorder Task 2 before Task 1's Step 5).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: translator interface + fake translator"
```

---

### Task 2: Romanian Duration Estimator

**Files:**
- Create: `src/dubio/engines/translation/duration.py`
- Test: `tests/unit/test_duration_estimate.py`

**Interfaces:**
- Produces: `estimate_duration(text: str, chars_per_second: float = 14.0) -> float` (Romanian speaking-rate heuristic; refined by real TTS in M3). Counts letters+spaces, ignores excess punctuation.

- [ ] **Step 1: Write the failing test**

```python
from dubio.engines.translation.duration import estimate_duration

def test_longer_text_longer_duration():
    assert estimate_duration("Ce faci?") < estimate_duration("Ce naiba faci acolo, băiete?")

def test_reasonable_range():
    d = estimate_duration("Ce faci, băiete?")
    assert 0.5 < d < 3.0
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `engines/translation/duration.py`**

```python
import re

def estimate_duration(text: str, chars_per_second: float = 14.0) -> float:
    core = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    n = len(core)
    return round(max(0.3, n / chars_per_second), 3)
```

- [ ] **Step 4: Run to verify pass** → PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: Romanian duration estimator for candidates"
```

---

### Task 3: LLM Translator Adapter

**Files:**
- Create: `src/dubio/engines/translation/llm.py`
- Test: `tests/unit/test_llm_translator.py` (mock client), `tests/integration/test_llm_real.py` (marked `model`, skipped)

**Interfaces:**
- Consumes: `TranslationRequest`, `Candidate`, `estimate_duration`, `assert_diacritics_preserved` (guard target output only when appropriate).
- Produces: `LLMTranslator(client, model, n_candidates=3)` implementing `translate`. Client is any object with `.chat.completions.create(...)` (OpenAI-compatible), injected for testability. Parses JSON candidate list; on malformed output raises `DubError("TRANS-001", …)`.

- [ ] **Step 1: Write the failing test with a mock client**

```python
import json
from dubio.engines.translation.base import TranslationRequest
from dubio.engines.translation.llm import LLMTranslator

class _FakeResp:
    def __init__(self, content): self.choices=[type("C",(),{"message":type("M",(),{"content":content})})]
class _FakeClient:
    def __init__(self, content): self._content=content; self.chat=self
    @property
    def completions(self): return self
    def create(self, **kw):
        return _FakeResp(self._content)

def test_llm_parses_candidates():
    content = json.dumps({"candidates":[
        {"text":"Ce faci?"},{"text":"Ce naiba faci acolo?"}]}, ensure_ascii=False)
    t = LLMTranslator(client=_FakeClient(content), model="x")
    req = TranslationRequest("What are you doing?","eng","ron",2.85,"agitated","","")
    cands = t.translate(req)
    assert cands[0].text == "Ce faci?" and cands[0].estimated_duration > 0
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `engines/translation/llm.py`**

```python
import json
from dubio.engines.translation.base import Translator, Candidate
from dubio.engines.translation.duration import estimate_duration
from dubio.errors import DubError

_PROMPT = """You are a professional dubbing translator.
Translate the SOURCE line from {src} to {tgt} for an animated character.
Constraints:
- The spoken translation should fit about {dur:.2f} seconds.
- Preserve meaning and tone. Character context: {ctx}.
- Keep Romanian diacritics (ă â î ș ț) correct.
Previous line: {prev}
Following line: {nxt}
SOURCE: {text}
Return STRICT JSON: {{"candidates":[{{"text":"..."}}, ...]}} with {n} options
ranked from shortest to longest natural phrasing."""

class LLMTranslator(Translator):
    def __init__(self, client, model: str, n_candidates: int = 3, temperature: float = 0.7):
        self.client=client; self.model=model; self.n=n_candidates; self.temp=temperature
    def translate(self, req):
        prompt = _PROMPT.format(src=req.source_language, tgt=req.target_language,
            dur=req.available_duration, ctx=req.character_context or "neutral",
            prev=req.previous_text, nxt=req.following_text, text=req.source_text, n=self.n)
        resp = self.client.chat.completions.create(model=self.model,
            messages=[{"role":"user","content":prompt}], temperature=self.temp)
        raw = resp.choices[0].message.content
        try:
            data = json.loads(raw)
            cands = [Candidate(c["text"], estimate_duration(c["text"]))
                     for c in data["candidates"]]
        except Exception as e:
            raise DubError("TRANS-001", f"Malformed LLM translation output: {e}",
                           {"raw": raw[:200]}, "Retry or lower temperature")
        if not cands:
            raise DubError("TRANS-002", "No candidates produced", {"text": req.source_text})
        return cands
```

- [ ] **Step 4: Add real-API integration test** (marked `model`, skipped by default) constructing a real `openai.OpenAI(base_url=..., api_key=...)` from env; asserts diacritics present for a diacritic source line.

- [ ] **Step 5: Run to verify pass** → `pytest tests/unit/test_llm_translator.py -v` PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: LLM translator adapter (OpenAI-compatible, injectable client)"
```

---

### Task 4: Candidate Selection + Translate Stage + CLI

**Files:**
- Create: `src/dubio/pipeline/translate.py`
- Test: `tests/integration/test_translate_stage.py`

**Interfaces:**
- Consumes: `Translator`, `TranslationRequest`, `Candidate`, `Manifest`, `timing.target_duration`.
- Produces: `select_candidate(cands, target) -> Candidate` (closest fit that does not overshoot beyond tolerance; prefer largest that is ≤ target*1.15, else the shortest); `translate_project(paths, translator, config)` filling each utterance's `translation.text`, `translation.candidates`, `translation.status="translated"`; writes `translation.json`. `dub translate <project>` and `dub translate <project> --utterance utt_XXXXXX --approve` / `--set "text"`.

- [ ] **Step 1: Write the failing test**

```python
from dubio.engines.translation.base import Candidate
from dubio.pipeline.translate import select_candidate

def test_select_prefers_best_fit_under_tolerance():
    cands = [Candidate("Ce faci?", 1.72), Candidate("Ce naiba faci?", 2.31),
             Candidate("Ce naiba faci acolo?", 2.94)]
    # target 2.85, tolerance 1.15 -> 3.2775 ceiling; pick longest <= ceiling = 2.94
    chosen = select_candidate(cands, target=2.85, max_ratio=1.15)
    assert chosen.text == "Ce naiba faci acolo?"

def test_select_falls_back_to_shortest_when_all_too_long():
    cands = [Candidate("foarte lung text aici", 5.0), Candidate("lung", 4.0)]
    chosen = select_candidate(cands, target=2.0, max_ratio=1.15)
    assert chosen.text == "lung"
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement `pipeline/translate.py`**

```python
import json
from dubio.engines.translation.base import TranslationRequest
from dubio.pipeline.timing import target_duration
from dubio.project.manifest import Manifest

def select_candidate(cands, target: float, max_ratio: float = 1.15):
    ceiling = target * max_ratio
    fitting = [c for c in cands if c.estimated_duration <= ceiling]
    if fitting:
        return max(fitting, key=lambda c: c.estimated_duration)
    return min(cands, key=lambda c: c.estimated_duration)

def translate_project(paths, translator, config) -> None:
    m = Manifest.load(paths.manifest)
    dump = []
    for i, u in enumerate(m.utterances):
        ctx = m.characters.get(u.speaker).name if u.speaker in m.characters else ""
        prev = m.utterances[i-1].source.text if i > 0 else ""
        nxt = m.utterances[i+1].source.text if i+1 < len(m.utterances) else ""
        req = TranslationRequest(u.source.text, m.project.source_language,
            m.project.target_language, target_duration(u), ctx, prev, nxt)
        cands = translator.translate(req)
        chosen = select_candidate(cands, target_duration(u), config.timing.max_duration_ratio)
        u.translation.text = chosen.text
        u.translation.candidates = [{"text": c.text, "estimated_duration": c.estimated_duration}
                                    for c in cands]
        u.translation.status = "translated"
        dump.append({"id": u.id, "chosen": chosen.text, "candidates": u.translation.candidates})
    (paths.base / "translation.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2))
    m.save(paths.manifest)
```

- [ ] **Step 4: Implement integration test** using `FakeTranslator` over a 2-utterance manifest; assert chosen text set, candidates persisted, diacritics preserved, status `translated`.

- [ ] **Step 5: Add CLI** `dub translate` (batch) and manual edit/approve:
  - `--utterance utt_X --set "Ce faci?"` overwrites `translation.text`, status `edited`.
  - `--utterance utt_X --approve` sets status `approved`.

- [ ] **Step 6: Run to verify pass** → PASS.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: candidate selection, translate stage, manual edit/approve CLI"
```

---

## Self-Review (M2)

- **Spec coverage:** §13 inputs (source, langs, duration, character, neighbors) → T3 prompt + T4 request build; multiple candidates + estimated_duration → T1/T2/T3; selected candidate → TTS source → T4; manual editing → T4 CLI; §14 diacritics → guarded in tests. 
- **Placeholders:** none. Real LLM endpoint injected via client for deterministic tests; real call is an opt-in `model`-marked test.
- **Type consistency:** `Candidate(text, estimated_duration)`, `TranslationRequest(...)`, `select_candidate(cands, target, max_ratio)`, `Translator.translate(req)` consistent across tasks and match manifest `Translation.candidates` shape.
- **Note on ordering:** Task 2 (estimator) is imported by Task 1's fake — build estimator first or accept Task 1 Step 5 passes only after Task 2. Executors should implement Task 2 before Task 1 Step 5.
