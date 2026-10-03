from __future__ import annotations

import asyncio
import json
import platform
import time
from pathlib import Path
from typing import Annotated

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .config import settings
from .model_manager import model_manager
from .services.compression_service import compress_bytes, decompress_bytes
from .services.job_manager import JobManager


app = FastAPI(title="Diffusion Compression Lab", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
jobs = JobManager(settings.output_dir)
experiments_path = settings.output_dir / "experiments.json"


def _read_experiments() -> list[dict]:
    if not experiments_path.exists():
        return []
    try:
        return json.loads(experiments_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _write_experiment(job_id: str, result: dict) -> None:
    rows = _read_experiments()
    row = {
        "id": job_id,
        "experiment_id": job_id,
        "created_at": time.time(),
        "image_name": result["metadata"].get("source_filename"),
        "lambda": result["metadata"].get("lambda_value"),
        **result["metrics"],
        "metadata": result["metadata"],
    }
    rows = [existing for existing in rows if existing.get("id") != job_id]
    rows.insert(0, row)
    experiments_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


@app.get("/api/model/status")
def model_status():
    return model_manager.status()


@app.get("/api/system/status")
def system_status():
    gpu = None
    if torch.cuda.is_available():
        gpu = {
            "name": torch.cuda.get_device_name(0),
            "memory_allocated": torch.cuda.memory_allocated(0),
            "memory_reserved": torch.cuda.memory_reserved(0),
        }
    return {"status": "online", "device": settings.resolved_device, "gpu": gpu, "python": platform.python_version()}


@app.post("/api/compress", status_code=202)
async def start_compression(
    image: Annotated[UploadFile, File(...)],
    mode: Annotated[str, Form()] = "research",
    bitrate: Annotated[float | None, Form()] = None,
    lambda_value: Annotated[float, Form()] = 5.0,
    steps: Annotated[int, Form()] = 1,
    resolution: Annotated[int, Form()] = 256,
    reconstruction_mode: Annotated[str, Form()] = "one_step",
    refinement_alpha: Annotated[float, Form()] = 0.0,
):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(400, "Image upload is empty")
    if resolution not in {128, 256, 512}:
        raise HTTPException(400, "Resolution must be 128, 256, or 512")
    payload = {
        "image_bytes": image_bytes,
        "filename": image.filename or "upload",
        "mode": mode,
        "bitrate": bitrate,
        "lambda_value": lambda_value,
        "steps": steps,
        "resolution": resolution,
        "reconstruction_mode": reconstruction_mode,
        "refinement_alpha": refinement_alpha,
    }
    job_id = jobs.create({"filename": image.filename or "upload"})

    def run(current_job_id: str, progress):
        result = compress_bytes(job_id=current_job_id, callback=progress, **payload)
        jobs.update(
            current_job_id,
            progress=100,
            stage="completed",
            metrics=result["metrics"],
            output={
                "dfc2_url": f"/api/jobs/{current_job_id}/download/dfc2",
                "reconstruction_url": f"/api/jobs/{current_job_id}/download/reconstruction",
                "metadata": result["metadata"],
            },
        )
        _write_experiment(current_job_id, result)

    jobs.submit(job_id, run)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    job.pop("payload", None)
    return job


@app.get("/api/jobs/{job_id}/download/dfc2")
def download_dfc2(job_id: str):
    path = settings.output_dir / f"{job_id}.dfc2"
    if not path.exists():
        raise HTTPException(404, "DFC2 file is not ready")
    return FileResponse(path, media_type="application/octet-stream", filename=f"{job_id}.dfc2")


@app.get("/api/jobs/{job_id}/download/reconstruction")
def download_reconstruction(job_id: str):
    path = settings.output_dir / f"{job_id}_reconstruction.png"
    if not path.exists():
        raise HTTPException(404, "Reconstruction is not ready")
    return FileResponse(path, media_type="image/png", filename=f"{job_id}_reconstruction.png")


@app.websocket("/ws/pipeline/{job_id}")
async def pipeline_socket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    last = None
    try:
        while True:
            job = jobs.get(job_id)
            if not job:
                await websocket.send_json({"type": "error", "error": "Job not found"})
                return
            snapshot = {key: job.get(key) for key in ("status", "progress", "stage", "metrics", "output", "error")}
            if snapshot != last:
                await websocket.send_json({"type": "progress", **snapshot})
                last = snapshot
            if job["status"] in {"completed", "error"}:
                return
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        return


@app.post("/api/decompress/inspect")
async def inspect_dfc2(file: Annotated[UploadFile, File(...)]):
    from .diffusion_codec.dfc2 import parse_packet

    try:
        packet = parse_packet(await file.read())
        return packet.metadata
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/decompress")
async def decompress(file: Annotated[UploadFile, File(...)]):
    try:
        image_bytes, metadata = decompress_bytes(await file.read())
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return StreamingResponse(
        iter([image_bytes]),
        media_type="image/png",
        headers={"X-DFC2-Metadata": json.dumps(metadata, separators=(",", ":"))},
    )


@app.get("/api/experiments")
def experiments():
    return _read_experiments()


@app.get("/api/metrics/{experiment_id}")
def metrics(experiment_id: str):
    for row in _read_experiments():
        if row.get("id") == experiment_id:
            return row
    job = jobs.get(experiment_id)
    if job and job.get("metrics"):
        return job["metrics"]
    raise HTTPException(404, "Experiment not found")


@app.get("/health")
def health():
    return {"status": "ok"}
