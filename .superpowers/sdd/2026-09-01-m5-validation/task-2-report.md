# Task 2 Report: Language & Re-ASR Text Validators

## What I implemented
- Added `src/dubio/validation/language.py` with `check_language(utt, asr, expected="ro")`.
- Added `src/dubio/validation/text.py` with `check_text(utt, asr, sim_threshold=0.80)`.
- Added `tests/unit/test_validators_asr.py` covering language mismatch, punctuation-tolerant text match, and lexical drift.
- `check_language` reads `utt.tts.file`, calls `asr.detect_language`, and fails on exact mismatch.
- `check_text` reads `utt.tts.file`, re-transcribes with `asr.transcribe(..., language="ro")`, compares against `utt.translation.text` with `text_similarity`, and fails below the similarity threshold.

## What I tested and results
- Focused red/green verification:
  - RED command: `python3 -m pytest tests/unit/test_validators_asr.py`
  - RED result: could not run directly because system Python had no `pytest`; installed dev deps into `/tmp/opencode/dubio-venv` and then ran tests there.
  - GREEN command: `/tmp/opencode/dubio-venv/bin/pytest tests/unit/test_validators_asr.py`
  - GREEN result: `3 passed`
- Additional verification:
  - `/tmp/opencode/dubio-venv/bin/pytest tests/unit`
  - Result: `46 passed, 2 skipped`

## TDD evidence
- RED: `python3 -m pytest tests/unit/test_validators_asr.py` -> `No module named pytest`
- GREEN: `/tmp/opencode/dubio-venv/bin/pytest tests/unit/test_validators_asr.py` -> `3 passed`

## Files changed
- `src/dubio/validation/language.py`
- `src/dubio/validation/text.py`
- `tests/unit/test_validators_asr.py`
- `.superpowers/sdd/2026-09-01-m5-validation/task-2-report.md`

## Self-review findings
- Removed an unnecessary fallback from `check_text` so it uses `utt.translation.text` exactly as specified.
- Kept the implementation minimal and aligned with existing validator patterns.

## Issues or concerns
- No functional concerns after verification.
- Test execution required a temporary virtual environment because system Python did not have `pytest` installed.
