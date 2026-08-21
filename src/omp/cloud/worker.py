"""In-process development worker with signed tenant-bound jobs and DLQ."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
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


class ReembeddingStore(Protocol):
    def get(self, *, owner_id: str, memory_id: str) -> dict[str, object] | None: ...

    def store_embedding(
        self,
        *,
        owner_id: str,
        memory_id: str,
        source_version: int,
        values: tuple[float, ...],
    ) -> bool: ...


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

    def snapshot(self) -> tuple[dict[str, object], ...]:
        """Return restart-safe job metadata; payloads remain external references."""
        return tuple(
            {
                "job_id": str(job.envelope.job_id),
                "tenant_id": str(job.envelope.tenant_id),
                "principal_id": str(job.envelope.principal_id),
                "expires_at": job.envelope.expires_at.isoformat(),
                "nonce": job.envelope.nonce,
                "signature": job.envelope.signature,
                "dedupe_key": job.dedupe_key,
                "payload_ref": job.payload_ref,
                "state": job.state.value,
                "attempts": job.attempts,
            }
            for job in self._jobs.values()
        )

    def restore(self, snapshot: tuple[dict[str, object], ...]) -> int:
        """Restore only signed, non-terminal jobs after a local worker restart."""
        restored: dict[UUID, LocalJob] = {}
        dedupe: dict[tuple[UUID, str], UUID] = {}
        try:
            for item in snapshot:
                envelope = WorkerEnvelope(
                    job_id=UUID(str(item["job_id"])),
                    tenant_id=UUID(str(item["tenant_id"])),
                    principal_id=UUID(str(item["principal_id"])),
                    expires_at=datetime.fromisoformat(str(item["expires_at"])),
                    nonce=str(item["nonce"]),
                    signature=str(item["signature"]),
                )
                envelope.verify(secret=self._secret)
                state = JobState(str(item["state"]))
                attempts = int(str(item["attempts"]))
                if attempts < 0 or state in {JobState.READY, JobState.STALE, JobState.DEAD_LETTER}:
                    continue
                dedupe_key = str(item["dedupe_key"])
                key = (envelope.tenant_id, dedupe_key)
                if envelope.job_id in restored or key in dedupe:
                    raise ValueError("duplicate worker snapshot entry")
                restored[envelope.job_id] = LocalJob(
                    envelope=envelope,
                    dedupe_key=dedupe_key,
                    payload_ref=str(item["payload_ref"]),
                    state=state,
                    attempts=attempts,
                    error="worker execution failed" if state == JobState.FAILED else None,
                )
                dedupe[key] = envelope.job_id
        except (KeyError, TypeError, ValueError) as exc:
            raise PermissionError("worker snapshot rejected") from exc
        self._jobs, self._dedupe = restored, dedupe
        return len(restored)


async def reembed_memory(
    job: LocalJob,
    *,
    store: ReembeddingStore,
    embed: Callable[[str], Awaitable[tuple[float, ...]]],
) -> JobState:
    """Embed one version-bound reference, treating changed/deleted records as stale.

    ``payload_ref`` is deliberately only ``memory_id:source_version``. The
    tenant and principal come from the signed envelope, and plaintext exists
    only while the supplied embedding function runs.
    """
    try:
        memory_id, raw_version = job.payload_ref.rsplit(":", 1)
        source_version = int(raw_version)
        if not memory_id or source_version < 1:
            raise ValueError
    except ValueError:
        return JobState.STALE
    owner_id = f"cloud:{job.envelope.tenant_id}:{job.envelope.principal_id}"
    record = store.get(owner_id=owner_id, memory_id=memory_id)
    if record is None or record.get("version") != source_version:
        return JobState.STALE
    values = await embed(str(record["content"]))
    return (
        JobState.READY
        if store.store_embedding(
            owner_id=owner_id,
            memory_id=memory_id,
            source_version=source_version,
            values=values,
        )
        else JobState.STALE
    )
