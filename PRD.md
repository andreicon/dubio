# PRD: Cartoon Dubbing Pipeline

## 1. Product Overview

### Working name

Cartoon Dubbing Pipeline

### Purpose

Build a local-first, modular video dubbing system designed specifically for animated content.

The system takes an existing video in a source language, identifies dialogue and speakers, translates the dialogue into a target language, synthesizes character-specific voices, fits generated speech to the original timeline, mixes the dubbed dialogue with the original music and sound effects, and produces a final dubbed video.

The first target language is Romanian.

The first target use case is English-language cartoons dubbed into Romanian.

### Core principle

The timeline is the source of truth.

Every piece of dialogue has an explicit start time, end time, speaker, source text, translated text, generated audio, and validation state.

TTS is an interchangeable component inside this pipeline. It does not control timing, speaker identity, mixing, or project state.

---

# 2. Problem Statement

Existing automated dubbing pipelines tend to combine transcription, diarization, translation, TTS, timing and audio composition into a single workflow.

This creates several problems:

* TTS output durations do not reliably match the original dialogue.
* Different generated voices have inconsistent loudness.
* Speaker identities can become ambiguous.
* Generated speech can overlap accidentally.
* Translation can produce dialogue substantially longer or shorter than the original.
* TTS language detection can fail on Romanian text containing diacritics.
* Regenerating a single bad line can require rerunning a large portion of the pipeline.
* Debugging becomes difficult because failures from different pipeline stages become indistinguishable.
* Original music and sound effects can be damaged or lost when replacing the dialogue track.

The new system must make each stage independently testable and replaceable.

---

# 3. Goals

## Primary goals

1. Produce high-quality Romanian cartoon dubbing from source video.
2. Preserve original music, ambience and sound effects wherever practical.
3. Assign stable voices to individual characters.
4. Maintain accurate dialogue timing.
5. Produce natural Romanian translations that respect available speaking time.
6. Normalize generated dialogue so voices have consistent perceived loudness.
7. Detect timing conflicts and overlapping dialogue.
8. Validate generated speech automatically.
9. Allow individual dialogue lines to be regenerated without rerunning the entire project.
10. Support multiple TTS engines through a common adapter interface.
11. Make failures observable and diagnosable.
12. Run locally on consumer GPU hardware where practical.

## Secondary goals

1. Support additional target languages later.
2. Support multiple TTS engines.
3. Support manual correction of transcription, speaker assignment and translation.
4. Support manual voice assignment.
5. Support batch processing of complete episodes.
6. Support deterministic project regeneration.
7. Make the pipeline suitable for eventual UI development.

---

# 4. Non-Goals

The initial version will not attempt to:

* Automatically reproduce the exact original actor performance.
* Generate original music or sound effects.
* Perform lip-sync animation.
* Modify character mouth movements.
* Create new video footage.
* Automatically determine the canonical identity of every cartoon character.
* Solve every possible language pair.
* Guarantee perfect emotional or comedic equivalence.
* Build a full web application before the processing pipeline is stable.

The first milestone is a reliable command-line pipeline that can produce a high-quality dubbed episode.

---

# 5. Design Principles

## 5.1 Timeline-first

Every utterance has an explicit source interval:

```text
start: 12.430
end:   15.870
duration: 3.440
```

The generated speech must be evaluated against that interval.

## 5.2 Modular engines

ASR, diarization, translation and TTS must be replaceable independently.

The application must not contain model-specific logic outside the corresponding adapter.

## 5.3 Intermediate artifacts are first-class

Every processing stage produces inspectable artifacts.

Examples:

```text
source.wav
dialogue.wav
music.wav
sfx.wav
transcript.json
diarization.json
translation.json
tts/
mix/
validation/
```

## 5.4 Never silently repair important errors

If two utterances overlap, the pipeline should report the overlap.

If Romanian language detection fails, the pipeline should report it.

If generated speech is substantially longer than the source interval, the pipeline should report it.

Automatic correction can exist, but the original problem must remain observable.

## 5.5 Regenerate locally

Changing one utterance should only regenerate the artifacts affected by that utterance.

## 5.6 TTS is disposable

No other subsystem should depend directly on Fish S2 Pro.

