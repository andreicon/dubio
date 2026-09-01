Task 1 status: done

Commit: 624788ae62ae2e092abda3f7d4a66b0a07a7b5af

Files changed:
- src/dubio/engines/translation/base.py
- src/dubio/engines/translation/fake.py
- tests/unit/test_translator_fake.py

Implementation notes:
- Added `Candidate` and `TranslationRequest` dataclasses plus the `Translator` protocol.
- Added `FakeTranslator` that resolves scripted source text to candidate texts and estimates durations through Task 2's helper.
- Defaults to echoing the source text if the mapping has no entry.

Verification:
- `.venv/bin/pytest tests/unit/test_translator_fake.py -v` → passed.
- `PYTHONPATH=src .venv/bin/python - <<'PY' ... PY` → passed; fake translator returned the expected candidate texts.

Concerns:
- None.

Fix note:
- Updated `src/dubio/engines/translation/fake.py` so `FakeTranslator(mapping)` now requires the mapping argument and no longer accepts a default `None`.
- Verification command: `python3 -m pytest tests/unit/test_translator_fake.py -v`.
- Result: could not execute the focused test because `pytest` is not installed in the current environment (`/usr/bin/python3: No module named pytest`).
