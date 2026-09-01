from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
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
from dubio.project.manifest import Manifest
from dubio.utils.hashing import stable_hash

log = get_logger("run")


@dataclass(frozen=True)
class StageSpec:
    name: str
    artifact_check: Callable[[ProjectPaths], bool]
    func: Callable[[ProjectPaths, Config, dict], None]


def _run_state_dir(paths: ProjectPaths) -> Path:
    return paths.base / ".run"


def _stage_state_path(paths: ProjectPaths, spec: StageSpec) -> Path:
    return _run_state_dir(paths) / f"{spec.name}.json"


def _load_manifest(paths: ProjectPaths) -> Manifest:
    return Manifest.load(paths.manifest)


def _stat_payload(path: Path) -> dict | None:
    if not path.exists():
        return None
    stat = path.stat()
    return {"path": str(path), "mtime_ns": stat.st_mtime_ns, "size": stat.st_size}


def _current_fingerprint(spec_name: str, paths: ProjectPaths, config: Config) -> str:
    manifest = _load_manifest(paths)
    source = Path(manifest.project.source)
    audio_source = paths.audio_dir / "source.wav"
    music = paths.audio_dir / "music.wav"
    sfx = paths.audio_dir / "sfx.wav"
    transcript = paths.audio_dir / "transcript.json"
    diarization = paths.audio_dir / "diarization.json"
    translation = paths.base / "translation.json"
    voice_map = {speaker: character.voice for speaker, character in manifest.characters.items()}
    speaker_names = {speaker: character.name for speaker, character in manifest.characters.items()}
    utterance_inputs = [
        {
            "id": utterance.id,
            "speaker": utterance.speaker,
            "text": utterance.source.text,
            "start": utterance.source.start,
            "end": utterance.source.end,
        }
        for utterance in manifest.utterances
    ]

    if spec_name == "extract":
        payload = {
            "source": _stat_payload(source),
            "sample_rate": config.audio.sample_rate,
        }
    elif spec_name == "separate":
        payload = {
            "source_audio": _stat_payload(audio_source),
        }
    elif spec_name == "transcribe":
        payload = {
            "source_audio": _stat_payload(audio_source),
            "source_language": manifest.project.source_language,
            "asr": {"engine": config.asr.engine, "model": config.asr.model},
        }
    elif spec_name == "diarize":
        payload = {
            "source_audio": _stat_payload(audio_source),
            "diarization": {"engine": config.diarization.engine, "model": config.diarization.model},
        }
    elif spec_name == "translate":
        payload = {
            "transcript": _stat_payload(transcript),
            "diarization": _stat_payload(diarization),
            "source_language": manifest.project.source_language,
            "target_language": manifest.project.target_language,
            "speaker_names": speaker_names,
            "utterances": utterance_inputs,
            "translator": {"engine": config.translation.engine, "model": config.translation.model},
        }
    elif spec_name == "synthesize":
        payload = {
            "translation": _stat_payload(translation),
            "voice_map": voice_map,
            "voices": {voice_id: voice.model_dump(mode="json") for voice_id, voice in manifest.voices.items()},
            "tts": {"engine": config.tts.engine, "model": config.tts.model},
        }
    elif spec_name == "normalize":
        payload = {
            "tts_outputs": [_stat_payload(paths.tts_dir / f"{utt.id}.wav") for utt in manifest.utterances],
            "voice_map": voice_map,
            "mix": {utt.id: utt.mix.model_dump(mode="json") for utt in manifest.utterances},
            "audio": config.audio.model_dump(mode="json"),
        }
    elif spec_name == "validate":
        payload = {
            "processed_outputs": [_stat_payload(paths.processed_dir / f"{utt.id}.wav") for utt in manifest.utterances],
            "tts": [{"id": utt.id, "file": utt.tts.file, "duration": utt.tts.duration, "translation": utt.translation.text} for utt in manifest.utterances],
            "asr": {"engine": config.asr.engine, "model": config.asr.model},
        }
    elif spec_name == "mix":
        payload = {
            "music": _stat_payload(music),
            "sfx": _stat_payload(sfx),
            "processed_outputs": [_stat_payload(paths.processed_dir / f"{utt.id}.wav") for utt in manifest.utterances],
            "timeline": [{"id": utt.id, "start": utt.source.start, "end": utt.source.end} for utt in manifest.utterances],
            "audio": config.audio.model_dump(mode="json"),
        }
    elif spec_name == "render":
        payload = {
            "source_video": _stat_payload(source),
            "final_audio": _stat_payload(paths.mix_dir / "final.wav"),
        }
    else:
        payload = {"manifest": manifest.model_dump(mode="json")}

    return stable_hash(spec_name, payload)


def _load_stage_state(paths: ProjectPaths, spec: StageSpec) -> dict | None:
    state_path = _stage_state_path(paths, spec)
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text(encoding="utf-8"))


def _write_stage_state(paths: ProjectPaths, spec: StageSpec, config: Config) -> None:
    state_path = _stage_state_path(paths, spec)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"fingerprint": _current_fingerprint(spec.name, paths, config)}, indent=2), encoding="utf-8")


def record_stage_state(paths: ProjectPaths, config: Config, stage_name: str) -> None:
    for spec in STAGES:
        if spec.name == stage_name:
            _write_stage_state(paths, spec, config)
            return
    raise DubError("RUN-002", f"unknown stage for state recording: {stage_name}", {"stage": stage_name})


def _artifact_ready(spec: StageSpec, paths: ProjectPaths) -> bool:
    try:
        return bool(spec.artifact_check(paths))
    except Exception:
        return False


def stage_complete(spec: StageSpec, paths: ProjectPaths, config: Config | None = None) -> bool:
    if not _artifact_ready(spec, paths):
        return False
    if config is None:
        return True
    state = _load_stage_state(paths, spec)
    if not state:
        return False
    return state.get("fingerprint") == _current_fingerprint(spec.name, paths, config)


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

        if not forcing and stage_complete(spec, paths, config):
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
        _write_stage_state(paths, spec, config)