Fish S2 Pro should be one implementation of:

```python
class TTSEngine:
    def synthesize(...)
```

A different model should be installable without rewriting the pipeline.

---

# 6. High-Level Architecture

```text
                         SOURCE VIDEO
                              |
                              v
                    +-------------------+
                    | Media Extraction  |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Audio Separation  |
                    +---------+---------+
                              |
                +-------------+-------------+
                |                           |
                v                           v
        +---------------+           +---------------+
        |      ASR      |           | Audio Stems   |
        | Whisper/etc.  |           | Music / SFX   |
        +-------+-------+           +---------------+
                |
                v
        +---------------+
        |  Diarization  |
        +-------+-------+
                |
                v
        +----------------------+
        | Dialogue Timeline    |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Translation Engine   |
        | Duration constrained |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Character Voice Map  |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | TTS Engine           |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Audio Processing     |
        | EQ / compression     |
        | loudness / limiting  |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Timeline Validation  |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Audio Mixer          |
        | Dialogue + SFX/Music |
        +----------+-----------+
                   |
                   v
        +----------------------+
        | Video Renderer       |
        +----------+-----------+
                   |
                   v
                 OUTPUT
```

---

# 7. Project Data Model

The project is represented by a version-controlled manifest.

Example:

```json
{
  "project": {
    "id": "episode-001",
    "source": "source/episode.mp4",
    "source_language": "eng",
    "target_language": "ron"
  },

  "characters": {
    "speaker_00": {
      "name": "Character A",
      "voice": "voice_a"
    },
    "speaker_01": {
      "name": "Character B",
      "voice": "voice_b"
    }
  },

  "voices": {
    "voice_a": {
      "engine": "fish-s2-pro",
      "reference": "voices/character_a.wav",
      "pitch": 0,
      "gain_db": -1,
      "speaking_rate": 1.0
    }
  },

  "utterances": [
    {
      "id": "utt_000001",
      "speaker": "speaker_00",

      "source": {
        "text": "What are you doing?",
        "start": 12.430,
        "end": 15.870
      },

      "translation": {
        "text": "Ce faci?",
        "status": "approved"
      },

      "tts": {
        "engine": "fish-s2-pro",
        "voice": "voice_a",
        "file": "audio/tts/utt_000001.wav",
        "duration": 2.94
      },

      "mix": {
        "gain_db": -1.5,
        "pan": 0
      },

      "validation": {
        "language": "pass",
        "transcription": "pass",
        "duration": "pass",
        "loudness": "pass",
        "overlap": "pass"
      }
    }
  ]
}
```

The manifest is the authoritative representation of the dubbing project.

---

# 8. Pipeline Stages

## 8.1 Media extraction

Extract:

* source video metadata
* source audio
* sample rate
* channel count
* duration
* frame rate
* resolution

The system must preserve the original video stream where possible.

Video should not be re-encoded unless required by the final rendering process.

---

# 9. Audio Separation

The system should attempt to separate dialogue from music and sound effects.

Potential implementation:

* Demucs or equivalent source-separation model
* FFmpeg for media handling

Expected outputs:

```text
audio/
  source.wav
  dialogue.wav
  music.wav
  sfx.wav
```

The separation engine must be replaceable.

If source separation quality is insufficient, the pipeline must still permit operation using the original audio.

---

# 10. Automatic Speech Recognition

Initial ASR engine:

* Whisper large-v3 or an equivalent high-quality local model.

The ASR stage must provide:

* utterance text
* segment start
* segment end
* word timestamps where available
* language
* confidence information where available

Example:

```json
{
  "text": "What are you doing?",
  "start": 12.43,
  "end": 15.87,
  "words": [
    {
      "word": "What",
      "start": 12.43,
      "end": 12.71
    }
  ]
}
```

Word-level timestamps should be retained even if the first implementation only uses segment-level timing.

---

# 11. Speaker Diarization

The diarization stage assigns speaker IDs to dialogue segments.

Example:

```text
SPEAKER_00
SPEAKER_01
SPEAKER_00
SPEAKER_02
```

The system must retain the original speaker IDs independently from character names.

This distinction matters because:

```text
SPEAKER_00 -> Bugs
```

is a project-level mapping.

