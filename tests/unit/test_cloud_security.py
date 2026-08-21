from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omp.cloud import (
    JobState,
    LocalDevelopmentKMS,
    LocalTenantWorker,
    TenantEnvelopeEncryptor,
    WorkerEnvelope,
)
from omp.cloud.encrypted_memory import EncryptedCloudMemoryService
from omp.cloud.tenant import TenantContextError, current_tenant, tenant_scope


def test_tenant_scope_is_request_local_and_fails_closed_when_absent() -> None:
    tenant = uuid4()
    with pytest.raises(TenantContextError):
        current_tenant()
    with tenant_scope(tenant):
        assert current_tenant() == tenant
    with pytest.raises(TenantContextError):
        current_tenant()


def test_envelope_ciphertext_is_tenant_and_record_bound() -> None:
    tenant, other_tenant, record = uuid4(), uuid4(), uuid4()
    encryptor = TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32))
    encrypted = encryptor.encrypt(
        tenant_id=tenant,
        record_id=record,
        field="content",
        plaintext="sensitive memory",
        key_version=1,
    )
    assert "sensitive memory" not in encrypted.encode()
    assert (
        encryptor.decrypt(tenant_id=tenant, record_id=record, field="content", value=encrypted)
        == "sensitive memory"
    )
    with pytest.raises(PermissionError):
        encryptor.decrypt(
            tenant_id=other_tenant, record_id=record, field="content", value=encrypted
        )


def test_envelope_ciphertext_storage_round_trip_rejects_malformed_value() -> None:
    from omp.cloud.security import EnvelopeCiphertext

    value = EnvelopeCiphertext(1, b"wrapped", b"nonce", b"ciphertext")
    assert EnvelopeCiphertext.decode(value.encode()) == value
    with pytest.raises(PermissionError):
        EnvelopeCiphertext.decode('{"v":1}')


def test_worker_envelope_fails_closed_for_tamper_and_expiry() -> None:
    secret = b"s" * 32
    envelope = WorkerEnvelope.sign(
        job_id=uuid4(),
        tenant_id=uuid4(),
        principal_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        nonce="n",
        secret=secret,
    )
    envelope.verify(secret=secret)
    with pytest.raises(PermissionError):
        envelope.verify(secret=b"x" * 32)
    expired = WorkerEnvelope.sign(
        job_id=uuid4(),
        tenant_id=uuid4(),
        principal_id=uuid4(),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        nonce="n",
        secret=secret,
    )
    with pytest.raises(PermissionError):
        expired.verify(secret=secret)


def test_cloud_memory_adapter_persists_ciphertext_and_tenant_binding() -> None:
    tenant, subject = uuid4(), uuid4()
    owner = f"cloud:{tenant}:{subject}"
    service = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    created = service.write(
        {
            "owner_id": owner,
            "content": "CANARY-PLAINTEXT-MEMORY",
            "type": "fact",
            "provenance": {"source_type": "user"},
            "idempotency_key": "write-1",
        }
    )
    assert "CANARY-PLAINTEXT-MEMORY" not in service.raw_dump()
    assert created["memory"]["content"] == "CANARY-PLAINTEXT-MEMORY"
    with pytest.raises(PermissionError):
        service.write(
            {
                "owner_id": "not-a-cloud-owner",
                "content": "x",
                "type": "fact",
                "provenance": {},
                "idempotency_key": "x",
            }
        )


def test_cloud_memory_rewrap_rotates_fields_without_plaintext_persistence() -> None:
    tenant, subject = uuid4(), uuid4()
    service = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    created = service.write(
        {
            "owner_id": f"cloud:{tenant}:{subject}",
            "content": "ROTATION-CANARY",
            "type": "fact",
            "provenance": {"source_type": "user"},
            "idempotency_key": "rotation-1",
        }
    )
    memory_id = created["memory"]["id"]
    assert service._records[memory_id]["content_ciphertext"]["key_version"] == 1
    assert service.rewrap(2) == 2
    assert service._records[memory_id]["content_ciphertext"]["key_version"] == 2
    assert service.search({"owner_id": f"cloud:{tenant}:{subject}", "query": "rotation"})[0][
        "memory"
    ]["content"] == "ROTATION-CANARY"
    assert "ROTATION-CANARY" not in service.raw_dump()


def test_cloud_backup_restore_reapplies_content_free_tombstone() -> None:
    tenant, subject = uuid4(), uuid4()
    owner = f"cloud:{tenant}:{subject}"
    service = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    created = service.write(
        {
            "owner_id": owner,
            "content": "BACKUP-DELETE-CANARY",
            "type": "fact",
            "provenance": {"source_type": "user"},
            "idempotency_key": "backup-1",
        }
    )
    snapshot = service.backup()
    memory_id = created["memory"]["id"]
    assert service.forget({"owner_id": owner, "id": memory_id, "idempotency_key": "forget-1"})[
        "status"
    ] == "forgotten"
    ledger = service.tombstones()
    assert "BACKUP-DELETE-CANARY" not in repr(ledger)

    restored = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    assert restored.restore(snapshot, tombstones=ledger) == 0
    assert restored.search({"owner_id": owner, "query": "backup"}) == []


@pytest.mark.asyncio
async def test_worker_is_tenant_bound_deduplicated_and_retries_to_dlq() -> None:
    secret, tenant, principal = b"s" * 32, uuid4(), uuid4()
    envelope = WorkerEnvelope.sign(
        job_id=uuid4(),
        tenant_id=tenant,
        principal_id=principal,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        nonce="job-1",
        secret=secret,
    )
    worker = LocalTenantWorker(signing_secret=secret, max_attempts=2)
    first = worker.enqueue(envelope, dedupe_key="embed:memory-1", payload_ref="memory-1")
    assert worker.enqueue(envelope, dedupe_key="embed:memory-1", payload_ref="ignored") is first

    async def fails(_: object) -> JobState:
        raise RuntimeError("synthetic")

    assert (await worker.run_one(envelope.job_id, fails)).state == JobState.FAILED
    assert (await worker.run_one(envelope.job_id, fails)).state == JobState.DEAD_LETTER
