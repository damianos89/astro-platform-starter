"""ReelCut backend - FastAPI app used by the Android client.

    uvicorn reelcut.main:app --host 0.0.0.0 --port 8000

Endpoints
  POST /v1/jobs                multipart: video file + options  -> JobStatus
  GET  /v1/jobs/{id}           JobStatus (poll until stage == done|failed)
  GET  /v1/jobs/{id}/plan      the EditPlan Claude produced
  GET  /v1/jobs/{id}/result    the rendered mp4
  GET  /healthz
"""
from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import pipeline
from .config import settings
from .jobs import JobStore
from .schemas import EditPlan, JobRequest, JobStage, JobStatus, StylePreset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("reelcut")

app = FastAPI(title="ReelCut", version="0.1.0")
store = JobStore(pipeline.process_job)

_ALLOWED_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".3gp"}


def require_token(authorization: Optional[str] = Header(default=None)) -> None:
    if not settings.api_token:
        return
    expected = f"Bearer {settings.api_token}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="invalid token")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "planner": settings.planner_backend, "transcriber": settings.transcribe_backend, "model": settings.claude_model}


@app.post("/v1/jobs", response_model=JobStatus, dependencies=[Depends(require_token)])
async def create_job(
    file: UploadFile = File(...),
    preset: StylePreset = Form(StylePreset.freestyle_mix),
    target_duration: float = Form(0),
    instructions: str = Form(""),
    language: str = Form(""),
    add_hook_title: bool = Form(True),
) -> JobStatus:
    suffix = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=415, detail=f"unsupported file type {suffix}")
    request = JobRequest(preset=preset, target_duration=target_duration, instructions=instructions[:2000], language=language[:8], add_hook_title=add_hook_title)
    job = store.create(request, suffix)

    limit = settings.max_upload_mb * 1024 * 1024
    written = 0
    with job.src_path.open("wb") as out:
        while chunk := await file.read(4 * 1024 * 1024):
            written += len(chunk)
            if written > limit:
                out.close()
                pipeline.cleanup_job_dir(job.dir)
                raise HTTPException(status_code=413, detail=f"file larger than {settings.max_upload_mb} MB")
            out.write(chunk)
    log.info("job %s: received %s (%.1f MB)", job.id, file.filename, written / 1e6)
    store.enqueue(job)
    return job.status


@app.get("/v1/jobs/{job_id}", response_model=JobStatus, dependencies=[Depends(require_token)])
def get_job(job_id: str) -> JobStatus:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job.status


@app.get("/v1/jobs/{job_id}/plan", response_model=EditPlan, dependencies=[Depends(require_token)])
def get_plan(job_id: str) -> EditPlan:
    job = store.get(job_id)
    if job is None or job.status.plan is None:
        raise HTTPException(status_code=404, detail="plan not available yet")
    return job.status.plan


@app.get("/v1/jobs/{job_id}/result", dependencies=[Depends(require_token)])
def get_result(job_id: str) -> FileResponse:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status.stage != JobStage.done or not job.output_path or not job.output_path.exists():
        raise HTTPException(status_code=409, detail=f"job is {job.status.stage.value}")
    return FileResponse(job.output_path, media_type="video/mp4", filename=f"reelcut-{job_id}.mp4")
