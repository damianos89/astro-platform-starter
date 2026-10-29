"""Runtime configuration, read from environment variables (see backend/.env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # Where uploads, intermediate files and rendered videos are stored.
    work_dir: Path = field(default_factory=lambda: Path(os.environ.get("REELCUT_WORK_DIR", "./data")))
    # Shared secret the Android app sends as "Authorization: Bearer <token>". Empty = no auth (dev only).
    api_token: str = field(default_factory=lambda: os.environ.get("REELCUT_API_TOKEN", ""))
    max_upload_mb: int = field(default_factory=lambda: int(os.environ.get("REELCUT_MAX_UPLOAD_MB", "500")))

    # Claude
    claude_model: str = field(default_factory=lambda: os.environ.get("REELCUT_CLAUDE_MODEL", "claude-opus-5-5"))
    claude_effort: str = field(default_factory=lambda: os.environ.get("REELCUT_CLAUDE_EFFORT", "high"))
    # "claude" uses the API; "heuristic" never calls Claude (offline/dev mode, used by the tests).
    planner_backend: str = field(default_factory=lambda: os.environ.get("REELCUT_PLANNER", "claude"))

    # Transcription: "whisper" (faster-whisper, local) or "mock" (tests / dev without a model download).
    transcribe_backend: str = field(default_factory=lambda: os.environ.get("REELCUT_TRANSCRIBER", "whisper"))
    whisper_model: str = field(default_factory=lambda: os.environ.get("REELCUT_WHISPER_MODEL", "small"))
    whisper_device: str = field(default_factory=lambda: os.environ.get("REELCUT_WHISPER_DEVICE", "cpu"))
    whisper_compute_type: str = field(default_factory=lambda: os.environ.get("REELCUT_WHISPER_COMPUTE", "int8"))

    # Rendering
    ffmpeg_bin: str = field(default_factory=lambda: os.environ.get("REELCUT_FFMPEG", "ffmpeg"))
    ffprobe_bin: str = field(default_factory=lambda: os.environ.get("REELCUT_FFPROBE", "ffprobe"))
    output_width: int = field(default_factory=lambda: int(os.environ.get("REELCUT_OUT_W", "1080")))
    output_height: int = field(default_factory=lambda: int(os.environ.get("REELCUT_OUT_H", "1920")))
    output_fps: int = field(default_factory=lambda: int(os.environ.get("REELCUT_OUT_FPS", "30")))
    x264_preset: str = field(default_factory=lambda: os.environ.get("REELCUT_X264_PRESET", "medium"))
    x264_crf: int = field(default_factory=lambda: int(os.environ.get("REELCUT_X264_CRF", "20")))
    keep_intermediates: bool = field(default_factory=lambda: _env_bool("REELCUT_KEEP_INTERMEDIATES", False))

    @property
    def jobs_dir(self) -> Path:
        return self.work_dir / "jobs"


settings = Settings()