The diarization engine must not know that `SPEAKER_00` represents Bugs.

---

# 12. Character Mapping

After diarization, the user can map speakers to characters.

Example:

```text
SPEAKER_00 -> Bugs
SPEAKER_01 -> Daffy
SPEAKER_02 -> Granny
```

The mapping must be persisted in the project manifest.

A speaker may have a character assigned manually.

Automatic character identification can be added later.

---

# 13. Translation

The translation stage must be duration-aware.

The translation model receives:

```text
Source text
Source language
Target language
Available duration
Character context
Previous/following dialogue where useful
```

Example:

```text
Source:
"What on earth are you doing?"

Available duration:
2.85 seconds

Target:
Romanian

Character:
agitated
```

The translation system should prefer natural target-language dialogue that fits the available duration.

The translator should be able to produce multiple candidates.

Example:

```json
{
  "candidates": [
    {
      "text": "Ce faci?",
      "estimated_duration": 1.72
    },
    {
      "text": "Ce naiba faci?",
      "estimated_duration": 2.31
    },
    {
      "text": "Ce naiba faci acolo?",
      "estimated_duration": 2.94
    }
  ]
}
```

The selected translation becomes the source for TTS.

---

# 14. Romanian Language Handling

Romanian must be treated as a first-class language.

The pipeline must preserve:

```text
ă
â
î
ș
ț
```

through every processing stage.

No component should silently strip Romanian diacritics.

Text normalization must be explicit and reversible where practical.

The system must have a dedicated TTS test suite for Romanian.

Test cases should include:

```text
Ce faci?

Ce faci, băiete?

Băiatul merge la magazin.

Știu că ai fost acolo.

Ăsta este un test pentru limba română.

Îți spun că nu este adevărat.

Ține minte ce ți-am spus.
```

Each TTS engine must be evaluated against these cases before being accepted for production use.

---

# 15. TTS Engine Interface

All TTS engines must implement a common abstraction.

Example:

```python
class TTSEngine(Protocol):
    def synthesize(
        self,
        text: str,
        voice: VoiceProfile,
        language: str,
        instructions: dict,
    ) -> AudioArtifact:
        ...
```

The interface must support:

* text
* target language
* voice/reference
* speaking rate
* pitch
* style/instructions
* optional emotion
* optional pause controls

The output must include:

* audio file
* sample rate
* duration
* metadata
* engine identifier
* engine version/model

---

# 16. Initial TTS Engine: Fish S2 Pro

Fish S2 Pro is the initial candidate TTS engine.

It must be treated as an experimental engine until it passes the project's Romanian and voice-quality evaluation suite.

The integration must test:

1. Romanian text without diacritics.
2. Romanian text with diacritics.
3. Romanian punctuation.
4. Short utterances.
5. Long utterances.
6. Emotional instructions.
7. Reference voice consistency.
8. Pitch control.
9. Speaking-rate control.
10. Output loudness consistency.
11. Repeated synthesis consistency.

Fish-specific functionality must remain inside:

```text
engines/fish_s2.py
```

No Fish-specific assumptions should leak into:

```text
pipeline/timing.py
pipeline/mix.py
pipeline/validation.py
```

---

# 17. Voice Profiles

Each character receives a persistent voice profile.

Example:

```yaml
id: bugs
engine: fish-s2-pro
reference: voices/bugs.wav

parameters:
  pitch: 2
  speaking_rate: 1.0
  gain_db: -1.5

style:
  personality: mischievous
  energy: high
```

Voice profiles must be independent from speaker IDs.

This allows:

```text
SPEAKER_00 -> Bugs -> bugs_voice
```

and allows the same voice to be reused across episodes.

---

# 18. TTS Generation

Each utterance is synthesized independently.

Example:

```text
utt_000142
    |
    +-- speaker: SPEAKER_01
    +-- character: Daffy
    +-- voice: daffy_voice
    +-- text: "Ce faci acolo?"
    +-- target duration: 2.80s
    |
    v
TTS
    |
    v
utt_000142.wav
```

The system must not generate the entire episode as one TTS request.

Independent generation allows:

* line-level regeneration
* line-level validation
* easier timing correction
* different voices
* caching
* parallel processing

---

