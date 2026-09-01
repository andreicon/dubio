# Troubleshooting

Stable error IDs:

| Code | Stage | Meaning |
| --- | --- | --- |
| `FFMPEG-001` | `extract` | Audio extraction failed |
| `FFMPEG-002` | `extract` | Probe failed |
| `SEP-001` | `separate` | Source separation failed |
| `TRANS-001` | `translate` | Translation request failed |
| `VOICE-001` | `synthesize` | No voice mapped for a speaker |
| `TTS-RO-001` | `synthesize` | Romanian TTS failed |
| `MIX-001` | `mix` | Dialogue clip placement failed |
| `RENDER-001` | `render` | Final video render failed |

If a run stops early, check `validation/report.json`, the stage logs, and the manifest for the last completed artifact. The `run` command reuses existing artifacts and only reruns stages that are missing or forced.
