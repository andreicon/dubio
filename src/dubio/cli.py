from pathlib import Path

import typer

from dubio.config import load_config
from dubio.engines.diarization.fake import FakeDiarizer
from dubio.project.manifest import Manifest, Project
from dubio.project.paths import ProjectPaths
from dubio.pipeline.extract import extract
from dubio.pipeline.diarize import diarize
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
