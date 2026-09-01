# Architecture

The pipeline runs in this order: `extract`, `separate`, `transcribe`, `diarize`, `translate`, `synthesize`, `normalize`, `validate`, `mix`, `render`.

`manifest.json` is the shared state between stages. Each stage updates it with the artifact metadata needed by later stages and by resumable runs.

Key outputs:
- `audio/source.wav` from `extract`
- `audio/transcript.json` from `transcribe`
- `audio/diarization.json` from `diarize`
- `translation.json` from `translate`
- `audio/tts/*.wav` from `synthesize`
- `audio/processed/*.wav` from `normalize`
- `validation/report.json` from `validate`
- `mix/final.wav` from `mix`
- `output/*-ro.mp4` from `render`
