# TTS Engines Evaluation

Task 6 Romanian gate outcome:
- PASS/FAIL: FAIL on opt-in GPU/model run
- Notes: default `pytest tests/tts/test_fish_romanian.py -v` deselected all 7 cases because GPU/model markers are excluded by default; opt-in `pytest -m "gpu and model" tests/tts/test_fish_romanian.py -v` failed on `ModuleNotFoundError: No module named 'fish_speech'` from the Fish adapter placeholder import.
