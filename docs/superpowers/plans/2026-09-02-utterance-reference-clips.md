# Utterance Reference Clips Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save one exact source-audio reference clip per utterance and pass that clip into Delusion/audio.cpp during synthesis.

**Architecture:** Keep the current transcript-and-utterance pipeline, but add a per-utterance reference clip extracted from `audio/source.wav` using the utterance’s exact source span. Persist that clip path on the utterance so synthesis can load it later and pass it directly to Delusion as the voice reference for that utterance only. This avoids reusable voice profiles for v1 and keeps the change localized to transcription, the manifest, and Delusion synthesis.

**Tech Stack:** Python 3.12, Typer CLI, Pydantic models in `src/dubio/project/manifest.py`, ffmpeg/ffprobe, soundfile/numpy/scipy audio utilities already present in the repo, pytest.

**Spec:** `PRD.md` (§17 Voice Profiles as future reusable state, §18 TTS Generation, §32 Pipeline Resumability, §33 Caching)

## Global Constraints

- Each utterance gets exactly one reference clip stored from the exact source span.
- The clip is cut from the original source audio, not from synthesized TTS output.
- Do not introduce a new enrollment command for this flow.
- Delusion/audio.cpp remains the synthesis backend for the reference clip.
- Preserve the existing reusable voice-profile system for other paths unless a task explicitly changes it.

---

### Task 1: Add per-utterance reference clip metadata to the manifest

**Files:**
- Modify: `src/dubio/project/manifest.py:49-80`
- Test: `tests/unit/test_manifest.py` or `tests/unit/test_voice_profiles.py` if that is the nearest existing manifest/voice test file

**Interfaces:**
- Consumes: `Utterance` and `Manifest` models
- Produces: `Utterance.reference_audio` (or equivalent explicit field) storing the saved clip path for later synthesis

- [ ] **Step 1: Write the failing test**

Add a unit test that constructs an utterance, sets a reference clip path on it, saves the manifest, reloads it, and asserts the path survives round-trip serialization.

```python
def test_utterance_reference_audio_round_trips(tmp_path):
    manifest = Manifest(
        project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"),
        utterances=[Utterance(id="utt_000001", speaker="SPEAKER_00", source=SourceSpan(text="x", start=0.0, end=1.0))],
    )
    manifest.utterances[0].reference_audio = "audio/reference/utt_000001.wav"
    manifest.save(tmp_path / "manifest.json")
    loaded = Manifest.load(tmp_path / "manifest.json")
    assert loaded.utterances[0].reference_audio == "audio/reference/utt_000001.wav"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/unit/test_manifest.py -k reference_audio`

Expected: FAIL because the model has no persisted per-utterance reference field yet.

- [ ] **Step 3: Write minimal implementation**

Add a nullable `reference_audio: str | None = None` field to `Utterance` and keep the rest of the model unchanged.

```python
class Utterance(BaseModel):
    ...
    reference_audio: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/unit/test_manifest.py -k reference_audio`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dubio/project/manifest.py tests/unit/test_manifest.py