# 19. Duration Matching

Every generated utterance must be compared with the target interval.

```text
Target:
2.80 seconds

Generated:
3.21 seconds

Difference:
+0.41 seconds
```

The system should use a configurable tolerance.

Suggested initial thresholds:

```text
PASS:
generated duration <= target + 5%

WARNING:
target + 5% to target + 15%

FAIL:
> target + 15%
```

Equivalent thresholds should exist for speech that is substantially too short.

Duration correction may use:

1. TTS speaking-rate controls.
2. Translation regeneration.
3. Audio time-stretching.

The system should prefer linguistic/timing correction before aggressive audio time-stretching.

---

# 20. Timing Strategy

The original timeline remains authoritative.

For each utterance:

```text
original_start
original_end
target_duration
```

Generated audio is placed at:

```text
original_start
```

The generated audio must fit within the available interval.

The compositor must never silently move dialogue to another location on the timeline.

If timing cannot be satisfied, the utterance is marked as failed.

---

# 21. Overlap Detection

The system must detect overlapping dialogue.

Example:

```text
utt_001:
10.00 -> 13.00

utt_002:
12.50 -> 14.20
```

Output:

```text
OVERLAP DETECTED

utt_001
utt_002

overlap: 0.50 seconds
```

Overlaps may be intentional.

The project must allow:

```json
{
  "overlap": {
    "allowed": true
  }
}
```

Intentional overlaps should be explicitly marked.

Unmarked overlaps are validation warnings or failures depending on severity.

---

# 22. Audio Processing

Every generated dialogue clip must pass through a standard audio-processing chain.

Potential stages:

```text
TTS output
    |
    v
DC offset removal
    |
    v
High-pass filtering
    |
    v
EQ
    |
    v
Compression
    |
    v
Loudness normalization
    |
    v
True peak limiting
    |
    v
Timeline placement
```

The exact processing chain must be configurable.

The goal is consistent perceived loudness across characters and scenes.

TTS-generated amplitude must never be treated as trustworthy project-level mixing information.

---

# 23. Loudness Normalization

Every generated clip must have measured loudness metadata.

Example:

```json
{
  "integrated_lufs": -16.4,
  "true_peak_db": -1.2,
  "rms_db": -18.7
}
```

The project must define a target dialogue loudness.

Initial target:

```text
Dialogue: approximately -16 LUFS integrated
True peak: <= -1 dBTP
```

These values should be configurable.

Character-specific gain may be applied after normalization.

---

# 24. Audio Mixing

The final mix combines:

```text
Original music
+
Original SFX / ambience
+
Dubbed dialogue
```

The system should preserve original music and effects whenever possible.

Dialogue must occupy its own mix layer.

Example:

```text
mix/
  dialogue.wav
  music.wav
  sfx.wav
  final_mix.wav
```

The mixer must support:

* gain
* pan
* fades
* ducking
* per-character gain
* per-utterance gain
* timeline placement

Automatic music ducking may be introduced later.

---

# 25. Video Rendering

The final renderer should use FFmpeg.

Requirements:

* Preserve original video quality where possible.
* Replace or mux the original audio with the final dubbed mix.
* Avoid unnecessary video re-encoding.
* Support common source formats.
* Preserve frame rate and resolution.
* Produce a standard MP4 output.

Example:

```bash
dub render episode-001
```

Output:

```text
output/episode-001-ro.mp4
```

---

# 26. Validation System

Validation is a first-class pipeline stage.

Every utterance should receive a validation report.

Example:

```text
utt_000142

Language        PASS
Text match      PASS
Duration        PASS
Loudness        PASS
Peak            PASS
Overlap         PASS
Audio quality   PASS

Score: 96/100
```

---

# 27. TTS Text Validation

Generated speech should be transcribed again using ASR.

Example:

```text
Expected:
"Ce faci, băiete?"

Generated transcription:
"Ce faci băiete?"
```

The system should tolerate punctuation differences.

It should flag substantial lexical differences.

This catches:

* hallucinated words
* omitted words
* pronunciation problems
* language switching
* incorrect TTS input
* unexpected speech

---

# 28. Language Validation

The generated audio should be checked for target-language consistency.

For Romanian:

