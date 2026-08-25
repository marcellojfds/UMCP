"""Deterministic, typed, non-sensitive connector fixtures for M03-W0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

Scope = Literal[
    "consent:grant",
    "memory:read",
    "memory:write",
    "memory:delete",
    "connection:revoke",
]


@dataclass(frozen=True, slots=True)
class ConnectorFixture:
    client_id: str
    tenant_id: str
    owner_id: str
    connection_id: str
    scopes: frozenset[Scope]


@dataclass(frozen=True, slots=True)
class ConsentFixture:
    consent_id: str
    mode: Literal["explicit"]
    reason_code: Literal["user_requested_memory"]
    granted_at: str


@dataclass(frozen=True, slots=True)
class ProvenanceFixture:
    source_client: str
    source_type: Literal["conversation", "user"]
    source_connection_id: str
    captured_at: str
    evidence_ref: str


CHATGPT_SIM: Final = ConnectorFixture(
    client_id="chatgpt-sim",
    tenant_id="tenant-a",
    owner_id="owner-a",
    connection_id="conn-chatgpt-sim",
    scopes=frozenset(
        {"consent:grant", "memory:read", "memory:write", "memory:delete", "connection:revoke"}
    ),
)
CLAUDE_SIM: Final = ConnectorFixture(
    client_id="claude-sim",
    tenant_id="tenant-a",
    owner_id="owner-a",
    connection_id="conn-claude-sim",
    scopes=frozenset({"consent:grant", "memory:read", "memory:write", "memory:delete"}),
)
READER_SIM: Final = ConnectorFixture(
    client_id="reader-sim",
    tenant_id="tenant-a",
    owner_id="owner-a",
    connection_id="conn-reader-sim",
    scopes=frozenset({"memory:read"}),
)
TENANT_B_SIM: Final = ConnectorFixture(
    client_id="tenant-b-sim",
    tenant_id="tenant-b",
    owner_id="owner-b",
    connection_id="conn-tenant-b-sim",
    scopes=frozenset({"consent:grant", "memory:read", "memory:write", "memory:delete"}),
)

CONSENT: Final = ConsentFixture(
    consent_id="consent-user-requested-001",
    mode="explicit",
    reason_code="user_requested_memory",
    granted_at="2026-08-24T12:00:00Z",
)
PROVENANCE: Final = ProvenanceFixture(
    source_client="chatgpt-sim",
    source_type="conversation",
    source_connection_id="conn-chatgpt-sim",
    captured_at="2026-08-24T12:00:01Z",
    evidence_ref="evidence-selected-excerpt-001",
)
