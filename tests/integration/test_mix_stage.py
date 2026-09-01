import numpy as np
from typer.testing import CliRunner

from dubio.cli import app
from dubio.audio.measure import load_wav, write_wav
from dubio.config import Config
from dubio.project.manifest import Manifest, Project, SourceSpan, Utterance
from dubio.project.paths import ProjectPaths


def test_mix_cli_writes_mix_outputs_and_places_dialogue_at_offset(tmp_path, monkeypatch):
    paths = ProjectPaths(tmp_path, "ep1")
    manifest = Manifest(
        project=Project(id="ep1", source="source.mp4", source_language="eng", target_language="ron"),
        utterances=[
            Utterance(
                id="utt_000001",
                speaker="SPEAKER_00",
                source=SourceSpan(text="Hello", start=0.5, end=1.0),
            )
        ],
    )
    manifest.save(paths.manifest)

    paths.processed_dir.mkdir(parents=True, exist_ok=True)
    sr = 48000
    write_wav(paths.processed_dir / "utt_000001.wav", np.ones(int(0.1 * sr)) * 0.5, sr)
    write_wav(paths.audio_dir / "music.wav", np.zeros(sr), sr)
    write_wav(paths.audio_dir / "sfx.wav", np.zeros(sr), sr)

    from dubio import cli as cli_module

    cli_module.load_config = lambda path=None: Config(audio={"sample_rate": sr})

    result = CliRunner().invoke(app, ["mix", "ep1", "--projects-root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    dialogue, loaded_sr = load_wav(paths.mix_dir / "dialogue.wav")
    final, final_sr = load_wav(paths.mix_dir / "final.wav")

    assert loaded_sr == sr
    assert final_sr == sr
    assert (paths.mix_dir / "music.wav").exists()
    assert (paths.mix_dir / "sfx.wav").exists()
    assert (paths.mix_dir / "final.wav").exists()
    assert dialogue[int(0.5 * sr)] == 0.5
    assert dialogue[0] == 0.0
    assert final[int(0.5 * sr)] != 0.0
