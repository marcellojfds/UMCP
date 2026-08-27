from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omp.cloud import (
    GoogleCloudKMS,
    HostedKMSUnavailable,
    JobState,
    KMSUnavailableError,
    LocalDevelopmentKMS,
    LocalRecoveryFixture,
    LocalTenantWorker,
    Principal,
    RecoveryUnavailableError,
    Scope,
    TenantEnvelopeEncryptor,
    WorkerEnvelope,
    reembed_memory,
)
from omp.cloud.encrypted_memory import EncryptedCloudMemoryService
from omp.cloud.tenant import (
    TenantContextError,
    current_tenant,
    tenant_scope,
    verified_principal_scope,
)


def test_tenant_scope_is_request_local_and_fails_closed_when_absent() -> None:
    tenant = uuid4()
    with pytest.raises(TenantContextError):
        current_tenant()
    with tenant_scope(tenant):
        assert current_tenant() == tenant
    with pytest.raises(TenantContextError):
        current_tenant()


def test_tenant_scope_requires_an_immutable_verified_principal_for_hosted_binding() -> None:
    tenant = uuid4()
    principal = Principal(
        subject_id=uuid4(),
        tenant_id=tenant,
        membership_id=uuid4(),
        scopes=frozenset({Scope.MEMORY_READ}),
        credential_id=uuid4(),
        auth_method="local-development",
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    with verified_principal_scope(principal):
        assert current_tenant() == tenant
    with pytest.raises(TenantContextError):
        with verified_principal_scope(object()):
            pass


def test_hosted_kms_seam_fails_closed_without_a_plaintext_fallback() -> None:
    encryptor = TenantEnvelopeEncryptor(HostedKMSUnavailable())
    with pytest.raises(KMSUnavailableError):
        encryptor.encrypt(
            tenant_id=uuid4(),
            record_id=uuid4(),
            field="content",
            plaintext="must never be persisted",
            key_version=1,
        )


def test_google_kms_adapter_binds_wrapped_keys_to_tenant_and_version() -> None:
    class Client:
        def encrypt(self, *, request):
            self.encrypt_request = request
            return type("Result", (), {"ciphertext": b"wrapped"})()

        def decrypt(self, *, request):
            self.decrypt_request = request
            return type("Result", (), {"plaintext": b"k" * 32})()

    client = Client()
    kms = GoogleCloudKMS(
        "projects/test/locations/us-central1/keyRings/umcp/cryptoKeys/envelope", client=client
    )
    tenant = uuid4()
    assert kms.wrap(tenant_id=tenant, key_version=1, dek=b"d" * 32) == b"wrapped"
    assert kms.unwrap(tenant_id=tenant, key_version=1, wrapped_dek=b"wrapped") == b"k" * 32
    assert client.encrypt_request["additional_authenticated_data"] == client.decrypt_request[
        "additional_authenticated_data"
    ]


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

    value = EnvelopeCiphertext(1, b"w" * 28, b"n" * 12, b"c" * 16)
    assert EnvelopeCiphertext.decode(value.encode()) == value
    with pytest.raises(PermissionError):
        EnvelopeCiphertext.decode('{"v":1}')
    with pytest.raises(PermissionError):
        EnvelopeCiphertext.decode('{"c":"YQ==","k":1,"n":"YQ==","v":1,"w":"YQ=="}')


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
    assert (
        service.search({"owner_id": f"cloud:{tenant}:{subject}", "query": "rotation"})[0]["memory"][
            "content"
        ]
        == "ROTATION-CANARY"
    )
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
    assert (
        service.forget({"owner_id": owner, "id": memory_id, "idempotency_key": "forget-1"})[
            "status"
        ]
        == "forgotten"
    )
    ledger = service.tombstones()
    assert "BACKUP-DELETE-CANARY" not in repr(ledger)

    restored = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    assert restored.restore(snapshot, tombstones=ledger) == 0
    assert restored.search({"owner_id": owner, "query": "backup"}) == []


def test_cloud_account_deletion_is_owner_scoped_and_leaves_content_free_tombstones() -> None:
    tenant, other_tenant, subject = uuid4(), uuid4(), uuid4()
    owner, other_owner = f"cloud:{tenant}:{subject}", f"cloud:{other_tenant}:{uuid4()}"
    service = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    records = (
        (owner, "ACCOUNT-DELETE-CANARY", "delete-a"),
        (other_owner, "other tenant", "delete-b"),
    )
    for owner_id, content, key in records:
        service.write(
            {
                "owner_id": owner_id,
                "content": content,
                "type": "fact",
                "provenance": {"source_type": "user"},
                "idempotency_key": key,
            }
        )
    assert service.delete_owner(owner) == 1
    assert service.search({"owner_id": owner, "query": "account"}) == []
    assert len(service.search({"owner_id": other_owner, "query": "other"})) == 1
    assert "ACCOUNT-DELETE-CANARY" not in repr(service.tombstones())


def test_local_recovery_inventory_measures_only_an_isolated_ciphertext_restore() -> None:
    tenant, subject = uuid4(), uuid4()
    owner = f"cloud:{tenant}:{subject}"
    service = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    service.write(
        {
            "owner_id": owner,
            "content": "RECOVERY-CANARY",
            "type": "fact",
            "provenance": {"source_type": "user"},
            "idempotency_key": "recovery-1",
        }
    )
    fixture = LocalRecoveryFixture(migration_head="0009_h06_security_recovery")
    snapshot, inventory = fixture.backup(service)
    assert "RECOVERY-CANARY" not in repr(snapshot)
    restored = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    receipt = fixture.restore_isolated(restored, snapshot, inventory)
    assert receipt.target == "isolated"
    assert receipt.rpo_seconds >= 0
    assert receipt.rto_seconds >= 0

    with pytest.raises(RecoveryUnavailableError):
        from omp.cloud.recovery import HostedRecoveryAdapter

        HostedRecoveryAdapter().inventory()


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


@pytest.mark.asyncio
async def test_worker_restart_restores_signed_retryable_job_without_payload() -> None:
    secret, tenant, principal = b"s" * 32, uuid4(), uuid4()
    envelope = WorkerEnvelope.sign(
        job_id=uuid4(),
        tenant_id=tenant,
        principal_id=principal,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        nonce="restart-job",
        secret=secret,
    )
    worker = LocalTenantWorker(signing_secret=secret, max_attempts=2)
    worker.enqueue(envelope, dedupe_key="embed:restart", payload_ref="memory-ref")

    async def fails(_: object) -> JobState:
        raise RuntimeError("synthetic")

    assert (await worker.run_one(envelope.job_id, fails)).state == JobState.FAILED
    snapshot = worker.snapshot()
    assert "content" not in repr(snapshot)
    restarted = LocalTenantWorker(signing_secret=secret, max_attempts=2)
    assert restarted.restore(snapshot) == 1

    async def ready(_: object) -> JobState:
        return JobState.READY

    assert (await restarted.run_one(envelope.job_id, ready)).state == JobState.READY
    tampered = [dict(snapshot[0], signature="bad")]
    with pytest.raises(PermissionError):
        LocalTenantWorker(signing_secret=secret).restore(tuple(tampered))


@pytest.mark.asyncio
async def test_worker_rejects_nonce_replay_and_snapshot_field_tampering() -> None:
    secret, tenant, principal = b"s" * 32, uuid4(), uuid4()
    envelope = WorkerEnvelope.sign(
        job_id=uuid4(),
        tenant_id=tenant,
        principal_id=principal,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        nonce="one-time-nonce",
        secret=secret,
    )
    worker = LocalTenantWorker(signing_secret=secret)
    worker.enqueue(envelope, dedupe_key="job:one", payload_ref="memory-1:1")
    replay = WorkerEnvelope.sign(
        job_id=uuid4(),
        tenant_id=tenant,
        principal_id=principal,
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        nonce="one-time-nonce",
        secret=secret,
    )
    with pytest.raises(PermissionError):
        worker.enqueue(replay, dedupe_key="job:two", payload_ref="memory-2:1")
    snapshot = list(worker.snapshot())
    snapshot[0]["payload_ref"] = "plaintext-content"
    with pytest.raises(PermissionError):
        LocalTenantWorker(signing_secret=secret).restore(tuple(snapshot))


@pytest.mark.asyncio
async def test_reembedding_is_tenant_bound_resumable_and_never_writes_stale_vectors() -> None:
    secret, tenant, principal = b"s" * 32, uuid4(), uuid4()
    owner = f"cloud:{tenant}:{principal}"
    service = EncryptedCloudMemoryService(TenantEnvelopeEncryptor(LocalDevelopmentKMS(b"k" * 32)))
    created = service.write(
        {
            "owner_id": owner,
            "content": "reembedding canary",
            "type": "fact",
            "provenance": {"source_type": "user"},
            "idempotency_key": "reembed-write",
        }
    )["memory"]

    def job() -> WorkerEnvelope:
        return WorkerEnvelope.sign(
            job_id=uuid4(),
            tenant_id=tenant,
            principal_id=principal,
            expires_at=datetime.now(UTC) + timedelta(minutes=1),
            nonce=str(uuid4()),
            secret=secret,
        )

    async def embed(content: str) -> tuple[float, ...]:
        assert content == "reembedding canary"
        return (0.25, 0.75)

    async def run_reembedding(work: object) -> JobState:
        assert hasattr(work, "payload_ref")
        return await reembed_memory(work, store=service, embed=embed)  # type: ignore[arg-type]

    ready = LocalTenantWorker(signing_secret=secret)
    ready_envelope = job()
    ready.enqueue(ready_envelope, dedupe_key="reembed:ready", payload_ref=f"{created['id']}:1")
    assert (await ready.run_one(ready_envelope.job_id, run_reembedding)).state == JobState.READY
    assert service.embedding(owner_id=owner, memory_id=created["id"]) == {
        "owner_id": owner,
        "source_version": 1,
        "values": (0.25, 0.75),
    }

    stale = LocalTenantWorker(signing_secret=secret)
    stale_envelope = job()
    stale.enqueue(stale_envelope, dedupe_key="reembed:stale", payload_ref=f"{created['id']}:1")
    service.update(
        {
            "owner_id": owner,
            "id": created["id"],
            "expected_version": 1,
            "patch": {"content": "changed"},
        }
    )
    assert (await stale.run_one(stale_envelope.job_id, run_reembedding)).state == JobState.STALE
    assert service.embedding(owner_id=owner, memory_id=created["id"]) is None

    deleted = LocalTenantWorker(signing_secret=secret)
    deleted_envelope = job()
    deleted.enqueue(
        deleted_envelope,
        dedupe_key="reembed:deleted",
        payload_ref=f"{created['id']}:2",
    )
    service.forget({"owner_id": owner, "id": created["id"], "idempotency_key": "reembed-forget"})
    assert (await deleted.run_one(deleted_envelope.job_id, run_reembedding)).state == JobState.STALE
