from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from dubio.config import Config
from dubio.errors import DubError
from dubio.project.manifest import Manifest
from dubio.project.paths import ProjectPaths


@dataclass
class MediaInfo:
    sample_rate: int
    channels: int
    duration: float
    fps: float
    width: int
    height: int
    video_codec: str


def probe(path) -> MediaInfo:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DubError("FFMPEG-002", "ffprobe failed", {"path": str(path)})

    data = json.loads(result.stdout)
    video = next((stream for stream in data["streams"] if stream["codec_type"] == "video"), {})
    audio = next((stream for stream in data["streams"] if stream["codec_type"] == "audio"), {})
    num, den = (video.get("r_frame_rate", "0/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den) else 0.0

    return MediaInfo(
        int(audio.get("sample_rate", 0)),
        int(audio.get("channels", 0)),
        float(data["format"]["duration"]),
        round(fps, 3),
        int(video.get("width", 0)),
        int(video.get("height", 0)),
        video.get("codec_name", ""),
    )


def extract_audio(source, out_wav, sr: int = 48000) -> Path:
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", str(sr), str(out_wav)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DubError("FFMPEG-001", "audio extraction failed", {"source": str(source)})
    return out_wav


def extract(paths: ProjectPaths, config: Config) -> MediaInfo:
    manifest = Manifest.load(paths.manifest)
    info = probe(manifest.project.source)
    extract_audio(manifest.project.source, paths.audio_dir / "source.wav", sr=config.audio.sample_rate)
    media_info_path = paths.audio_dir / "media_info.json"
    media_info_path.parent.mkdir(parents=True, exist_ok=True)
    media_info_path.write_text(json.dumps(info.__dict__, indent=2), encoding="utf-8")
    return info
