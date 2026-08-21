from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omp.cloud import LocalDevelopmentKMS, TenantEnvelopeEncryptor, WorkerEnvelope
from omp.cloud.encrypted_memory import EncryptedCloudMemoryService


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
