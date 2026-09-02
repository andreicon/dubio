# Delusion Voice Cloning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `dubio voices` enroll Delusion/audio.cpp voice references end-to-end so a mapped speaker can synthesize with a cloned reference voice.

**Architecture:** Keep `dubio voices` as the single public entrypoint. Extend the existing speaker-to-character mapping step so it can also attach or update a voice profile with Delusion reference audio and optional metadata, then make synthesis consume that stored voice profile without any extra enrollment command. Preserve engine-agnostic manifest storage so non-Delusion voices still work the same way.

**Tech Stack:** Python 3.12, Typer CLI, Pydantic models in `src/dubio/project/manifest.py`, YAML/JSON manifest storage, Delusion/audio.cpp CLI via `AUDIOCPP_PATH` or `PATH`, pytest.

**Spec:** `PRD.md` (§17 Voice Profiles, §18 TTS Generation, §32 Pipeline Resumability, §33 Caching, §34 Parallelism)

## Global Constraints

- `dubio voices` remains the public command for speaker mapping.
- Voice profiles stay independent from speaker IDs and are stored in the manifest.
- Delusion/audio.cpp synthesis must keep working through the existing `AUDIOCPP_PATH` / `PATH` resolution.
- Do not add a separate enrollment command in v1.
- Preserve current behavior for non-Delusion voices.

---

### Task 1: Extend voice mapping data flow for Delusion enrollment

**Files:**
- Modify: `src/dubio/pipeline/voices.py:1-7`
- Modify: `src/dubio/cli.py:82-96`
- Test: `tests/unit/test_voice_profiles.py`

**Interfaces:**
- Consumes: `map_character(manifest, speaker_id, name, voice=None)` and `Manifest.voices`
- Produces: `map_character(..., voice=None, reference=None, engine=None, parameters=None)` or a similarly explicit extension that can attach a voice profile when the caller supplies Delusion enrollment data

- [ ] **Step 1: Write the failing test**

Add a unit test that calls the mapping helper with a speaker name plus Delusion enrollment data and asserts both are persisted:

```python
def test_map_character_can_enroll_voice_profile():
    manifest = Manifest(project=Project(id="ep1", source="s.mp4", source_language="eng", target_language="ron"))

    map_character(
        manifest,
        "SPEAKER_00",
        "Bugs",
        voice="bugs_ro",
        reference="voices/bugs.wav",
        engine="delusion",
    )

    assert manifest.characters["SPEAKER_00"].voice == "bugs_ro"
    assert manifest.voices["bugs_ro"].engine == "delusion"
    assert manifest.voices["bugs_ro"].reference == "voices/bugs.wav"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/unit/test_voice_profiles.py -k enroll`

Expected: FAIL because the mapping helper does not yet accept or persist enrollment fields.

- [ ] **Step 3: Write minimal implementation**

Update `map_character()` to accept optional voice-enrollment fields and store them in `manifest.voices[voice]` when present. Keep the existing behavior when only `speaker_id`, `name`, and `voice` are supplied.

```python
def map_character(manifest, speaker_id: str, name: str, voice: str | None = None, reference: str | None = None, engine: str | None = None, parameters: dict | None = None) -> None:
    manifest.characters[speaker_id] = Character(name=name, voice=voice)
    if voice and (reference is not None or engine is not None or parameters is not None):
        manifest.voices[voice] = Voice(
            engine=engine or manifest.voices.get(voice, Voice(engine="fake")).engine,
            reference=reference,
            pitch=(parameters or {}).get("pitch", manifest.voices.get(voice, Voice(engine="fake")).pitch),
            speaking_rate=(parameters or {}).get("speaking_rate", manifest.voices.get(voice, Voice(engine="fake")).speaking_rate),
            gain_db=(parameters or {}).get("gain_db", manifest.voices.get(voice, Voice(engine="fake")).gain_db),
        )
```

Keep the implementation straightforward and do not introduce a separate voice registry class.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/unit/test_voice_profiles.py -k enroll`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dubio/pipeline/voices.py src/dubio/cli.py tests/unit/test_voice_profiles.py
git commit -m "feat: enroll delusion voices via map"
```

### Task 2: Thread Delusion enrollment options through the CLI

**Files:**
- Modify: `src/dubio/cli.py:82-96`
- Test: `tests/integration/test_voice_mapping.py` (create if it does not exist)

**Interfaces:**
- Consumes: CLI `dubio voices <project>`
- Produces: `dubio voices` accepting optional Delusion-specific enrollment flags, at minimum a reference WAV path and the voice id to store on the manifest

- [ ] **Step 1: Write the failing test**

Add an integration test that creates a manifest with no voices, invokes the CLI with a Delusion enrollment flag, and asserts the manifest now has both the character mapping and a populated `manifest.voices[...]` entry.

```python
def test_voices_command_enrolls_delusion_reference(tmp_path):
    ...
    result = CliRunner().invoke(
        app,
        [
            "voices",
            "ep1",
            "--projects-root",
            str(tmp_path),
            "--map",
            "SPEAKER_00=Bugs",
            "--voice",
            "SPEAKER_00=bugs_ro",
            "--reference",
            "voices/bugs.wav",
        ],
    )
    assert result.exit_code == 0, result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/integration/test_voice_mapping.py -k enroll`

