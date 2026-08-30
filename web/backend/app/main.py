from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .jobs import Job, manager
from .results import build_results
from .vectors import VECTORS

app = FastAPI(title="AI Defense Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "vector": job.vector,
        "command": " ".join(job.command),
        "status": job.status,
        "log": "\n".join(job.log),
        "returncode": job.returncode,
        "startedAt": job.started_at,
        "finishedAt": job.finished_at,
    }


@app.get("/api/results")
def get_results():
    return build_results()


class RunRequest(BaseModel):
    params: dict = {}


@app.post("/api/run/{vector}")
def start_run(vector: str, req: RunRequest):
    if vector not in VECTORS:
        raise HTTPException(404, f"unknown vector: {vector}")
    try:
        job = manager.start(vector, req.params)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    return job_to_dict(job)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    return job_to_dict(job)


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str):
    try:
        job = manager.stop(job_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    return job_to_dict(job)


@app.get("/api/vectors/{vector}/current-job")
def current_job(vector: str):
    job = manager.current_for(vector)
    return job_to_dict(job) if job else None


@app.get("/api/health")
def health():
    return {"ok": True}
