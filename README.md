# dubio

Automated local-first video dubbing with character voices, duration-aware translation, speech synthesis, audio mixing, and FFmpeg rendering.

> **Early development:** dubio is currently experimental. APIs, configuration, and processing stages are likely to change.

## What is dubio?

dubio takes a video in one language and produces a dubbed version in another.

The system handles transcription, speaker identification, translation, voice assignment, speech synthesis, audio processing, mixing, and final video rendering.

The project is built around the original dialogue timeline. Each piece of dialogue can be processed independently, making it possible to regenerate a single line, change a translation, swap a voice, or adjust audio without processing the entire video again.

The initial target is local GPU processing, with individual components kept replaceable so different ASR, translation, diarization, and TTS engines can be tested without rewriting the rest of the system.

## Design goals

* Run locally wherever practical.
* Keep the original video, music, and sound effects intact.
* Give characters stable, configurable voices.
* Treat timing as a first-class constraint.
* Generate speech one utterance at a time.
* Keep TTS engines interchangeable.
* Detect bad output instead of silently accepting it.
* Cache intermediate results.
* Resume interrupted jobs.
* Regenerate individual utterances without rerunning the whole pipeline.

## Current stack

The initial implementation is built around:

* Python
* FFmpeg
* Whisper for speech recognition
* speaker diarization
* Demucs or equivalent source separation
* Fish S2 Pro as the initial TTS engine
* CUDA for local GPU acceleration

These are implementation choices, not permanent dependencies. The processing system is designed around adapters so individual components can be replaced.

## Timing

dubio does not let generated speech define the timeline.

If the original dialogue occupies:

```text
12.430s → 15.870s
```

the target speech has a 3.440 second window.

The translation stage can take that constraint into account, and the TTS stage reports the actual generated duration.

Output that falls outside configured tolerances is flagged for review or further processing.

This is especially useful for languages where a literal translation can produce substantially longer dialogue than the source.

## Voices

(This section is under active development.)

Characters have persistent voice profiles rather than being tied directly to diarization IDs.

A speaker identified during transcription can be mapped to a character, and that character can have a configured voice, reference recording, pitch, speaking rate, gain, and other parameters. The `dubio voices` command now handles both mapping and Delusion voice enrollment when a reference WAV is supplied. 

This keeps speaker identification separate from voice selection and makes voice configuration reusable across projects.

## TTS

TTS is an isolated component of the processing system.

The current candidate is OmniVoice via Delusion, but the rest of dubio should not need to know which model produced the audio.

The TTS interface is intended to support:

* text
* language
* voice/reference audio
* speaking rate
* pitch
* style instructions
* emotion
* pause controls

Generated audio is processed and validated before it reaches the final mix.

## Audio

Generated dialogue passes through a configurable processing chain that can include:

* filtering
* EQ
* compression
* loudness normalization
* limiting
* per-character gain
* per-utterance gain

TTS output levels are measured rather than trusted.

The final mix combines generated dialogue with the retained music, effects, and ambience from the source.

## Validation

dubio validates generated speech before rendering the final video.

Checks include:

* target-language detection
* generated speech transcription
* text similarity
* duration
* loudness
* true peak
* dialogue overlaps
* voice consistency, where supported

A failed utterance should be isolated rather than poisoning the entire job.

The goal is to make it obvious whether a bad result came from transcription, translation, TTS, timing, or audio processing.

## Caching and resumability

Pipeline stages produce persistent intermediate artifacts.

A completed stage should not be rerun when its inputs and configuration have not changed.

Changing one dialogue line should not require regenerating the rest of the video.

The long-term goal is deterministic, content-aware caching across the processing pipeline.

## CLI

The CLI is the first interface to the processing engine.

If you use the local Delusion/audio.cpp TTS backend, set `AUDIOCPP_PATH` in your `.env` file to the `audiocpp_cli` binary. You can also run `./install_audiocpp_cli.sh` from the repository root first if you want the binary built locally; the adapter falls back to `audiocpp_cli` on `PATH`.

Planned commands:

```bash
dubio init <project>
dubio extract <project>
dubio separate <project>
dubio transcribe <project>
dubio diarize <project>
dubio translate <project>
dubio synthesize <project>
dubio validate <project>
dubio mix <project>
dubio render <project>
dubio run <project>
```

Individual utterances should be addressable for testing and regeneration.

The CLI is intentionally separate from the processing engine so a web interface can use the same pipeline later.

## Web interface

The long-term interface is intended to support a simple workflow:

1. Upload a video.
2. Select the source and target languages.
3. Start the dubbing job.
4. Track processing progress.
5. Review validation results.
6. Download the dubbed video.

The processing engine will run as an asynchronous job rather than inside the HTTP request.

This allows the same core system to support local CLI usage and a web application.

## Development status

dubio is being built incrementally.

Current priorities:

1. TTS evaluation harness.
2. Romanian TTS testing (my main language, native speaker, i only speak Romanian and English so I'll be focusing on these languages at first).
3. Timeline and processing state.
4. ASR and diarization.
5. Duration-aware translation.
6. TTS integration.
7. Audio processing and validation.
8. Mixing and rendering.
9. End-to-end video processing.
10. Web application.

The first major technical checkpoint is determining whether the selected TTS engines produce reliable speech for the target languages and voice profiles.

## Requirements

The initial development environment targets:

* NVIDIA GPU with CUDA support
* Python
* FFmpeg
* sufficient disk space for source and intermediate audio
* enough VRAM for the selected ML models

An 8 GB GPU is the initial development target, so model and worker configuration should account for constrained VRAM.

## License

TBD.

## Contributing

The project is currently under active development and the architecture is still changing.

Issues, experiments, model comparisons, and reproducible bug reports are welcome once the initial pipeline is established.
