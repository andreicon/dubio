# Task 1 Report

## Status
Completed in the M6 worktree.

## Commit Hashes
Not committed.

## Fix Update
- Added `dubio separate` CLI wiring in `src/dubio/cli.py`.
- Added `--no-separate` support that routes through the existing fallback-to-source behavior.
- Kept the Demucs import lazy so the CLI still loads when the optional separation dependency is absent.
- Fixed the Demucs adapter to emit 48k stems and collapse non-vocal sources into `music` with an `sfx` approximation.
- Normalized hard separation failures to `DubError("SEP-001", ...)` with source context in the pipeline.

## Summary
- Added `dubio.engines.separation.base` with `Stems` and `SourceSeparator`.
- Added deterministic `FakeSeparator` that writes dialogue/music/sfx stems.
- Added a minimal `DemucsSeparator` adapter that wraps import/runtime failures as `DubError("SEP-001", ...)`.
- Added `dubio.pipeline.separate` with source fallback behavior that preserves dialogue and writes silent music/sfx stems.
- Added integration and GPU/model-marked unit coverage for the new interface.

## Test Summary
- `python3.12 -m compileall src tests` passed.
- `pytest` is not installed in the worktree interpreter, so I could not run the requested pytest targets in this environment.
- A direct `python3.12` CLI smoke check could not run because runtime dependencies like `typer` are also unavailable in the base interpreter.
- Re-ran syntax verification after the fix with `python3.12 -m compileall src tests`.

## Concerns
- The environment does not have `pytest` available, so the new tests were syntax-checked but not executed here.
- The Demucs adapter is intentionally thin and depends on the installed `demucs` API at runtime.
- The CLI smoke path still cannot be executed in this container because `typer` is not installed in the base interpreter.
