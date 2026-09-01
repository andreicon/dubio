from pathlib import Path

import typer

from dubio.config import load_config
from dubio.engines.diarization.fake import FakeDiarizer
from dubio.engines.translation.fake import FakeTranslator
from dubio.engines.translation.llm import LLMTranslator
from dubio.harness.factory import build_tts
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths
from dubio.pipeline.extract import extract
from dubio.pipeline.diarize import diarize
from dubio.pipeline.synthesize import synthesize_project
from dubio.pipeline.translate import translate_project
from dubio.pipeline.voices import map_character
from dubio.pipeline.transcribe import transcribe

app = typer.Typer(help="Video Dubbing Pipeline")


@app.callback()
def main():
    """Video dubbing pipeline commands."""


@app.command()
def init(
    project: str = typer.Argument(...),
    source: str = typer.Option(...),
    source_lang: str = "eng",
    target_lang: str = "ron",
    projects_root: str = "projects",
):
    paths = ProjectPaths(Path(projects_root), project)
    manifest = Manifest(
        project=Project(
            id=project,
            source=source,
            source_language=source_lang,
            target_language=target_lang,
        )
    )
    manifest.save(paths.manifest)
    typer.echo(f"Initialized {paths.manifest}")


@app.command(name="extract")
def extract_cmd(project: str = typer.Argument(...), projects_root: str = "projects", config: str | None = None):
    paths = ProjectPaths(Path(projects_root), project)
    info = extract(paths, load_config(Path(config) if config else None))
    typer.echo(f"Extracted {paths.audio_dir / 'source.wav'} ({info.duration:.3f}s)")


@app.command(name="transcribe")
def transcribe_cmd(project: str = typer.Argument(...), projects_root: str = "projects"):
    from dubio.engines.asr.fake import FakeASR

    paths = ProjectPaths(Path(projects_root), project)
    transcribe(paths, FakeASR(), load_config(None))
    typer.echo(f"Transcribed {paths.audio_dir / 'transcript.json'}")


@app.command(name="diarize")
def diarize_cmd(project: str = typer.Argument(...), projects_root: str = "projects"):
    paths = ProjectPaths(Path(projects_root), project)
    diarize(paths, FakeDiarizer([]), load_config(None))
    typer.echo(f"Diarized {paths.audio_dir / 'diarization.json'}")


@app.command(name="voices")
def voices_cmd(
    project: str = typer.Argument(...),
    map: list[str] = typer.Option(None),
    projects_root: str = "projects",
):
    paths = ProjectPaths(Path(projects_root), project)
    manifest = Manifest.load(paths.manifest)
    for mapping in map or []:
        if "=" not in mapping:
            raise typer.BadParameter("Expected SPEAKER_00=Name")
        speaker_id, name = mapping.split("=", 1)
        map_character(manifest, speaker_id, name)
    manifest.save(paths.manifest)
    typer.echo(f"Updated {paths.manifest}")


def _build_translator(config, paths: ProjectPaths):
    engine = config.translation.engine
    if engine == "fake":
        return FakeTranslator({})
    if engine == "llm":
        import os
        import openai

        client = openai.OpenAI(
            base_url=os.environ.get("DUBIO_LLM_BASE_URL"),
            api_key=os.environ.get("DUBIO_LLM_API_KEY"),
        )
        return LLMTranslator(client=client, model=config.translation.model or os.environ.get("DUBIO_LLM_MODEL", "gpt-4o-mini"))
    raise typer.BadParameter(f"Unsupported translation engine: {engine}")


@app.command(name="translate")
def translate_cmd(
    project: str = typer.Argument(...),
    projects_root: str = "projects",
    utterance: str | None = typer.Option(None),
    set_text: str | None = typer.Option(None, "--set"),
    approve: bool = typer.Option(False, "--approve"),
):
    paths = ProjectPaths(Path(projects_root), project)
    manifest = Manifest.load(paths.manifest)

    if utterance is not None:
        target = manifest.get_utterance(utterance)
        if set_text is not None:
            target.translation.text = set_text
            target.translation.status = "edited"
        elif approve:
            target.translation.status = "approved"
        else:
            raise typer.BadParameter("Use --set or --approve with --utterance")
        manifest.save(paths.manifest)
        typer.echo(f"Updated {paths.manifest}")
        return

    config = load_config(None)
    translate_project(paths, _build_translator(config, paths), config)
    typer.echo(f"Translated {paths.manifest}")


@app.command(name="synthesize")
def synthesize_cmd(
    project: str = typer.Argument(...),
    projects_root: str = "projects",
    utterance: str | None = typer.Option(None),
    force: bool = typer.Option(False, "--force"),
): 
    paths = ProjectPaths(Path(projects_root), project)
    config = load_config(None)
    tts_kwargs = {}
    if config.tts.model is not None:
        tts_kwargs["model_version"] = config.tts.model
    if config.tts.engine == "fish-s2-pro":
        tts_kwargs["device"] = config.hardware.device
    synthesize_project(
        paths,
        build_tts(config.tts.engine, out_dir=paths.tts_dir, **tts_kwargs),
        config,
        force=force,
        utterance_id=utterance,
    )
    typer.echo(f"Synthesized {paths.manifest}")
