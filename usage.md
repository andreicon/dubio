# Usage

This project turns a short video into a dubbed Romanian MP4.

## Prerequisites

- Python environment with the project installed
- `ffmpeg`
- `ffprobe`

## Quick Start

If you have a file named `sample.mp4` in the repository root:

```bash
dubio init sample --source sample.mp4 --projects-root projects
```

That creates `projects/sample/manifest.json` and the project directory layout.

## Run The Pipeline

Run the stages one by one if you want to inspect each step:

```bash
dubio extract sample --projects-root projects
dubio transcribe sample --projects-root projects
dubio diarize sample --projects-root projects
dubio voices sample --projects-root projects --map SPEAKER_00=Bugs --map SPEAKER_01=Daffy
dubio translate sample --projects-root projects
dubio synthesize sample --projects-root projects
dubio normalize sample --projects-root projects
dubio validate sample --projects-root projects
dubio separate sample --projects-root projects
dubio mix sample --projects-root projects
dubio render sample --projects-root projects
```

If you want the pipeline to manage stage skipping for you:

```bash
dubio run sample --projects-root projects
```

To rerun from a specific stage onward:

```bash
dubio run sample --projects-root projects --force-from translate
```

## Regenerate One Utterance

If you only want to rebuild one line and remix the final audio:

```bash
dubio regenerate sample --projects-root projects --utterance utt_000001
```

## Outputs

For a project named `sample`, the main artifacts appear under:

```text
projects/sample/
  manifest.json
  audio/source.wav
  audio/transcript.json
  audio/diarization.json
  audio/tts/
  audio/processed/
  validation/report.json
  mix/final.wav
  output/sample-ro.mp4
```

## Notes

- `dubio run` reuses completed artifacts when they still match the current inputs and config.
- `dubio render` creates the final MP4 without re-encoding the video stream.
- `dubio regenerate` only rebuilds the chosen utterance, then recomposes the final mix.

## Common Config Tweaks

Start with `config.yaml` if you want to adjust the behavior for your machine or model choices.

- `asr.engine` and `asr.model` control transcription.
- `diarization.engine` controls speaker separation.
- `translation.engine` controls translation.
- `tts.engine` controls speech synthesis.
- `hardware.device` and `hardware.max_tts_workers` control runtime performance.
- `audio.sample_rate`, `audio.target_lufs`, and `audio.true_peak_db` control output audio normalization.