```text
Expected language: ro
Detected language: ro
```

A mismatch should generate a validation failure.

Language validation is particularly important for Fish S2 Pro and any future multilingual TTS engine.

---

# 29. Voice Consistency Validation

The system should eventually support speaker-embedding comparison.

For each character:

```text
reference voice
       |
       v
speaker embedding

generated utterance
       |
       v
speaker embedding

similarity score
```

This can detect cases where a TTS engine unexpectedly produces a voice substantially different from the character's configured voice.

This is a later milestone and is not required for the first MVP.

---

# 30. Quality Score

Each utterance receives a composite score.

Possible dimensions:

```text
Translation quality
Duration accuracy
Language correctness
ASR text similarity
Loudness consistency
Peak safety
Voice similarity
Overlap state
```

Example:

```json
{
  "score": 92,
  "checks": {
    "language": 1.0,
    "text_similarity": 0.97,
    "duration": 0.94,
    "loudness": 1.0,
    "voice_similarity": 0.86
  }
}
```

The exact scoring formula can evolve.

The system must retain raw measurements so the score can be recalculated later.

---

# 31. CLI

The first interface should be a command-line application.

Suggested commands:

```bash
dub init <project>

dub extract <project>

dub separate <project>

dub transcribe <project>

dub diarize <project>

dub translate <project>

dub voices <project>

dub synthesize <project>

dub validate <project>

dub mix <project>

dub render <project>

dub run <project>
```

Individual utterances must be addressable:

```bash
dub synthesize episode-001 --utterance utt_000142
```

Validation:

```bash
dub validate episode-001 --utterance utt_000142
```

Regeneration:

```bash
dub regenerate episode-001 --utterance utt_000142
```

---

# 32. Pipeline Resumability

Every stage must be resumable.

If the pipeline fails during TTS generation:

```bash
dub run episode-001
```

should reuse successful previous artifacts.

It must not regenerate completed work unless explicitly requested.

Artifacts should be associated with:

* stage
* input hash
* configuration hash
* engine/model version

This provides deterministic caching.

---

# 33. Caching

Generated artifacts must be cached.

The cache key should incorporate relevant inputs.

For TTS:

```text
hash(
    engine
    model version
    voice
    language
    text
    instructions
    relevant parameters
)
```

Changing the translation should invalidate the TTS artifact.

Changing unrelated utterances should not.

---

# 34. Parallelism

Independent utterances should be processed concurrently.

The TTS scheduler must support:

* configurable worker count
* GPU-aware scheduling
* queueing
* retries
* failure isolation
* progress reporting

GPU memory consumption must be configurable.

The system must avoid launching enough concurrent TTS jobs to exhaust VRAM.

---

# 35. Error Handling

Failures must be explicit.

Example:

```text
ERROR TTS-RO-001

Utterance:
utt_000142

Engine:
fish-s2-pro

Expected language:
ron

Detected language:
eng

Input:
"Ce faci, băiete?"

Output:
Language mismatch.

Suggested action:
Run Romanian TTS diagnostic suite.
```

Errors should have stable identifiers.

---

# 36. Observability

Every pipeline stage should emit structured logs.

Example:

```json
{
  "timestamp": "...",
  "project": "episode-001",
  "stage": "tts",
  "utterance": "utt_000142",
  "engine": "fish-s2-pro",
  "duration_ms": 4280,
  "status": "success"
}
```

The system should provide human-readable logs by default and JSON logs as an option.

---

# 37. Directory Structure

Suggested repository:

```text
cartoon-dubber/
│
├── README.md
├── PRD.md
├── pyproject.toml
│
├── src/
│   └── dub/
│       ├── cli.py
│       │
│       ├── pipeline/
│       │   ├── extract.py
│       │   ├── separate.py
│       │   ├── transcribe.py
│       │   ├── diarize.py
│       │   ├── translate.py
│       │   ├── voices.py
│       │   ├── synthesize.py
│       │   ├── timing.py
│       │   ├── normalize.py
│       │   ├── mix.py
│       │   ├── validate.py
│       │   └── render.py
│       │
│       ├── engines/
│       │   ├── asr/
│       │   ├── diarization/
│       │   ├── translation/
│       │   └── tts/
│       │       ├── base.py
│       │       ├── fish_s2.py
│       │       └── ...
│       │
│       ├── audio/
│       ├── models/
│       ├── project/
│       ├── validation/
│       └── utils/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── tts/
│
├── projects/
│   └── .gitkeep
│
└── docs/
    ├── architecture.md
    ├── tts-engines.md
    └── troubleshooting.md
```

