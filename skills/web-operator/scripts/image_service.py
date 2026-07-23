#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["fastapi", "uvicorn"]
# ///
"""Local FastAPI service that queues image-generation jobs and runs them
serially through the site generate-image scripts over the host Chrome CDP.

Jobs run one at a time. Callers can observe queue position and cancel jobs.
Queue state is in-memory: a restart drops pending jobs, generated files stay.

Entry point: omp web-operator image-serve [--port 8320] [--out-dir PATH]
"""

import argparse
import asyncio
import json
import os
import signal
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

OMP_HOME = Path(os.environ.get("OMP_HOME", Path.home() / ".oh-my-superpowers"))
SITES_DIR = Path(__file__).resolve().parent / "sites"
DEFAULT_OUT_DIR = OMP_HOME / "data" / "chatgpt-images"
DEFAULT_JOB_TIMEOUT_SEC = 180
MAX_HISTORY = 200

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELED = "canceled"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Job:
    def __init__(self, prompt: str, site: str, timeout_sec: int, out_path: Path):
        self.id = uuid.uuid4().hex[:12]
        self.prompt = prompt
        self.site = site
        self.timeout_sec = timeout_sec
        self.out_path = out_path
        self.status = QUEUED
        self.created_at = now_iso()
        self.started_at: Optional[str] = None
        self.finished_at: Optional[str] = None
        self.result: Optional[dict] = None
        self.error: Optional[str] = None


class JobQueue:
    """Serial job queue. Pure state machine; process execution is injected."""

    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.order: list[str] = []  # submission order, all jobs ever seen

    def submit(self, job: Job) -> None:
        self.jobs[job.id] = job
        self.order.append(job.id)
        self._trim_history()

    def next_queued(self) -> Optional[Job]:
        for job_id in self.order:
            job = self.jobs[job_id]
            if job.status == QUEUED:
                return job
        return None

    def position(self, job: Job) -> Optional[int]:
        """Jobs ahead of this one (running job counts as 1). None if not waiting."""
        if job.status == RUNNING:
            return 0
        if job.status != QUEUED:
            return None
        ahead = sum(
            1
            for job_id in self.order
            if self.jobs[job_id].status in (QUEUED, RUNNING)
            and self.order.index(job_id) < self.order.index(job.id)
        )
        return ahead

    def cancel(self, job: Job) -> bool:
        """Cancel a queued job. Running jobs are canceled by the worker (kill)."""
        if job.status == QUEUED:
            job.status = CANCELED
            job.finished_at = now_iso()
            return True
        return False

    def queue_length(self) -> int:
        return sum(1 for j in self.jobs.values() if j.status in (QUEUED, RUNNING))

    def _trim_history(self) -> None:
        finished = [
            job_id
            for job_id in self.order
            if self.jobs[job_id].status in (DONE, FAILED, CANCELED)
        ]
        excess = len(finished) - MAX_HISTORY
        for job_id in finished[:max(0, excess)]:
            self.order.remove(job_id)
            del self.jobs[job_id]


def job_view(queue: JobQueue, job: Job) -> dict:
    return {
        "job_id": job.id,
        "status": job.status,
        "position": queue.position(job),
        "prompt": job.prompt,
        "site": job.site,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "result": job.result,
        "error": job.error,
    }


