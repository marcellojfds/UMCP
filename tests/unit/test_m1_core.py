from dataclasses import replace
from datetime import UTC, datetime

import pytest

from omp.adapters.embeddings import HashEmbeddingProvider
from omp.application.fakes import InMemoryUnitOfWorkFactory
from omp.application.models import (
    CaptureMemoryCommand,
    ConfirmCandidateCommand,
    ForgetMemoryCommand,
    ListInboxCommand,
    RecallMemoryCommand,
    SpacePolicy,
)
from omp.application.services import MemoryApplicationService
from omp.domain import (
    CaptureConsent,
    ConnectionRevokedError,
    ConsentMode,
    ConsentReason,
    MemoryState,
    MemoryType,
    Provenance,
    RestoreBlockedByTombstoneError,
    SourceType,
)


def m1_provenance() -> Provenance:
    return Provenance(
        source_type=SourceType.CONVERSATION,
        source_client="chatgpt-sim",
        source_connection_id="conn-chatgpt-sim",
        conversation_id="conv-opaque-001",
        message_id="msg-opaque-007",
        source_model="model-opaque",
        captured_at=datetime(2026, 8, 22, 12, tzinfo=UTC),
        evidence=("user-selected-excerpt-1",),
    )


def consent() -> CaptureConsent:
    return CaptureConsent(
        mode=ConsentMode.ASSISTED,
        consent_id="consent-opaque-001",
        reason_code=ConsentReason.USER_REQUESTED_MEMORY,
        policy_version="m1-local-1",
        granted_at=datetime(2026, 8, 22, 12, tzinfo=UTC),
    )


def make_service() -> tuple[MemoryApplicationService, InMemoryUnitOfWorkFactory]:
    factory = InMemoryUnitOfWorkFactory()
    return (
        MemoryApplicationService(
            uow_factory=factory,
            embedding_provider=HashEmbeddingProvider(),
        ),
        factory,
    )


def capture(key: str = "capture-1") -> CaptureMemoryCommand:
    return CaptureMemoryCommand(
        tenant_id="tenant-a",
        owner_id="owner-a",
        connection_id="conn-chatgpt-sim",
        content="incentives mal designed make teams optimize the metric, not the outcome",
        memory_type=MemoryType.LESSON,
        space="MBA",
        provenance=m1_provenance(),
        consent=consent(),
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_m1_capture_inbox_confirm_cross_space_recall_and_tenant_isolation() -> None:
    app, _ = make_service()
    captured = await app.capture(capture())
    assert captured.created is True
    assert captured.memory.state == MemoryState.CANDIDATE
    assert captured.memory.capture_consent == consent()
    assert captured.memory.provenance.source_client == "chatgpt-sim"

    inbox = await app.list_inbox(ListInboxCommand("tenant-a", "owner-a", "conn-chatgpt-sim"))
    assert tuple(item.id for item in inbox.candidates) == (captured.memory.id,)
    assert (
        await app.list_inbox(ListInboxCommand("tenant-b", "owner-b", "conn-chatgpt-sim-b"))
    ).candidates == ()
    assert (
        await app.recall(
            RecallMemoryCommand(
                "tenant-a", "owner-a", "conn-chatgpt-sim", "optimize outcome", "Work"
            )
        )
    ).count == 0

    confirmed = await app.confirm_candidate(
        ConfirmCandidateCommand(
            "tenant-a",
            "owner-a",
            "conn-chatgpt-sim",
            captured.memory.id,
            expected_version=1,
            idempotency_key="confirm-1",
        )
    )
    assert confirmed.state == MemoryState.CONFIRMED
    assert confirmed.version == 2
    result = await app.recall(
        RecallMemoryCommand(
            "tenant-a",
            "owner-a",
            "conn-claude-sim",
            "incentives mal designed make teams optimize the metric, not the outcome",
            "Work",
            include_spaces=("MBA",),
            space_policy=SpacePolicy(
                default_recall="explicit_allowlist", allowed_spaces=frozenset({"MBA"})
            ),
        )
    )
    assert result.count == 1
    assert result.items[0].reason_retrieved == "explicit_cross_space_semantic_match"
    assert result.items[0].memory.provenance.source_client == "chatgpt-sim"

    tenant_b = await app.recall(
        RecallMemoryCommand(
            "tenant-b",
            "owner-b",
            "conn-chatgpt-sim-b",
            "incentives mal designed make teams optimize the metric, not the outcome",
            "Work",
            include_spaces=("MBA",),
            space_policy=SpacePolicy(
                default_recall="explicit_allowlist", allowed_spaces=frozenset({"MBA"})
            ),
        )
    )
    assert tenant_b.count == 0

    with pytest.raises(ConnectionRevokedError):
        await app.capture(replace(capture("revoked"), connection_revoked=True))


@pytest.mark.asyncio
async def test_m1_forget_tombstone_blocks_restore_and_replays_are_stable() -> None:
    app, _ = make_service()
    captured = await app.capture(capture())
    package = await app.export_memories(owner_id="owner-a")
    forgotten = await app.forget(
        ForgetMemoryCommand("owner-a", captured.memory.id, tenant_id="tenant-a")
    )
    repeated = await app.forget(
        ForgetMemoryCommand("owner-a", captured.memory.id, tenant_id="tenant-a")
    )
    assert forgotten.forgotten is True
    assert repeated.forgotten is False
    with pytest.raises(RestoreBlockedByTombstoneError):
        await app.import_memories(owner_id="owner-a", records=package)
