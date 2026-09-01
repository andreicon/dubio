from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class HardwareCfg(BaseModel):
    device: str = "cuda"
    max_tts_workers: int = 1


class EngineCfg(BaseModel):
    engine: str
    model: str | None = None


class AudioCfg(BaseModel):
    sample_rate: int = 48000
    target_lufs: float = -16
    true_peak_db: float = -1


class TimingCfg(BaseModel):
    max_duration_ratio: float = 1.15
    warning_duration_ratio: float = 1.05


class Config(BaseModel):
    hardware: HardwareCfg = Field(default_factory=HardwareCfg)
    asr: EngineCfg = Field(default_factory=lambda: EngineCfg(engine="whisper", model="large-v3"))
    diarization: EngineCfg = Field(default_factory=lambda: EngineCfg(engine="pyannote"))
    translation: EngineCfg = Field(default_factory=lambda: EngineCfg(engine="llm"))
    tts: EngineCfg = Field(default_factory=lambda: EngineCfg(engine="fish-s2-pro"))
    audio: AudioCfg = Field(default_factory=AudioCfg)
    timing: TimingCfg = Field(default_factory=TimingCfg)


def load_config(path: Path | None) -> Config:
    if path is None:
        default = Path("config.yaml")
        if not default.exists():
            return Config()
        path = default
    data = yaml.safe_load(Path(path).read_text())
    return Config(**(data or {}))