def build_app(out_dir: Path):
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from pydantic import BaseModel, Field

    out_dir.mkdir(parents=True, exist_ok=True)
    queue = JobQueue()
    wakeup = asyncio.Event()
    running_proc: dict[str, asyncio.subprocess.Process] = {}

    class SubmitBody(BaseModel):
        prompt: str = Field(min_length=1)
        site: str = "chatgpt"
        timeout: int = Field(default=DEFAULT_JOB_TIMEOUT_SEC, gt=0, le=1800)
        filename: Optional[str] = None

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(_app):
        task = asyncio.get_running_loop().create_task(worker())
        yield
        task.cancel()

    app = FastAPI(title="omp web-operator image service", lifespan=lifespan)

    async def run_job(job: Job) -> None:
        script = SITES_DIR / job.site / "generate-image.sh"
        job.status = RUNNING
        job.started_at = now_iso()
        proc = await asyncio.create_subprocess_exec(
            "bash",
            str(script),
            job.prompt,
            "--out",
            str(job.out_path),
            "--overwrite",
            "--json",
            "--timeout",
            str(job.timeout_sec),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        running_proc[job.id] = proc
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=job.timeout_sec + 60
            )
        except asyncio.TimeoutError:
            _kill(proc)
            await proc.wait()
            job.status = FAILED
            job.error = "job timed out (process killed)"
            return
        finally:
            running_proc.pop(job.id, None)
            job.finished_at = now_iso()

        if job.status == CANCELED:
            return
        if proc.returncode == 0:
            try:
                job.result = json.loads(stdout.decode("utf-8"))
            except json.JSONDecodeError:
                job.result = {"path": str(job.out_path)}
            job.status = DONE
        else:
            job.status = FAILED
            job.error = (stderr or stdout).decode("utf-8", "replace").strip()[-2000:]

    async def worker() -> None:
        while True:
            job = queue.next_queued()
            if job is None:
                wakeup.clear()
                await wakeup.wait()
                continue
            await run_job(job)

    def _kill(proc: asyncio.subprocess.Process) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

    @app.get("/health")
    async def health():
        cdp_ok = await cdp_health()
        return {"ok": True, "cdp": cdp_ok, "queue_length": queue.queue_length()}

    @app.post("/jobs", status_code=202)
    async def submit(body: SubmitBody):
        script = SITES_DIR / body.site / "generate-image.sh"
        if not script.is_file():
            raise HTTPException(400, f"unsupported site: {body.site}")
        name = body.filename or f"{now_iso().replace(':', '-')}-{uuid.uuid4().hex[:6]}.png"
        job = Job(body.prompt, body.site, body.timeout, out_dir / name)
        queue.submit(job)
        wakeup.set()
        return {
            "job_id": job.id,
            "position": queue.position(job),
            "queue_length": queue.queue_length(),
        }

    @app.get("/jobs")
    async def list_jobs():
        return {"jobs": [job_view(queue, queue.jobs[j]) for j in queue.order]}

    @app.get("/jobs/{job_id}")
    async def get_job(job_id: str):
        job = queue.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "unknown job")
        return job_view(queue, job)

    @app.delete("/jobs/{job_id}")
    async def cancel_job(job_id: str):
        job = queue.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "unknown job")
        if job.status == QUEUED:
            queue.cancel(job)
            return {"ok": True, "status": job.status}
        if job.status == RUNNING:
            job.status = CANCELED
            job.finished_at = now_iso()
            proc = running_proc.get(job_id)
            if proc is not None:
                _kill(proc)
            return {"ok": True, "status": job.status}
        raise HTTPException(409, f"job already {job.status}")

    @app.get("/jobs/{job_id}/image")
    async def get_image(job_id: str):
        job = queue.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "unknown job")
        if job.status != DONE:
            raise HTTPException(409, f"job is {job.status}, not done")
        if not job.out_path.is_file():
            raise HTTPException(410, "image file no longer exists")
        return FileResponse(job.out_path)

    return app


async def cdp_health() -> bool:
    """Chrome CDP reachability: DevToolsActivePort-independent /json/version probe."""
    cdp = SITES_DIR.parent / "cdp.mjs"
    proc = await asyncio.create_subprocess_exec(
        "node",
        str(cdp),
        "list",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        await asyncio.wait_for(proc.wait(), timeout=15)
    except asyncio.TimeoutError:
        proc.kill()
        return False
    return proc.returncode == 0


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="omp web-operator image service")
    parser.add_argument("--port", type=int, default=8320)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    app = build_app(Path(args.out_dir).expanduser())
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
