"""FFmpeg rendering: cut + concat segments, enhance picture and sound, burn the ASS captions.

Everything happens in ONE ffmpeg process (optionally preceded by a vidstab pass). ffmpeg runs with the
job directory as cwd and only relative, ASCII file names so no filtergraph path escaping is needed.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

from .config import settings
from .media import MediaError, MediaInfo
from .schemas import Enhance, Segment

log = logging.getLogger(__name__)

ProgressCb = Callable[[float], None]
_OUT_TIME = re.compile(r"out_time_us=(\d+)")


def _video_fit_chain(info: MediaInfo, w: int, h: int, fps: int) -> str:
    """Portrait sources are cropped to fill; landscape/square ones get a blurred copy as background."""
    if info.aspect <= 0.7:
        return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},format=yuv420p"
    return (
        f"split[bg][fg];"
        f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=24:6,eq=brightness=-0.08[bgb];"
        f"[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[fgs];"
        f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,fps={fps},format=yuv420p"
    )


def _enhance_video_chain(enh: Enhance) -> str:
    parts: List[str] = []
    if enh.color_boost > 0:
        sat = 1 + 0.45 * enh.color_boost
        con = 1 + 0.12 * enh.color_boost
        parts.append(f"eq=saturation={sat:.3f}:contrast={con:.3f}")
    if enh.sharpen:
        parts.append("unsharp=5:5:0.7:5:5:0.0")
    return ",".join(parts)


def _enhance_audio_chain(enh: Enhance) -> str:
    parts: List[str] = []
    if enh.denoise_audio:
        parts.append("afftdn=nf=-25")
    parts.append("highpass=f=70")
    if enh.loudness_normalize:
        parts.append("loudnorm=I=-14:TP=-1.5:LRA=11")
    parts.append("aresample=48000")
    return ",".join(parts)


def stabilize(src: Path, job_dir: Path, info: MediaInfo) -> Path:
    """Two-pass vidstab over the whole source. Slow; only used when the plan asks for it."""
    trf = "stab.trf"
    out = job_dir / "stabilized.mp4"
    base = [settings.ffmpeg_bin, "-y", "-v", "error", "-i", str(src)]
    subprocess.run(base + ["-vf", f"vidstabdetect=shakiness=5:accuracy=15:result={trf}", "-f", "null", "-"], cwd=job_dir, check=True)
    subprocess.run(
        base + ["-vf", f"vidstabtransform=input={trf}:smoothing=20:zoom=2,unsharp=5:5:0.5", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "copy", out.name],
        cwd=job_dir,
        check=True,
    )
    return out


def build_filter_graph(segments: List[Segment], info: MediaInfo, enh: Enhance, ass_file: str, fonts_dir: Optional[str]) -> str:
    w, h, fps = settings.output_width, settings.output_height, settings.output_fps
    audio_src = "[0:a]" if info.has_audio else "[1:a]"
    chains: List[str] = []
    for i, seg in enumerate(segments):
        chains.append(f"[0:v]trim=start={seg.start:.3f}:end={seg.end:.3f},setpts=PTS-STARTPTS[v{i}]")
        chains.append(f"{audio_src}atrim=start={seg.start:.3f}:end={seg.end:.3f},asetpts=PTS-STARTPTS[a{i}]")
    inputs = "".join(f"[v{i}][a{i}]" for i in range(len(segments)))
    chains.append(f"{inputs}concat=n={len(segments)}:v=1:a=1[vc][ac]")

    vchain = [_video_fit_chain(info, w, h, fps)]
    ev = _enhance_video_chain(enh)
    if ev:
        vchain.append(ev)
    ass = f"ass={ass_file}" + (f":fontsdir={fonts_dir}" if fonts_dir else "")
    vchain.append(ass)
    chains.append("[vc]" + ",".join(vchain) + "[vout]")
    chains.append("[ac]" + _enhance_audio_chain(enh) + "[aout]")
    return ";".join(chains)


def render(
    src: Path,
    job_dir: Path,
    info: MediaInfo,
    segments: List[Segment],
    enh: Enhance,
    ass_path: Path,
    out_path: Path,
    on_progress: Optional[ProgressCb] = None,
) -> Path:
    if enh.stabilize:
        try:
            src = stabilize(src, job_dir, info)
        except subprocess.CalledProcessError as exc:  # keep going without stabilisation
            log.warning("stabilisation failed, continuing without it: %s", exc)

    # ffmpeg only ever sees relative names -> no filtergraph escaping issues
    src_link = job_dir / ("source" + src.suffix.lower())
    if not src_link.exists():
        os.symlink(src.resolve(), src_link)
    fonts_dir_env = os.environ.get("REELCUT_FONTS_DIR")
    fonts_dir = None
    if fonts_dir_env and Path(fonts_dir_env).is_dir():
        link = job_dir / "fonts"
        if not link.exists():
            os.symlink(Path(fonts_dir_env).resolve(), link)
        fonts_dir = "fonts"

    graph = build_filter_graph(segments, info, enh, ass_path.name, fonts_dir)
    (job_dir / "filtergraph.txt").write_text(graph)
    total = sum(s.end - s.start for s in segments)

    cmd = [settings.ffmpeg_bin, "-y", "-v", "error", "-nostdin", "-progress", "pipe:1", "-i", src_link.name]
    if not info.has_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += [
        "-filter_complex",
        graph,
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-preset",
        settings.x264_preset,
        "-crf",
        str(settings.x264_crf),
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-shortest",
        out_path.name,
    ]
    log.info("ffmpeg render: %d segments, %.1fs output", len(segments), total)
    proc = subprocess.Popen(cmd, cwd=job_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        m = _OUT_TIME.match(line.strip())
        if m and on_progress and total > 0:
            on_progress(min(0.99, int(m.group(1)) / 1_000_000 / total))
    _, err = proc.communicate()
    if proc.returncode != 0:
        tail = "\n".join(err.strip().splitlines()[-20:])
        raise MediaError(f"ffmpeg render failed ({proc.returncode}):\n{tail}")
    if on_progress:
        on_progress(1.0)
    return out_path
