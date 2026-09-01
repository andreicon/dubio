# Task 2 Report

## What I changed
- Added `src/dubio/pipeline/normalize.py` with:
  - `process_clip(samples, sr, chain_cfg, target_lufs, true_peak_db)`
  - `normalize_utterance(m, utt, paths, config)`
  - `normalize_project(paths, config)`
- Wired `dubio normalize <project> [--utterance utt_X]` into `src/dubio/cli.py`.
- Added `tests/integration/test_normalize_stage.py` to cover real WAV processing, loudness metadata persistence, and CLI single-utterance normalization.

## Files touched
- `src/dubio/pipeline/normalize.py`
- `src/dubio/cli.py`
- `tests/integration/test_normalize_stage.py`

## Tests run
- `python3 -m compileall src/dubio/pipeline/normalize.py src/dubio/cli.py tests/integration/test_normalize_stage.py`
- Attempted `python3 -m pytest tests/integration/test_normalize_stage.py -q`
- Attempted a direct runtime check via `python3` for the normalize path

## Output summary
- `compileall` succeeded for all touched Python files.
- `pytest` could not run because `pytest` is not installed in this environment.
- The direct runtime check could not execute because the environment is also missing project runtime dependencies such as `numpy`.

## Concerns
- The normalize implementation was verified for syntax, but not fully executed end-to-end in this container because required Python packages are unavailable.
- The CLI command currently normalizes either a single utterance or the whole manifest and persists the manifest after processing.
