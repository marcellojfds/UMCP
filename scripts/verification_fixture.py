#!/usr/bin/env python3
"""A disposable black-box fixture used to test Verification's own assertions.

This is not a second product implementation and is never used as Core evidence.
It models only the observable contract needed by the conformance harness.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class FixtureError(AssertionError):
    pass


@dataclass
class Connection:
    client: str
    user: str
    tenant: str
    scopes: set[str]
    revoked: bool = False


@dataclass
class Memory:
    memory_id: str
    tenant: str
    user: str
    content: str
    memory_type: str
    space: str
    state: str
    source_client: str
    source_type: str
    source_id: str
    captured_at: str
    concepts: tuple[str, ...]
    reason_retrieved: str = ""


@dataclass
class SyntheticVault:
    connections: dict[str, Connection] = field(default_factory=dict)
    memories: dict[str, Memory] = field(default_factory=dict)
    tombstones: set[str] = field(default_factory=set)
    snapshots: dict[str, Memory] = field(default_factory=dict)
    next_id: int = 1

    def connect(self, client: str, user: str, tenant: str, scopes: set[str] | None = None) -> None:
        self.connections[client] = Connection(
            client, user, tenant, scopes or {"memory:read", "memory:write", "memory:delete"}
        )

    def _connection(self, client: str, scope: str) -> Connection:
        connection = self.connections[client]
        if connection.revoked or scope not in connection.scopes:
            raise PermissionError(f"connection {client} is not authorized for {scope}")
        return connection

    def capture_candidate(
        self, client: str, content: str, *, space: str, concepts: tuple[str, ...]
    ) -> str:
        connection = self._connection(client, "memory:write")
        memory_id = f"synthetic-memory-{self.next_id:03d}"
        self.next_id += 1
        normalized = re.sub(r"\s+", " ", content.strip())
        self.memories[memory_id] = Memory(
            memory_id=memory_id,
            tenant=connection.tenant,
            user=connection.user,
            content=normalized,
            memory_type="lesson",
            space=space,
            state="candidate",
            source_client=client,
            source_type="conversation",
            source_id=f"synthetic-conversation-{memory_id}",
            captured_at=datetime.now(UTC).isoformat(),
            concepts=concepts,
        )
        return memory_id

    def confirm(self, client: str, memory_id: str) -> None:
        connection = self._connection(client, "memory:write")
        memory = self.memories[memory_id]
        if memory.tenant != connection.tenant or memory.user != connection.user:
            raise PermissionError("memory ownership mismatch")
        memory.state = "confirmed"

    def search(
        self, client: str, query: str, *, space: str, related_spaces: tuple[str, ...] = ()
    ) -> list[dict[str, Any]]:
        connection = self._connection(client, "memory:read")
        query_terms = set(re.findall(r"[a-zà-ÿ]+", query.lower()))
        allowed_spaces = {space, *related_spaces}
        results: list[dict[str, Any]] = []
        for memory in self.memories.values():
            if (
                memory.memory_id in self.tombstones
                or memory.tenant != connection.tenant
                or memory.user != connection.user
            ):
                continue
            if memory.state not in {"confirmed", "pinned"} or memory.space not in allowed_spaces:
                continue
            content_terms = set(re.findall(r"[a-zà-ÿ]+", memory.content.lower()))
            concept_terms = set(term.lower() for term in memory.concepts)
            overlap = query_terms & (content_terms | concept_terms)
            if not overlap:
                continue
            memory.reason_retrieved = "concept overlap under explicit cross-space policy"
            results.append(
                {
                    "memory_id": memory.memory_id,
                    "content": memory.content,
                    "space": memory.space,
                    "state": memory.state,
                    "provenance": {
                        "source_client": memory.source_client,
                        "source_type": memory.source_type,
                        "source_id": memory.source_id,
                        "captured_at": memory.captured_at,
                    },
                    "reason_retrieved": memory.reason_retrieved,
                }
            )
        return results

    def revoke(self, client: str) -> None:
        self.connections[client].revoked = True

    def forget(self, client: str, memory_id: str) -> bool:
        connection = self._connection(client, "memory:delete")
        memory = self.memories.get(memory_id)
        if memory is None or memory.tenant != connection.tenant or memory.user != connection.user:
            return False
        self.snapshots[memory_id] = copy.deepcopy(memory)
        self.tombstones.add(memory_id)
        del self.memories[memory_id]
        return True

    def restore(self, memory_id: str) -> str:
        if memory_id in self.tombstones:
            return "skipped-tombstone"
        if memory_id in self.snapshots:
            self.memories[memory_id] = copy.deepcopy(self.snapshots[memory_id])
            return "restored"
        return "not-found"


def make_vault() -> SyntheticVault:
    vault = SyntheticVault()
    vault.connect("chatgpt-sim", "user-a", "tenant-a")
    vault.connect("claude-sim", "user-a", "tenant-a")
    vault.connect("chatgpt-sim-b", "user-b", "tenant-b")
    return vault


def acceptance_cross_client() -> None:
    vault = make_vault()
    memory_id = vault.capture_candidate(
        "chatgpt-sim",
        (
            "No meu projeto do MBA, incentivos mal desenhados fazem equipes "
            "otimizar a métrica, não o resultado."
        ),
        space="MBA",
        concepts=("incentivos", "métricas", "comportamento organizacional"),
    )
    if vault.memories[memory_id].state != "candidate":
        raise FixtureError("capture did not produce candidate")
    vault.confirm("chatgpt-sim", memory_id)
    results = vault.search(
        "claude-sim",
        "Por que a equipe de trabalho aumentou tickets encerrados enquanto a satisfação caiu?",
        space="Work",
        related_spaces=("MBA",),
    )
    if len(results) != 1:
        raise FixtureError("Claude did not recover the confirmed cross-space lesson")
    record = results[0]
    for key in ("provenance", "reason_retrieved", "space"):
        if key not in record:
            raise FixtureError(f"recall record lacks {key}")
    if record["provenance"]["source_client"] != "chatgpt-sim" or record["space"] != "MBA":
        raise FixtureError("recall provenance or source space is wrong")
    if vault.search("chatgpt-sim-b", "incentivos métricas", space="Work", related_spaces=("MBA",)):
        raise FixtureError("tenant B received a result")
    vault.revoke("chatgpt-sim")
    try:
        vault.capture_candidate(
            "chatgpt-sim", "new synthetic lesson", space="MBA", concepts=("new",)
        )
    except PermissionError:
        pass
    else:
        raise FixtureError("revoked ChatGPT connection still wrote")
    if (
        len(
            vault.search("claude-sim", "incentivos métricas", space="Work", related_spaces=("MBA",))
        )
        != 1
    ):
        raise FixtureError("Claude stopped after ChatGPT revocation")
    if not vault.forget("claude-sim", memory_id):
        raise FixtureError("forget did not remove memory")
    if vault.restore(memory_id) != "skipped-tombstone":
        raise FixtureError("restore resurrected forgotten memory")
    if vault.search("claude-sim", "incentivos métricas", space="Work", related_spaces=("MBA",)):
        raise FixtureError("forgotten memory remained searchable")


def scenario(name: str) -> None:
    if name in {"cross-client", "local-integration"}:
        acceptance_cross_client()
        return
    if name == "memory-inbox":
        vault = make_vault()
        memory_id = vault.capture_candidate(
            "chatgpt-sim", "Synthetic inbox candidate", space="MBA", concepts=("inbox",)
        )
        if vault.memories[memory_id].state != "candidate":
            raise FixtureError("candidate was not placed in inbox state")
        vault.confirm("chatgpt-sim", memory_id)
        if vault.memories[memory_id].state != "confirmed":
            raise FixtureError("inbox confirmation did not update state")
        return
    if name == "concepts-and-notes":
        vault = make_vault()
        memory_id = vault.capture_candidate(
            "chatgpt-sim", "Synthetic concept note", space="MBA", concepts=("concept-x",)
        )
        vault.confirm("chatgpt-sim", memory_id)
        if vault.memories[memory_id].concepts != ("concept-x",):
            raise FixtureError("concept provenance was lost")
        return
    if name == "backup-delete-restore":
        vault = make_vault()
        memory_id = vault.capture_candidate(
            "chatgpt-sim", "Synthetic backup record", space="MBA", concepts=("backup",)
        )
        vault.confirm("chatgpt-sim", memory_id)
        vault.forget("chatgpt-sim", memory_id)
        if vault.restore(memory_id) != "skipped-tombstone" or memory_id not in vault.tombstones:
            raise FixtureError("tombstone policy failed")
        return
    raise FixtureError(f"unknown fixture scenario: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        required=True,
        choices=(
            "local-integration",
            "cross-client",
            "memory-inbox",
            "concepts-and-notes",
            "backup-delete-restore",
        ),
    )
    args = parser.parse_args()
    scenario(args.scenario)
    digest = hashlib.sha256(args.scenario.encode()).hexdigest()[:12]
    print(f"fixture scenario passed: {args.scenario} synthetic-run={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
