"""The processing pipeline for one job: probe -> transcribe -> plan (Claude) -> captions -> render."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from . import captions, media, planner, render, transcribe
from .config import settings
from .jobs import Job
from .schemas import JobStage
from .timeline import Timeline

log = logging.getLogger(__name__)


def process_job(job: Job) -> Path:
    job_dir = job.dir
    job.update(stage=JobStage.probing, progress=0.02, message="Video wird analysiert")
    info = media.probe(job.src_path)
    log.info("job %s: %.1fs %dx%d audio=%s", job.id, info.duration, info.width, info.height, info.has_audio)

    job.update(stage=JobStage.transcribing, progress=0.08, message="Sprache wird transkribiert")
    wav = job_dir / "audio.wav"
    if info.has_audio:
        media.extract_audio(job.src_path, wav)
        transcript = transcribe.transcribe(wav, info.duration, job.request.language or None)
    else:
        transcript = transcribe.Transcript(language=job.request.language or "de", duration=info.duration, words=[])
    (job_dir / "transcript.json").write_text(transcript.model_dump_json(indent=2))

    job.update(stage=JobStage.planning, progress=0.35, message="Claude plant Schnitt und Untertitel")
    try:
        plan = planner.make_plan(transcript, job.request)
    except planner.PlannerError:
        raise
    except Exception as exc:  # noqa: BLE001 - API/network trouble: fall back so the user still gets a video
        if settings.planner_backend != "claude":
            raise
        log.exception("Claude planning failed, using heuristic plan")
        plan = planner.sanitize_plan(planner.plan_heuristic(transcript, job.request), transcript)
        plan.summary = f"Fallback-Plan (Claude nicht erreichbar: {type(exc).__name__}). " + plan.summary
    (job_dir / "plan.json").write_text(plan.model_dump_json(indent=2))
    timeline = Timeline(plan.keep_segments)
    job.update(progress=0.45, plan=plan, output_duration=round(timeline.output_duration, 2))

    job.update(stage=JobStage.rendering, progress=0.5, message="Video wird gerendert")
    ass_path = job_dir / "captions.ass"
    ass_path.write_text(captions.build_ass(plan, timeline, hook_title=job.request.add_hook_title), encoding="utf-8")
    out_path = job_dir / "output.mp4"

    def on_progress(frac: float) -> None:
        job.update(progress=0.5 + 0.49 * frac)

    render.render(job.src_path, job_dir, info, plan.keep_segments, plan.enhance, ass_path, out_path, on_progress)
    job.output_path = out_path
    job.update(stage=JobStage.done, progress=1.0, message="Fertig", result_url=f"/v1/jobs/{job.id}/result")

    if not settings.keep_intermediates:
        for name in ("audio.wav", "stabilized.mp4", "stab.trf"):
            p = job_dir / name
            if p.exists():
                p.unlink()
    return out_path


def cleanup_job_dir(job_dir: Path) -> None:
    shutil.rmtree(job_dir, ignore_errors=True)