---

# 38. Configuration

Global configuration should be separate from project configuration.

Example:

```yaml
hardware:
  device: cuda
  max_tts_workers: 1

asr:
  engine: whisper
  model: large-v3

diarization:
  engine: pyannote

translation:
  engine: configured-model

tts:
  engine: fish-s2-pro

audio:
  sample_rate: 48000
  target_lufs: -16
  true_peak_db: -1

timing:
  max_duration_ratio: 1.15
  warning_duration_ratio: 1.05
```

Project-specific overrides belong in the project manifest.

---

# 39. Hardware Target

Initial development environment:

```text
OS: Windows
CPU: AMD Ryzen 5 5600X
GPU: NVIDIA RTX 3070
VRAM: 8 GB
```

The architecture must support CUDA.

Models must be selected with VRAM constraints in mind.

GPU-intensive stages should avoid unnecessary model duplication.

The system should make it possible to move individual stages to another machine later.

---

# 40. Testing Strategy

## Unit tests

Test:

* manifest parsing
* manifest validation
* timeline calculations
* overlap detection
* duration calculations
* loudness metadata
* cache keys
* engine adapters
* configuration handling

## Integration tests

Test complete small pipelines using short audio/video fixtures.

## TTS tests

Every supported TTS engine must pass a standard test suite.

Test:

* Romanian
* Romanian diacritics
* short speech
* long speech
* punctuation
* numbers
* names
* emotional instructions
* reference voice
* duration
* loudness

## Regression tests

Known problematic utterances should become permanent fixtures.

Example:

```text
fixtures/tts/romanian/diacritics_001.txt
fixtures/tts/fish/failed_language_001.txt
```

A bug fixed once must have a regression test.

---

# 41. Development Milestones

## Milestone 0: TTS Research Harness

Before building the full pipeline, create a standalone TTS evaluation tool.

Input:

```text
text
language
voice reference
engine
```

Output:

```text
audio
duration
loudness
detected language
ASR transcription
```

The first goal is to establish whether Fish S2 Pro is actually suitable for Romanian.

This milestone must be completed before committing heavily to the TTS architecture.

---

## Milestone 1: Timeline Prototype

Build:

* media extraction
* Whisper transcription
* timeline manifest
* basic diarization
* manual speaker mapping

No TTS yet.

Deliverable:

```text
episode.mp4
    ↓
manifest.json
```

with accurate utterance timing.

---

## Milestone 2: Translation

Add:

* Romanian translation
* duration-aware translation
* multiple candidate translations
* manual translation editing

Deliverable:

```text
manifest.json
```

containing approved Romanian dialogue.

---

## Milestone 3: TTS

Add:

* TTS abstraction
* Fish S2 Pro adapter
* voice profiles
* per-utterance synthesis
* caching
* duration measurement

Deliverable:

```text
audio/tts/*.wav
```

---

## Milestone 4: Audio Processing

Add:

* normalization
* compression
* EQ
* limiting
* loudness analysis
* character gain

Deliverable:

```text
audio/processed/*.wav
```

---

## Milestone 5: Validation

Add:

* duration validation
* language validation
* ASR text validation
* loudness validation
* overlap detection
* validation reports

Deliverable:

```text
validation/report.json
validation/report.html
```

The HTML report is optional for the first implementation.

---

## Milestone 6: Mixing

Add:

* dialogue track
* music/SFX track
* timeline composition
* optional ducking
* final audio render

Deliverable:

```text
mix/final.wav
```

---

## Milestone 7: Final Video

Add:

* FFmpeg muxing
* final MP4 output
* metadata
* reproducible rendering

Deliverable:

```text
output/episode-001-ro.mp4
```

---

# 42. MVP Acceptance Criteria

The MVP is complete when the system can take a short cartoon scene and:

