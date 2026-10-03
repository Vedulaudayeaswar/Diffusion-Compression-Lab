from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobManager:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="compression-job")

    def create(self, payload: dict[str, Any]) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": "queued",
                "progress": 0,
                "stage": "queued",
                "created_at": utc_now(),
                "started_at": None,
                "completed_at": None,
                "metrics": None,
                "output": None,
                "error": None,
                "payload": payload,
            }
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return json.loads(json.dumps(job, default=str)) if job else None

    def update(self, job_id: str, **values: Any) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(values)

    def submit(self, job_id: str, fn: Callable[[str, Callable[..., None]], None]) -> None:
        self._executor.submit(self._run, job_id, fn)

    def _run(self, job_id: str, fn: Callable[[str, Callable[..., None]], None]) -> None:
        self.update(job_id, status="running", started_at=utc_now(), stage="preprocessing")

        def progress(**values: Any) -> None:
            self.update(job_id, **values)

        try:
            fn(job_id, progress)
            self.update(job_id, status="completed", progress=100, stage="completed", completed_at=utc_now())
        except Exception as exc:
            self.update(
                job_id,
                status="error",
                stage="error",
                completed_at=utc_now(),
                error=str(exc),
            )

