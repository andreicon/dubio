from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from dubio.config import Config
from dubio.errors import DubError
from dubio.logging import get_logger
from dubio.pipeline.diarize import diarize
from dubio.pipeline.extract import extract
from dubio.pipeline.mix import mix_project
from dubio.pipeline.normalize import normalize_project
from dubio.pipeline.render import render
from dubio.pipeline.separate import separate
from dubio.pipeline.synthesize import synthesize_project
from dubio.pipeline.transcribe import transcribe
from dubio.pipeline.translate import translate_project
from dubio.pipeline.validate import validate_project
from dubio.project.paths import ProjectPaths

log = get_logger("run")


@dataclass(frozen=True)
class StageSpec:
    name: str
    artifact_check: Callable[[ProjectPaths], bool]
    func: Callable[[ProjectPaths, Config, dict], None]


def stage_complete(spec: StageSpec, paths: ProjectPaths) -> bool:
    try:
        return bool(spec.artifact_check(paths))
    except Exception:
        return False


STAGES: list[StageSpec] = [
    StageSpec("extract", lambda paths: (paths.audio_dir / "source.wav").exists(), lambda paths, config, engines: extract(paths, config)),
    StageSpec("separate", lambda paths: (paths.audio_dir / "music.wav").exists(), lambda paths, config, engines: separate(paths, engines["separator"], config)),
    StageSpec("transcribe", lambda paths: (paths.audio_dir / "transcript.json").exists(), lambda paths, config, engines: transcribe(paths, engines["asr"], config)),
    StageSpec("diarize", lambda paths: (paths.audio_dir / "diarization.json").exists(), lambda paths, config, engines: diarize(paths, engines["diarizer"], config)),
    StageSpec("translate", lambda paths: (paths.base / "translation.json").exists(), lambda paths, config, engines: translate_project(paths, engines["translator"], config)),
    StageSpec("synthesize", lambda paths: paths.tts_dir.exists() and any(paths.tts_dir.glob("utt_*.wav")), lambda paths, config, engines: synthesize_project(paths, engines["tts"], config)),
    StageSpec("normalize", lambda paths: paths.processed_dir.exists() and any(paths.processed_dir.glob("utt_*.wav")), lambda paths, config, engines: normalize_project(paths, config)),
    StageSpec("validate", lambda paths: (paths.validation_dir / "report.json").exists(), lambda paths, config, engines: validate_project(paths, engines["asr"], config)),
    StageSpec("mix", lambda paths: (paths.mix_dir / "final.wav").exists(), lambda paths, config, engines: mix_project(paths, config)),
    StageSpec("render", lambda paths: paths.output_dir.exists() and any(paths.output_dir.glob("*-ro.mp4")), lambda paths, config, engines: render(paths, config)),
]


def run(paths: ProjectPaths, config: Config, engines: dict, force_from: str | None = None) -> None:
    stage_names = {spec.name for spec in STAGES}
    if force_from is not None and force_from not in stage_names:
        raise DubError("RUN-002", f"unknown stage for --force-from: {force_from}", {"force_from": force_from, "stages": sorted(stage_names)})

    forcing = False

    for spec in STAGES:
        if spec.name == force_from:
            forcing = True

        if not forcing and stage_complete(spec, paths):
            log.info("stage_skipped", stage=spec.name)
            continue

        log.info("stage_start", stage=spec.name)
        try:
            spec.func(paths, config, engines)
        except DubError as exc:
            log.error("stage_failed", stage=spec.name, code=exc.code, message=exc.message)
            raise
        except Exception as exc:  # noqa: BLE001
            error = DubError("RUN-001", f"stage {spec.name} failed", {"stage": spec.name, "error": str(exc)})
            log.error("stage_failed", stage=spec.name, code=error.code, message=error.message)
            raise error from exc
        log.info("stage_done", stage=spec.name)
