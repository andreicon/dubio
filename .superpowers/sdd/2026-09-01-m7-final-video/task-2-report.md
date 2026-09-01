Status: completed and committed, with fix follow-up and explicit diarizer failure.

Files changed:
- `src/dubio/pipeline/run.py`
- `src/dubio/cli.py`
- `tests/integration/test_run_resume.py`

Commands run:
- `python3 -m pytest tests/integration/test_run_resume.py`
- `python3 -m compileall src tests`

Test results:
- `python3 -m pytest tests/integration/test_run_resume.py` could not run because `pytest` is not installed in this shell (`No module named pytest`).
- `python3 -m compileall src tests` passed and compiled the touched source and test files successfully.

Commits:
- `1d48e2a` `feat(run): add resumable orchestrator`
- `0fd4ad9` `fix(run): reject invalid force-from`
- `89b1168` `fix(cli): lazy-load diarizer fallback`
- `b9ccde4` `fix(cli): fail on unknown diarizer`

Final verification:
- `python3 -m compileall src tests` passed and compiled the touched source and test files successfully.
- The fix patch was applied and the invalid-stage test now asserts `DubError`.
- The lazy diarizer fallback was applied in `dubio run`.
- The CLI now raises `DubError` for unsupported diarization engines.

Concerns:
- Full pytest execution is still pending in an environment with `pytest` installed.
- The new `dubio run` command currently wires fake ASR/diarization plus the existing translation/TTS factories; that keeps the CLI thin, but the command still depends on whatever engines are available in the current environment.