git commit -m "feat: store utterance reference clips"
```

### Task 2: Extract one exact reference clip per utterance during transcription

**Files:**
- Modify: `src/dubio/pipeline/transcribe.py:1-42`
- Modify: `src/dubio/pipeline/extract.py` only if the utterance clip extraction needs a shared helper or source-audio path hookup
- Test: `tests/integration/test_transcribe.py` or the closest existing transcribe integration file

**Interfaces:**
- Consumes: the source WAV at `paths.audio_dir / "source.wav"` and each utterance’s `source.start` / `source.end`
- Produces: `audio/reference/<utt_id>.wav` (or the chosen path) plus `utterance.reference_audio` pointing at that clip

- [ ] **Step 1: Write the failing test**

Add an integration test that creates a simple source WAV, runs transcription on a scripted result with one segment, and asserts a new reference clip exists for that utterance and matches the exact source span duration.

```python
def test_transcribe_writes_exact_reference_clip(tmp_path):
    ...
    assert (paths.audio_dir / "reference" / "utt_000001.wav").exists()
    assert manifest.utterances[0].reference_audio == "audio/reference/utt_000001.wav"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/integration/test_transcribe.py -k reference_clip`

Expected: FAIL because transcription does not yet write a clip or store its path.

- [ ] **Step 3: Write minimal implementation**

In `transcribe()`, after utterances are created, cut `source.wav` with `ffmpeg` or the repo’s audio helpers using the exact utterance span and save each clip under `paths.audio_dir / "reference" / f"{utt.id}.wav"`. Write the saved relative path into `utterance.reference_audio` before saving the manifest.

Use the exact source span bounds already on the utterance; do not add padding in this v1.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/integration/test_transcribe.py -k reference_clip`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dubio/pipeline/transcribe.py tests/integration/test_transcribe.py
git commit -m "feat: save utterance reference clips"
```

### Task 3: Pass the per-utterance reference clip into Delusion synthesis

**Files:**
- Modify: `src/dubio/pipeline/synthesize.py:18-50`
- Modify: `src/dubio/engines/tts/delusion.py:48-58`
- Test: `tests/integration/test_synthesize.py`

**Interfaces:**
- Consumes: `utterance.reference_audio` from the manifest
- Produces: Delusion synthesis calls that use the utterance-specific reference clip instead of a reusable voice profile reference

- [ ] **Step 1: Write the failing test**

Add an integration test that sets `utterance.reference_audio` to a known WAV path, stubs the Delusion backend, and asserts `tts.synthesize()` receives that exact reference for the utterance.

```python
def test_delusion_uses_utterance_reference_audio(tmp_path, monkeypatch):
    ...
    assert observed["reference"] == str(reference_clip)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/integration/test_synthesize.py -k utterance_reference`

Expected: FAIL because synthesis still uses the manifest voice profile path, not the per-utterance clip.

- [ ] **Step 3: Write minimal implementation**

In `synthesize_utterance()`, prefer `utterance.reference_audio` when present, and build a `VoiceProfile` or equivalent call payload that passes that path into Delusion/audio.cpp. Keep the reusable `manifest.voices[...]` path working for any utterance that does not yet have a per-utterance clip.

```python
reference = utterance.reference_audio or voice.reference
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/integration/test_synthesize.py -k utterance_reference`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dubio/pipeline/synthesize.py src/dubio/engines/tts/delusion.py tests/integration/test_synthesize.py
git commit -m "feat: use utterance reference clips in delusion"
```

### Task 4: Update the pipeline docs for per-utterance cloning

**Files:**
- Modify: `usage.md`
- Modify: `README.md` only if the flow needs a short note there

**Interfaces:**
- Consumes: the final per-utterance reference clip flow
- Produces: docs explaining that transcription now writes reference clips and synthesis uses them per utterance

- [ ] **Step 1: Write the failing doc expectation**

If the repo has no doc tests, use direct file inspection as the verification step after editing.

- [ ] **Step 2: Update docs**

Add a short note explaining that `transcribe` now saves `audio/reference/<utt_id>.wav` and `synthesize` uses that utterance-local reference clip for Delusion/audio.cpp.

Example wording:

```text
Transcribe now saves a per-utterance reference clip from the exact source span, and Delusion synthesis uses that clip as the voice reference for that utterance.
```

- [ ] **Step 3: Verify docs are consistent with code**

Confirm the docs match the actual path name and do not mention the old reusable-voice requirement as the primary path for this feature.

- [ ] **Step 4: Commit**

```bash
git add usage.md README.md
git commit -m "docs: describe utterance reference clipping"
```

### Task 5: End-to-end verification

**Files:**
- No code changes unless verification exposes a concrete bug

**Interfaces:**
- Consumes: the full `extract -> transcribe -> synthesize` slice with utterance reference clips
- Produces: verified per-utterance reference-clip cloning flow

- [ ] **Step 1: Run the focused tests**

Run:

```bash
./.venv/bin/python -m pytest tests/unit/test_manifest.py tests/integration/test_transcribe.py tests/integration/test_synthesize.py
```

Expected: PASS.

- [ ] **Step 2: Run the real pipeline slice**

Run the shortest real project slice that creates utterance reference clips and synthesizes with them, using the repo’s configured `AUDIOCPP_PATH` and an existing project.

Expected: per-utterance reference clips are written, synthesis consumes them, and the earlier `TTS synthesis failed for 13 utterance(s)` aggregate error is gone for this path.

- [ ] **Step 3: Record any backend limitations**

If Delusion/audio.cpp still has quality or similarity issues with the per-utterance clip approach, note that as a backend limitation rather than adding a second enrollment system.
