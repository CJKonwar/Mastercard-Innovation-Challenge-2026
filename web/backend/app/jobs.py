"""Runs a vector's CLI as a real subprocess in a background thread and keeps its
output/status in memory - good enough for a single-demo-instance backend, not
meant to survive a restart or serve multiple concurrent operators."""
from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field

from .vectors import REPO_ROOT, VECTORS


@dataclass
class Job:
    id: str
    vector: str
    command: list[str]
    status: str = "running"  # running | done | failed | stopped
    log: list[str] = field(default_factory=list)
    returncode: int | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    process: subprocess.Popen | None = field(default=None, repr=False)
    stop_requested: bool = False


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._running_by_vector: dict[str, str] = {}
        self._lock = threading.Lock()

    def start(self, vector: str, params: dict) -> Job:
        if vector not in VECTORS:
            raise ValueError(f"unknown vector: {vector}")
        with self._lock:
            existing = self._running_by_vector.get(vector)
            if existing and self._jobs[existing].status == "running":
                raise RuntimeError(f"{vector} already has a run in progress (job {existing})")
            command = VECTORS[vector](params)
            job = Job(id=uuid.uuid4().hex[:12], vector=vector, command=command)
            self._jobs[job.id] = job
            self._running_by_vector[vector] = job.id
        thread = threading.Thread(target=self._run, args=(job,), daemon=True)
        thread.start()
        return job

    def _run(self, job: Job) -> None:
        try:
            # New session -> its own process group, so a stop() can kill the
            # whole tree (the dispatcher itself spawns a nested subprocess for
            # the vector's own main.py; killing just this top PID would orphan
            # that child and leave it running).
            proc = subprocess.Popen(
                job.command, cwd=REPO_ROOT, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
                start_new_session=True,
            )
            with self._lock:
                job.process = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                with self._lock:
                    job.log.append(line.rstrip("\n"))
            proc.wait()
            with self._lock:
                if job.stop_requested:
                    job.status = "stopped"
                else:
                    job.status = "done" if proc.returncode == 0 else "failed"
                job.returncode = proc.returncode
                job.finished_at = time.time()
        except Exception as e:
            with self._lock:
                job.log.append(f"[backend] failed to launch: {type(e).__name__}: {e}")
                job.status = "failed"
                job.finished_at = time.time()

    def stop(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ValueError("no such job")
            if job.status != "running":
                raise RuntimeError(f"job is not running (status: {job.status})")
            job.stop_requested = True
            proc = job.process
            job.log.append("[backend] stop requested by user")
        if proc is not None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def current_for(self, vector: str) -> Job | None:
        with self._lock:
            job_id = self._running_by_vector.get(vector)
            return self._jobs.get(job_id) if job_id else None

    def list_recent(self, limit: int = 20) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: -j.started_at)[:limit]


manager = JobManager()
