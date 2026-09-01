# Cartoon Dubbing Pipeline — Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement each milestone plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first, modular, timeline-first CLI pipeline that dubs English cartoons into Romanian, preserving music/SFX and producing a final MP4.

**Architecture:** A single JSON manifest per project is the source of truth. A Typer CLI (`dub <stage> <project>`) drives independent, resumable, cache-keyed stages. Every ML capability (ASR, diarization, translation, TTS, source-separation) lives behind a `Protocol` interface in `engines/<kind>/base.py` with a deterministic `fake` adapter for tests and a real GPU adapter for production. `pipeline/` orchestrates stages and never imports a concrete engine.

**Tech Stack:** Python 3.12, Typer (CLI), pydantic v2 (manifest), FFmpeg (media/render), faster-whisper/openai-whisper (ASR), pyannote.audio (diarization), Demucs (separation), Fish S2 Pro (TTS, experimental), pyloudnorm + soundfile + numpy + scipy + FFmpeg loudnorm (audio), an OpenAI-compatible LLM endpoint (translation), structlog (logging), pytest (+ markers `gpu`, `model`) for tests.

**Spec:** `PRD.md` (repository root). This plan argues from the PRD; executors read both.

---

## Global Constraints

These apply to **every** task in every milestone plan. Values are copied verbatim from the PRD.

- **Runtime:** Python 3.12. Package `dub` under `src/` layout. Build via `pyproject.toml`.
- **Tests:** `pytest`. Heavy tests marked `@pytest.mark.gpu` and/or `@pytest.mark.model`. Default CI runs `pytest -m "not gpu and not model"`. Every non-trivial function ships with unit tests. TDD: failing test first.
- **Manifest is authoritative** (PRD §7). All stage outputs recorded in `manifest.json`. Modeled with pydantic v2. Round-trips must preserve Romanian diacritics.
- **Romanian diacritics `ă â î ș ț` must survive every stage** (PRD §14). No component silently strips them. Shared fixture list of 7 canonical lines reused across ASR/translation/TTS/validation tests.
- **Engine isolation** (PRD §5.2, §16): no engine-specific logic outside its adapter. `pipeline/*.py` imports only interfaces from `engines/*/base.py`. Modules `pipeline/timing.py`, `pipeline/mix.py`, `pipeline/validate.py` must contain zero Fish/Whisper/pyannote assumptions.
- **Never silently repair important errors** (PRD §5.4): overlaps, language-detection failures, and over-long speech are always reported even if auto-corrected.
- **Regenerate locally** (PRD §5.5): changing one utterance regenerates only its affected artifacts.
- **Determinism & caching** (PRD §32–33): every artifact keyed by `hash(stage, input_hash, config_hash, engine_id, engine_version)`. Stages are resumable and idempotent; completed work is not redone unless forced.
- **Errors** (PRD §35): stable string identifiers (e.g. `TTS-RO-001`), structured payload, suggested action. A failed operation never corrupts previously successful artifacts (PRD §47).
- **Observability** (PRD §36): every stage emits structured logs via structlog; human-readable by default, `--json-logs` optional.
- **Audio defaults** (PRD §23, §38): 48000 Hz, target −16 LUFS integrated, true peak ≤ −1 dBTP. All configurable.
- **Config** (PRD §38): global `config.yaml` (hardware/engines/audio/timing) is separate from per-project manifest overrides.
- **Definition of Done** (PRD §47): clear interface, unit tests, inspectable artifacts, explicit errors, independently rerunnable, no cross-stage engine leakage, output represented in manifest, failures non-corrupting.

---

## Repository / File Structure

Established in M0 Task 0 and extended by later milestones (mirrors PRD §37).

