What I implemented
- Added `dubio.validation.CheckResult` as the shared dataclass contract.
- Added numeric validators: `check_duration`, `check_overlaps`, `check_loudness`, and `check_peak`.
- `check_duration` uses `target_duration` and `duration_status` from the existing timing helpers.
- `check_overlaps` returns one `CheckResult` per offending pair and respects `overlap_allowed` through `find_overlaps`.
- `check_loudness` reads `Validation.measurements["loudness"]["integrated_lufs"]`.
- `check_peak` reads `Validation.measurements["loudness"]["true_peak_db"]`.
- Added `tests/unit/test_validators_numeric.py` covering duration pass, overlap filtering, loudness pass, and peak fail.

What I tested and results
- Attempted initial RED run before implementation: `pytest tests/unit/test_validators_numeric.py` failed because `pytest` was not installed in the environment.
- After bootstrapping an isolated venv and installing dependencies, focused validation tests passed: `python -m pytest tests/unit/test_validators_numeric.py` -> 5 passed.
- Relevant existing timing tests also passed: `python -m pytest tests/unit/test_timing.py` -> 3 passed.

TDD evidence
- RED: `python3 -m pytest tests/unit/test_validators_numeric.py` -> `ModuleNotFoundError: No module named 'pytest'` during collection before project deps were installed.
- GREEN: `/tmp/opencode/dubio-venv/bin/python -m pytest tests/unit/test_validators_numeric.py` -> `5 passed in 0.11s`.

Files changed
- `src/dubio/validation/__init__.py`
- `src/dubio/validation/duration.py`
- `src/dubio/validation/overlap.py`
- `src/dubio/validation/loudness.py`
- `src/dubio/validation/peak.py`
- `tests/unit/test_validators_numeric.py`

Self-review findings
- No code defects found in the new validator implementations.
- The overlap validator currently classifies short overlaps as `warning` and longer ones as `fail`, matching the existing task brief pattern.

Any issues or concerns
- The base container did not have `pytest` or project dependencies installed, so I verified in a local venv instead of the system interpreter.
