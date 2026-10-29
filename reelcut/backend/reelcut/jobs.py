"""In-memory job registry + single background worker thread.

Jobs are also mirrored to <job_dir>/status.json so a restarted server can still serve finished results.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional

from .config import settings
from .schemas import JobRequest, JobStage, JobStatus

log = logging.getLogger(__name__)


@dataclass
class Job:
    id: str
    request: JobRequest
    src_path: Path
    dir: Path
    status: JobStatus
    output_path: Optional[Path] = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def update(self, stage: Optional[JobStage] = None, progress: Optional[float] = None, message: Optional[str] = None, **extra) -> None:
        with self.lock:
            if stage is not None:
                self.status.stage = stage
            if progress is not None:
                self.status.progress = max(0.0, min(1.0, progress))
            if message is not None:
                self.status.message = message
            for k, v in extra.items():
                setattr(self.status, k, v)
            (self.dir / "status.json").write_text(self.status.model_dump_json(indent=2))


class JobStore:
    def __init__(self, runner: Callable[[Job], None]):
        self._jobs: Dict[str, Job] = {}
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._runner = runner
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._loop, name="reelcut-worker", daemon=True)
        settings.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._restore()
        self._worker.start()

    # ------------------------------------------------------------------ public
    def create(self, request: JobRequest, suffix: str) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job_dir = settings.jobs_dir / job_id
        job_dir.mkdir(parents=True)
        job = Job(
            id=job_id,
            request=request,
            src_path=job_dir / f"input{suffix}",
            dir=job_dir,
            status=JobStatus(id=job_id, stage=JobStage.queued, progress=0.0, message="In Warteschlange"),
        )
        (job_dir / "request.json").write_text(request.model_dump_json(indent=2))
        with self._lock:
            self._jobs[job_id] = job
        return job

    def enqueue(self, job: Job) -> None:
        job.update(stage=JobStage.queued, progress=0.0)
        self._queue.put(job.id)

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    # ------------------------------------------------------------------ internals
    def _loop(self) -> None:
        while True:
            job_id = self._queue.get()
            job = self.get(job_id)
            if job is None:
                continue
            try:
                self._runner(job)
            except Exception as exc:  # noqa: BLE001 - anything from the pipeline ends up in the job status
                log.exception("job %s failed", job_id)
                job.update(stage=JobStage.failed, message="Fehlgeschlagen", error=str(exc)[:2000])
            finally:
                self._queue.task_done()

    def _restore(self) -> None:
        """Pick up finished jobs from disk so results survive a restart (unfinished ones are marked failed)."""
        for status_file in settings.jobs_dir.glob("*/status.json"):
            try:
                status = JobStatus.model_validate_json(status_file.read_text())
                request = JobRequest.model_validate_json((status_file.parent / "request.json").read_text())
            except Exception:  # noqa: BLE001
                continue
            job_dir = status_file.parent
            output = job_dir / "output.mp4"
            if status.stage != JobStage.done or not output.exists():
                if status.stage not in (JobStage.done, JobStage.failed):
                    status.stage = JobStage.failed
                    status.error = "server restarted during processing"
            src = next(iter(job_dir.glob("input.*")), job_dir / "input.mp4")
            self._jobs[status.id] = Job(id=status.id, request=request, src_path=src, dir=job_dir, status=status, output_path=output if output.exists() else None)