```
cartoon-dubber/                 (== repo root; currently /root/workspace/dubbingV2)
├── PRD.md
├── README.md                   (created M0)
├── pyproject.toml              (created M0)
├── config.yaml                 (created M0 — global config)
├── src/dub/
│   ├── __init__.py             (__version__)
│   ├── cli.py                  (Typer app: dub <stage>)
│   ├── logging.py              (structlog setup)
│   ├── errors.py               (DubError + stable IDs)
│   ├── config.py               (global config loader)
│   ├── pipeline/
│   │   ├── extract.py  separate.py  transcribe.py  diarize.py
│   │   ├── translate.py  voices.py  synthesize.py  timing.py
│   │   ├── normalize.py  mix.py  validate.py  render.py  run.py
│   ├── engines/
│   │   ├── asr/{base,fake,whisper}.py
│   │   ├── diarization/{base,fake,pyannote}.py
│   │   ├── translation/{base,fake,llm}.py
│   │   ├── separation/{base,fake,demucs}.py
│   │   └── tts/{base,fake,fish_s2}.py
│   ├── audio/{measure,process}.py
│   ├── project/{manifest,voices,paths}.py
│   ├── validation/{duration,overlap,loudness,peak,language,text,score}.py
│   ├── harness/tts_eval.py
│   └── utils/{romanian,cache,scheduler,similarity,hashing}.py
├── tests/{unit,integration,fixtures,tts}/
├── projects/.gitkeep
└── docs/{architecture.md,tts-engines.md,troubleshooting.md}
```

---

## Milestones (build in order)

| # | Plan file | Deliverable | Gate |
|---|-----------|-------------|------|
| M0 | `2026-09-01-m0-tts-research-harness.md` | `dub-tts-test` harness + Fish Romanian eval report | **Fish must pass Romanian eval before M3** |
| M1 | `2026-09-01-m1-timeline-prototype.md` | `episode.mp4 → manifest.json` with accurate timing | — |
| M2 | `2026-09-01-m2-translation.md` | manifest with approved Romanian dialogue | — |
| M3 | `2026-09-01-m3-tts.md` | `audio/tts/*.wav` per-utterance | needs M0 gate |
| M4 | `2026-09-01-m4-audio-processing.md` | `audio/processed/*.wav` normalized | — |
| M5 | `2026-09-01-m5-validation.md` | `validation/report.json` | — |
| M6 | `2026-09-01-m6-mixing.md` | `mix/final.wav` | — |
| M7 | `2026-09-01-m7-final-video.md` | `output/<id>-ro.mp4` + `dub run`/`regenerate` | MVP acceptance §42 |

**Milestone 0 is the first implementation task (PRD §46) and must complete before heavy TTS investment.** M1 and M2 can proceed in parallel with M0 since they use fake engines; M3 depends on the M0 Fish gate.

---

## PRD → Milestone Coverage Map

- §7 manifest → M1 T1. §8 extract → M1 T3. §9 separation → M6 T1. §10 ASR → M1 T4. §11–12 diarize/mapping → M1 T5–T6.
- §13 translation → M2. §14 Romanian → Foundation T0.3 + reused everywhere. §15–16 TTS interface/Fish → M0.
- §17 voice profiles → M3 T1. §18 per-utterance synth → M3 T3. §19 duration matching → M3 T5.
- §20 timing → M1 T7 / M6 T2. §21 overlap → M1 T7 / M5 T1. §22–23 audio/loudness → M4. §24 mix → M6. §25 render → M7 T1.
- §26 validation → M5 T3. §27 text validation → M5 T2. §28 language validation → M5 T2. §29 voice consistency → deferred (future). §30 score → M5 T3.
- §31 CLI → distributed across milestones. §32 resume → M7 T2. §33 cache → M3 T2. §34 parallelism → M3 T4.
- §35 errors → Foundation T0.1. §36 observability → Foundation T0.1. §40 testing → every task. §42 acceptance → M7 T3. §46 first task → M0.
- §29 voice-embedding consistency, §44 future features → explicitly out of MVP scope.

---

## Execution Handoff

Execute milestone plans **in numeric order**. For each milestone, use superpowers:subagent-driven-development (fresh subagent per task + review) or superpowers:executing-plans (inline batch with checkpoints). Do not begin M3 until the M0 Fish Romanian evaluation report exists and is reviewed.