Expected: FAIL because the CLI does not yet accept or wire the new enrollment arguments.

- [ ] **Step 3: Write minimal implementation**

Add only the CLI options needed for the v1 flow and pass them through to `map_character()`; keep the public command as `dubio voices`.

```python
@app.command(name="voices")
def voices_cmd(
    project: str = typer.Argument(...),
    map: list[str] = typer.Option(None),
    voice: list[str] = typer.Option(None),
    reference: str | None = typer.Option(None),
    projects_root: str = "projects",
):
    ...
```

Parse `--voice SPEAKER_00=bugs_ro` the same way `--map` is parsed, and only apply enrollment data when the matching speaker is present. If `reference` is provided, store it on the voice profile.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/integration/test_voice_mapping.py -k enroll`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dubio/cli.py tests/integration/test_voice_mapping.py
git commit -m "feat: add delusion voice enrollment flags"
```

### Task 3: Make Delusion synthesis consume the enrolled reference voice

**Files:**
- Modify: `src/dubio/engines/tts/delusion.py`
- Modify: `src/dubio/pipeline/synthesize.py` only if needed for reference forwarding consistency
- Test: `tests/integration/test_synthesize.py`

**Interfaces:**
- Consumes: manifest voice profiles created by Task 1 and Task 2
- Produces: Delusion synthesis using the stored reference audio when a voice profile has one

- [ ] **Step 1: Write the failing test**

Add a test that builds a voice profile with `engine="delusion"` and `reference="tests/fixtures/voices/test.wav"`, stubs the Delusion backend, and asserts the backend is invoked with the reference-bearing voice profile.

```python
def test_delusion_synthesis_uses_reference_voice(monkeypatch, tmp_path):
    ...
    assert voice.reference == "tests/fixtures/voices/test.wav"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/python -m pytest tests/integration/test_synthesize.py -k reference`

Expected: FAIL if the adapter is not yet forwarding reference-backed voices through the Delusion path.

- [ ] **Step 3: Write minimal implementation**

Ensure the Delusion adapter keeps using the `voice.reference` field from the manifest voice profile and does not require a separate voice cloning command. If the underlying `delusion` library needs a model path or reference transcription later, keep that wiring behind the same `VoiceProfile` fields rather than adding new command concepts.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/bin/python -m pytest tests/integration/test_synthesize.py -k reference`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dubio/engines/tts/delusion.py src/dubio/pipeline/synthesize.py tests/integration/test_synthesize.py
git commit -m "feat: wire delusion reference voices"
```

### Task 4: Update docs and command examples for the new enrollment flow

**Files:**
- Modify: `usage.md`
- Modify: `commands.md`
- Modify: `README.md` only if the voice workflow needs a short note there

**Interfaces:**
- Consumes: the final `dubio voices` CLI shape from Tasks 1 and 2
- Produces: docs that show mapping and enrollment in one command and describe the Delusion reference-voice requirement clearly

- [ ] **Step 1: Write the failing doc check**

Add or update a small doc-focused test only if the repo already has a pattern for it; otherwise skip a doc test and verify by direct file inspection after editing.

- [ ] **Step 2: Update docs**

Update the example command in `commands.md` and `usage.md` to show the Delusion enrollment form, for example:

```bash
dubio voices edhonour --projects-root projects --map SPEAKER_00=Bugs --voice SPEAKER_00=bugs_ro --reference voices/bugs.wav
```

Clarify that `dubio voices` now both assigns the speaker mapping and enrolls the Delusion reference voice when reference data is supplied.

- [ ] **Step 3: Verify docs are consistent with code**

Check that the docs match the final CLI flags exactly and that no obsolete enrollment command is mentioned.

- [ ] **Step 4: Commit**

```bash
git add usage.md commands.md README.md
git commit -m "docs: describe delusion voice enrollment"
```

### Task 5: End-to-end verification

**Files:**
- No code changes unless verification exposes a concrete bug

**Interfaces:**
- Consumes: the full `dubio voices` + `dubio synthesize` flow
- Produces: a verified end-to-end voice cloning path for Delusion/audio.cpp

- [ ] **Step 1: Run the focused tests**

Run:

```bash
./.venv/bin/python -m pytest tests/unit/test_voice_profiles.py tests/integration/test_voice_mapping.py tests/integration/test_synthesize.py
```

Expected: PASS.

- [ ] **Step 2: Run the real pipeline slice**

Run the smallest real project slice that exercises enrollment and synthesis with Delusion, using the repo’s configured `AUDIOCPP_PATH` and the existing `edhonour` project or a dedicated fixture project.

Expected: `dubio voices` creates the cloned voice profile and `dubio synthesize` completes without the earlier `VOICE-001`, `TTS-RO-001`, or sample-rate mismatch failures.

- [ ] **Step 3: Capture remaining gaps**

If Delusion still cannot produce acceptable cloned speech, record the concrete backend limitation and stop there rather than adding new abstractions.
