"""Thin ffprobe/ffmpeg helpers."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .config import settings


class MediaError(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 1.0


def run(cmd: List[str], cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-15:]
        raise MediaError(f"{cmd[0]} failed ({proc.returncode}):\n" + "\n".join(tail))
    return proc


def probe(path: Path) -> MediaInfo:
    proc = run(
        [
            settings.ffprobe_bin,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    data = json.loads(proc.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        raise MediaError("no video stream found")
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
    if duration <= 0:
        raise MediaError("could not determine duration")
    num, _, den = (video.get("avg_frame_rate") or "30/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    width, height = int(video["width"]), int(video["height"])
    # Respect rotation metadata (phone footage is often stored landscape + rotate=90).
    rotation = 0
    for sd in video.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = int(float(sd["rotation"]))
    if video.get("tags", {}).get("rotate"):
        rotation = int(float(video["tags"]["rotate"]))
    if abs(rotation) % 180 == 90:
        width, height = height, width
    return MediaInfo(duration=duration, width=width, height=height, fps=fps or 30.0, has_audio=has_audio)


def extract_audio(src: Path, dst_wav: Path) -> Path:
    """16 kHz mono PCM, what Whisper expects."""
    run(
        [
            settings.ffmpeg_bin,
            "-y",
            "-v",
            "error",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(dst_wav),
        ]
    )
    return dst_wav
