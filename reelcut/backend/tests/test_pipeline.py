"""End-to-end test with a synthetic video, the mock transcriber and the heuristic planner (no API key needed)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("REELCUT_TRANSCRIBER", "mock")
os.environ.setdefault("REELCUT_PLANNER", "heuristic")
os.environ.setdefault("REELCUT_X264_PRESET", "ultrafast")

from reelcut import captions, media, planner, transcribe  # noqa: E402
from reelcut.schemas import (  # noqa: E402
    Animation,
    Caption,
    CaptionSize,
    CaptionStyle,
    EditPlan,
    Enhance,
    FontFamily,
    JobRequest,
    Position,
    Segment,
    StylePreset,
    Transcript,
    Word,
)
from reelcut.timeline import Timeline, normalize_segments  # noqa: E402


def make_video(path: Path, seconds: float = 8, size: str = "720x1280", audio: bool = True) -> Path:
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30:duration={seconds}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=44100:duration={seconds}"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    if audio:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += [str(path)]
    subprocess.run(cmd, check=True)
    return path


# ----------------------------------------------------------------------------- unit


def test_normalize_segments_merges_and_clamps():
    segs = normalize_segments([Segment(start=5, end=9), Segment(start=-1, end=2), Segment(start=1.9, end=3), Segment(start=20, end=30)], duration=10)
    assert [(s.start, s.end) for s in segs] == [(0.0, 3.0), (5.0, 9.0)]


def test_timeline_mapping():
    tl = Timeline([Segment(start=2, end=4), Segment(start=6, end=9)])
    assert tl.output_duration == 5
    assert tl.to_output(3) == 1
    assert tl.to_output(5) is None
    assert tl.map_range(3.5, 7) == (2.0, 3.0)  # longest surviving piece (6-7 in segment 2) wins
    assert tl.map_range(4.5, 5.5) is None


def test_ass_colour_conversion():
    assert captions.ass_color("#FF8800") == "&H000088FF"
    assert captions.ass_color("#000000", alpha=0x80) == "&H80000000"


def test_sanitize_drops_cut_captions_and_fixes_colours():
    transcript = Transcript(duration=10, words=[Word(text="a", start=1, end=1.5)])
    plan = EditPlan(
        title="  Hallo   Welt ",
        summary="",
        keep_segments=[Segment(start=0, end=5)],
        captions=[
            Caption(start=1, end=2, text="drin", style=CaptionStyle(fill_color="red")),
            Caption(start=7, end=8, text="weg"),
        ],
    )
    clean = planner.sanitize_plan(plan, transcript)
    assert clean.title == "Hallo Welt"
    assert [c.text for c in clean.captions] == ["drin"]
    assert clean.captions[0].style.fill_color == "#FFFFFF"


def test_heuristic_plan_removes_fillers_and_mixes_styles():
    transcript = transcribe.transcribe_mock(Path("/nonexistent.wav"), duration=20, language="de")
    plan = planner.make_plan(transcript, JobRequest(preset=StylePreset.freestyle_mix, target_duration=0))
    assert plan.keep_segments
    assert plan.captions
    assert all("Ähm" not in c.text for c in plan.captions)
    fonts = {c.style.font for c in plan.captions}
    assert len(fonts) >= 2, "freestyle preset should mix fonts"
    # trailing silence (last 10 %) is cut
    assert plan.keep_segments[-1].end < transcript.duration


def test_build_ass_contains_styles_and_events():
    tl = Timeline([Segment(start=0, end=10)])
    plan = EditPlan(
        title="Hook Titel",
        summary="",
        keep_segments=tl.segments,
        captions=[
            Caption(start=1, end=2, text="Krasser Look hier", emphasis_words=["Krasser"], animation=Animation.pop, position=Position.lower),
            Caption(start=2.1, end=3, text="wort für wort", animation=Animation.typewriter, style=CaptionStyle(font=FontFamily.mono, box=True, uppercase=False)),
            Caption(start=3.1, end=4, text="{geschweift}", emoji="🔥", animation=Animation.slide_up, position=Position.top, style=CaptionStyle(size=CaptionSize.huge, rotation_deg=5)),
        ],
    )
    ass = captions.build_ass(plan, tl)
    assert ass.count("Style: S") == 4  # 3 caption styles + title style
    assert ass.count("Dialogue:") == 4
    assert r"\k" in ass and r"\move(" in ass and r"\fscx70" in ass
    assert "{" not in ass.split("[Events]")[1].replace("{\\", "") and "(GESCHWEIFT)" in ass  # braces escaped, uppercase applied
    assert "KRASSER" in ass


# ----------------------------------------------------------------------------- integration


@pytest.mark.parametrize("size,audio", [("720x1280", True), ("1280x720", False)])
def test_full_render(tmp_path: Path, size: str, audio: bool):
    src = make_video(tmp_path / "in.mp4", seconds=8, size=size, audio=audio)
    info = media.probe(src)
    assert abs(info.duration - 8) < 0.3
    assert info.has_audio is audio

    transcript = transcribe.transcribe_mock(tmp_path / "audio.wav", duration=info.duration, language="de")
    plan = planner.make_plan(transcript, JobRequest(preset=StylePreset.freestyle_mix, target_duration=5))
    plan.enhance = Enhance(denoise_audio=True, loudness_normalize=True, sharpen=True, color_boost=0.4)
    tl = Timeline(plan.keep_segments)
    assert tl.output_duration <= 5 * 1.15 + 0.5

    ass_path = tmp_path / "captions.ass"
    ass_path.write_text(captions.build_ass(plan, tl), encoding="utf-8")
    from reelcut import render

    progress = []
    out = render.render(src, tmp_path, info, plan.keep_segments, plan.enhance, ass_path, tmp_path / "out.mp4", progress.append)
    assert out.exists() and out.stat().st_size > 10_000
    assert progress and progress[-1] == 1.0

    out_info = media.probe(out)
    assert (out_info.width, out_info.height) == (1080, 1920)
    assert out_info.has_audio
    assert abs(out_info.duration - tl.output_duration) < 0.6
    # the filtergraph really burns the subtitles and applies enhancement
    graph = (tmp_path / "filtergraph.txt").read_text()
    assert "ass=captions.ass" in graph and "loudnorm" in graph and "unsharp" in graph
    if size == "1280x720":
        assert "boxblur" in graph  # landscape -> blurred background


def test_job_store_and_api(tmp_path: Path, monkeypatch):
    """Spin the FastAPI app up in-process and run one job through the real worker thread."""
    monkeypatch.setenv("REELCUT_WORK_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("REELCUT_API_TOKEN", "secret")
    import importlib

    from reelcut import config

    importlib.reload(config)
    from reelcut import jobs, main, pipeline, render

    importlib.reload(jobs)
    importlib.reload(render)
    importlib.reload(pipeline)
    importlib.reload(main)
    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    src = make_video(tmp_path / "in.mp4", seconds=6)
    assert client.get("/healthz").json()["ok"] is True
    assert client.get("/v1/jobs/nope").status_code == 401  # token required

    headers = {"Authorization": "Bearer secret"}
    with src.open("rb") as f:
        r = client.post("/v1/jobs", files={"file": ("in.mp4", f, "video/mp4")}, data={"preset": "bold_pop", "target_duration": "4"}, headers=headers)
    assert r.status_code == 200, r.text
    job_id = r.json()["id"]

    import time

    deadline = time.time() + 120
    status = r.json()
    while status["stage"] not in ("done", "failed") and time.time() < deadline:
        time.sleep(0.5)
        status = client.get(f"/v1/jobs/{job_id}", headers=headers).json()
    assert status["stage"] == "done", json.dumps(status, indent=2)
    assert status["plan"]["captions"]
    assert status["output_duration"] <= 4 * 1.15 + 0.5

    res = client.get(f"/v1/jobs/{job_id}/result", headers=headers)
    assert res.status_code == 200 and res.headers["content-type"] == "video/mp4" and len(res.content) > 10_000
    assert client.get(f"/v1/jobs/{job_id}/plan", headers=headers).json()["keep_segments"]