1. Extract the source audio.
2. Produce accurate source-language transcription.
3. Produce speaker-separated dialogue.
4. Map speakers to characters.
5. Translate dialogue into Romanian.
6. Preserve Romanian diacritics.
7. Generate character-specific Romanian speech.
8. Detect TTS language failures.
9. Measure generated duration.
10. Fit speech within the original timeline.
11. Detect unintended overlaps.
12. Normalize dialogue loudness.
13. Preserve original music and SFX.
14. Produce a final mixed audio track.
15. Produce a final MP4.
16. Regenerate a single utterance without rerunning the complete pipeline.
17. Resume processing after an interrupted run.
18. Produce enough diagnostic information to identify which stage failed.

---

# 43. Quality Targets

Initial targets:

### Timing

At least 90% of generated utterances should fall within ±10% of their target duration without aggressive time-stretching.

### Language

Romanian TTS should correctly interpret Romanian text containing:

```text
ă â î ș ț
```

for the supported TTS engine.

### Loudness

Dialogue clips should remain within a configurable loudness tolerance around the project target.

### Reliability

A failed individual utterance must not invalidate successfully generated utterances.

### Reproducibility

Running the same project with unchanged inputs and configuration should reuse cached artifacts.

---

# 44. Future Features

Potential later features:

* Web-based timeline editor.
* Waveform visualization.
* Subtitle-style dialogue editor.
* Manual drag-and-drop timing.
* Character voice preview.
* Automatic voice selection.
* Voice embedding analysis.
* Automatic overlap resolution.
* Automatic dialogue ducking.
* Emotion detection.
* Character emotion profiles.
* Scene-level context for translation.
* Automatic translation candidate ranking.
* Multi-language dubbing.
* Batch episode processing.
* Distributed GPU workers.
* Cloud TTS adapters.
* Human-in-the-loop review workflows.
* Automatic quality ranking of TTS engines.
* Lip-sync generation.
* Facial animation.
* Subtitle generation.
* Automatic chapter/scene detection.

---

# 45. Critical Technical Decisions

The following decisions are intentional:

### Open-Dubbing

Open-Dubbing is not the core orchestration framework.

Useful components and research may be reused, but the new pipeline owns the project manifest, timeline and orchestration.

### Fish S2 Pro

Fish S2 Pro is the initial TTS candidate.

It is not a hard dependency of the architecture.

### FFmpeg

FFmpeg is the primary media processing and rendering tool.

### Whisper

Whisper large-v3 is the initial ASR candidate.

### Source separation

Demucs or an equivalent engine is the initial source-separation candidate.

### Python

Python is the initial implementation language because the target ML ecosystem is Python-heavy.

### CLI first

The processing engine must stabilize before building a graphical interface.

---

# 46. First Implementation Task

Do not start by implementing the complete pipeline.

Start with:

```text
TTS Evaluation Harness
```

It should accept:

```bash
dub-tts-test \
  --engine fish-s2-pro \
  --language ro \
  --text "Ce faci, băiete?" \
  --reference voices/test.wav
```

and produce:

```text
result/
  audio.wav
  input.txt
  transcription.txt
  metrics.json
```

`metrics.json` should contain at minimum:

```json
{
  "engine": "fish-s2-pro",
  "language_expected": "ro",
  "language_detected": "ro",
  "duration_seconds": 2.31,
  "integrated_lufs": -16.2,
  "true_peak_db": -1.4,
  "transcription": "Ce faci, băiete?",
  "text_similarity": 0.98
}
```

Build the test harness first.

Use it to evaluate Fish S2 Pro with Romanian diacritics and several representative cartoon lines.

Only after that test passes should the full dubbing pipeline be implemented.

---

# 47. Definition of Done

A feature is considered complete when:

* It has a clear interface.
* It has unit tests.
* It produces inspectable artifacts.
* Errors are explicit.
* It can be rerun independently.
* It does not introduce engine-specific assumptions into unrelated pipeline stages.
* Its output is represented in the project manifest where appropriate.
* A failed operation does not corrupt previously successful pipeline stages.

The project is considered production-ready for the initial cartoon-dubbing use case when a complete episode can be processed from source video to final Romanian MP4 with minimal manual intervention, and individual problematic lines can be diagnosed and regenerated without restarting the project.
