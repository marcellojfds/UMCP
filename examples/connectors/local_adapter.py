"""A deterministic local adapter; it intentionally does not call product code."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from .fixtures import ConnectorFixture, ConsentFixture, ProvenanceFixture, Scope

RECALL_REASON: Final = "explicit_connector_semantic_match"
REVOKED_AT: Final = "2026-08-24T12:01:00Z"


class ConnectorContractError(RuntimeError):
    """Fail-closed error with a stable contract code and no sensitive detail."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class Memory:
    memory_id: str
    tenant_id: str
    owner_id: str
    content: str
    provenance: ProvenanceFixture
    version: int


class SyntheticLocalAdapter:
    """In-memory connector boundary for typed M03 preflight fixtures."""

    def __init__(self, fixtures: tuple[ConnectorFixture, ...]) -> None:
        self._fixtures = {fixture.client_id: fixture for fixture in fixtures}
        self._revoked: set[str] = set()
        self._consents: dict[tuple[str, str], ConsentFixture] = {}
        self._memories: dict[str, Memory] = {}
        self._operation_results: dict[tuple[str, str], object] = {}
        self._events: list[dict[str, str]] = []

    def _fixture(self, client_id: str) -> ConnectorFixture:
        try:
            return self._fixtures[client_id]
        except KeyError:
            raise ConnectorContractError("unknown_connection") from None

    def _authorized(self, client_id: str, scope: Scope) -> ConnectorFixture:
        fixture = self._fixture(client_id)
        if fixture.connection_id in self._revoked:
            raise ConnectorContractError("connection_revoked")
        if scope not in fixture.scopes:
            raise ConnectorContractError("scope_denied")
        return fixture

    def grant_consent(self, client_id: str, consent: ConsentFixture) -> ConsentFixture:
        fixture = self._authorized(client_id, "consent:grant")
        self._consents[(fixture.connection_id, consent.consent_id)] = consent
        return consent

    def capture(
        self,
        client_id: str,
        *,
        content: str,
        consent_id: str,
        provenance: ProvenanceFixture,
        idempotency_key: str,
    ) -> Memory:
        fixture = self._authorized(client_id, "memory:write")
        consent = self._consents.get((fixture.connection_id, consent_id))
        if consent is None:
            raise ConnectorContractError("consent_required")
        if provenance.source_connection_id != fixture.connection_id:
            raise ConnectorContractError("provenance_connection_mismatch")
        operation_key = (fixture.connection_id, idempotency_key)
        existing = self._operation_results.get(operation_key)
        if existing is not None:
            if not isinstance(existing, Memory) or existing.content != content:
                raise ConnectorContractError("idempotency_conflict")
            return existing
        memory = Memory(
            memory_id="memory-connector-001",
            tenant_id=fixture.tenant_id,
            owner_id=fixture.owner_id,
            content=content,
            provenance=provenance,
            version=1,
        )
        self._memories[memory.memory_id] = memory
        self._operation_results[operation_key] = memory
        return memory

    def recall(self, client_id: str, *, query: str) -> tuple[dict[str, object], ...]:
        fixture = self._authorized(client_id, "memory:read")
        return tuple(
            {
                "memory_id": memory.memory_id,
                "content": memory.content,
                "provenance": memory.provenance,
                "reason_retrieved": RECALL_REASON,
            }
            for memory in self._memories.values()
            if memory.tenant_id == fixture.tenant_id
            and memory.owner_id == fixture.owner_id
            and query.lower() in memory.content.lower()
        )

    def update(
        self,
        client_id: str,
        *,
        memory_id: str,
        content: str,
        idempotency_key: str,
    ) -> Memory:
        fixture = self._authorized(client_id, "memory:write")
        operation_key = (fixture.connection_id, idempotency_key)
        existing = self._operation_results.get(operation_key)
        if existing is not None:
            if not isinstance(existing, Memory) or existing.content != content:
                raise ConnectorContractError("idempotency_conflict")
            return existing
        memory = self._memories.get(memory_id)
        if memory is None:
            raise ConnectorContractError("memory_not_found")
        if (memory.tenant_id, memory.owner_id) != (fixture.tenant_id, fixture.owner_id):
            raise ConnectorContractError("isolation_denied")
        updated = replace(memory, content=content, version=memory.version + 1)
        self._memories[memory_id] = updated
        self._operation_results[operation_key] = updated
        return updated

    def forget(self, client_id: str, *, memory_id: str, idempotency_key: str) -> dict[str, str]:
        fixture = self._authorized(client_id, "memory:delete")
        operation_key = (fixture.connection_id, idempotency_key)
        existing = self._operation_results.get(operation_key)
        if existing is not None:
            if not isinstance(existing, dict):
                raise ConnectorContractError("idempotency_conflict")
            return existing
        memory = self._memories.get(memory_id)
        if memory is not None and (memory.tenant_id, memory.owner_id) != (
            fixture.tenant_id,
            fixture.owner_id,
        ):
            raise ConnectorContractError("isolation_denied")
        status = (
            "forgotten" if self._memories.pop(memory_id, None) is not None else "already_absent"
        )
        result = {"memory_id": memory_id, "status": status}
        self._operation_results[operation_key] = result
        return result

    def revoke(self, actor_client_id: str, *, target_connection_id: str) -> dict[str, str]:
        actor = self._authorized(actor_client_id, "connection:revoke")
        target = next(
            (
                fixture
                for fixture in self._fixtures.values()
                if fixture.connection_id == target_connection_id
            ),
            None,
        )
        if target is None:
            raise ConnectorContractError("unknown_connection")
        if actor.tenant_id != target.tenant_id:
            raise ConnectorContractError("isolation_denied")
        self._revoked.add(target.connection_id)
        event = {
            "event_id": "event-connection-revoked-001",
            "event_type": "connection.revoked",
            "connection_id": target.connection_id,
            "revoked_at": REVOKED_AT,
            "reason": "user_requested_revocation",
        }
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple[dict[str, str], ...]:
        return tuple(self._events)
