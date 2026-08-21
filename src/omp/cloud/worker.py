"""In-process development worker with signed tenant-bound jobs and DLQ."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from .security import WorkerEnvelope


class JobState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    STALE = "stale"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass(slots=True)
class LocalJob:
    envelope: WorkerEnvelope
    dedupe_key: str
    payload_ref: str
    state: JobState = JobState.PENDING
    attempts: int = 0
    error: str | None = None


class LocalTenantWorker:
    """Bounded retry worker. Payloads are refs, never content/log data."""

    def __init__(self, *, signing_secret: bytes, max_attempts: int = 3) -> None:
        self._secret = signing_secret
        self._max_attempts = max_attempts
        self._jobs: dict[UUID, LocalJob] = {}
        self._dedupe: dict[tuple[UUID, str], UUID] = {}

    def enqueue(self, envelope: WorkerEnvelope, *, dedupe_key: str, payload_ref: str) -> LocalJob:
        envelope.verify(secret=self._secret)
        key = (envelope.tenant_id, dedupe_key)
        existing = self._dedupe.get(key)
        if existing is not None:
            return self._jobs[existing]
        job = LocalJob(envelope=envelope, dedupe_key=dedupe_key, payload_ref=payload_ref)
        self._jobs[envelope.job_id] = job
        self._dedupe[key] = envelope.job_id
        return job

    async def run_one(
        self, job_id: UUID, handler: Callable[[LocalJob], Awaitable[JobState]]
    ) -> LocalJob:
        job = self._jobs[job_id]
        if job.state in {JobState.READY, JobState.STALE, JobState.DEAD_LETTER}:
            return job
        try:
            job.envelope.verify(secret=self._secret)
            job.attempts += 1
            result = await handler(job)
            if result not in {JobState.READY, JobState.STALE}:
                raise ValueError("worker handler returned invalid terminal state")
            job.state = result
            job.error = None
        except Exception:
            if job.attempts >= self._max_attempts:
                job.state = JobState.DEAD_LETTER
            else:
                job.state = JobState.FAILED
            job.error = "worker execution failed"
        return job

    def retryable(self) -> tuple[LocalJob, ...]:
        return tuple(job for job in self._jobs.values() if job.state == JobState.FAILED)

    def job(self, job_id: UUID) -> LocalJob:
        return self._jobs[job_id]
