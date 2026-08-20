from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

from omp.sdk.client import MemoryClient, OfficialStdioTransport, ProtocolError

EXIT_CODES = {
    "ok": 0,
    "validation_error": 2,
    "not_found": 3,
    "version_conflict": 4,
    "forbidden": 5,
    "rate_limited": 6,
    "dependency_unavailable": 7,
    "internal_error": 1,
}


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omp", description="Open Memory Protocol local CLI")
    parser.add_argument(
        "--demo-backend", action="store_true", help="explicitly use the local file demo backend"
    )
    parser.add_argument("--data-file", help="demo backend persistence file")
    parser.add_argument("--json", action="store_true", help="emit stable JSON output")
    commands = parser.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status")
    _output_flags(status)

    memory = commands.add_parser("memory")
    memory_commands = memory.add_subparsers(dest="memory_command", required=True)
    write = memory_commands.add_parser("write")
    write.add_argument("--owner-id", required=True)
    write.add_argument("--content", required=True)
    write.add_argument("--type", required=True)
    write.add_argument("--space")
    write.add_argument("--importance", type=float, default=0.5)
    write.add_argument("--confidence", type=float, default=0.5)
    write.add_argument("--idempotency-key", required=True)
    _output_flags(write)

    search = memory_commands.add_parser("search")
    search.add_argument("--owner-id", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--space")
    search.add_argument("--type")
    search.add_argument("--state")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--min-relevance", type=float, default=0.78)
    _output_flags(search)

    update = memory_commands.add_parser("update")
    update.add_argument("--owner-id", required=True)
    update.add_argument("--id", required=True)
    update.add_argument("--expected-version", required=True, type=int)
    update.add_argument("--content")
    update.add_argument("--type")
    update.add_argument("--space")
    update.add_argument("--state")
    update.add_argument("--importance", type=float)
    update.add_argument("--confidence", type=float)
    update.add_argument("--idempotency-key", required=True)
    _output_flags(update)

    forget = memory_commands.add_parser("forget")
    forget.add_argument("--owner-id", required=True)
    forget.add_argument("--id", required=True)
    forget.add_argument("--idempotency-key", required=True)
    forget.add_argument("--reason")
    _output_flags(forget)

    export = commands.add_parser("export")
    export.add_argument("path", nargs="?", default="omp-export.json")
    export.add_argument("--owner-id")
    _output_flags(export)

    importing = commands.add_parser("import")
    importing.add_argument("path")
    importing.add_argument("--dry-run", action="store_true")
    _output_flags(importing)

    eval_command = commands.add_parser("eval")
    eval_subcommands = eval_command.add_subparsers(dest="eval_command", required=True)
    smoke = eval_subcommands.add_parser("smoke")
    _output_flags(smoke)
    return parser


def _output_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", dest="json_local")
    parser.add_argument("--data-file", dest="data_file_local")


def _client(args: argparse.Namespace) -> MemoryClient:
    data_file = getattr(args, "data_file_local", None) or args.data_file
    backend = os.environ.get("OMP_BACKEND", "postgres")
    demo = bool(args.demo_backend or backend == "demo")
    if data_file and not demo:
        raise ProtocolError("validation_error", "--data-file requires explicit --demo-backend")
    if demo:
        data_file = data_file or ".omp/memory.json"
    environment = dict(os.environ)
    environment["OMP_BACKEND"] = "demo" if demo else "postgres"
    return MemoryClient(
        OfficialStdioTransport(
            data_file=data_file,
            demo_backend=demo,
            env=environment,
        )
    )


def _json_mode(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False) or getattr(args, "json_local", False))


def _provenance() -> dict[str, Any]:
    return {"source_type": "agent", "captured_at": _timestamp(), "source_model": "omp-cli"}


def execute(args: argparse.Namespace) -> tuple[int, Any]:
    client = _client(args)
    if args.command == "status":
        return 0, {
            "status": "ready",
            "protocol": "omp.mcp.v0",
            "transport": "stdio",
            "capabilities": client.capabilities(),
        }
    if args.command == "memory":
        if args.memory_command == "write":
            return 0, client.write(
                content=args.content,
                type=args.type,
                owner_id=args.owner_id,
                space=args.space,
                importance=args.importance,
                confidence=args.confidence,
                provenance=_provenance(),
                idempotency_key=args.idempotency_key,
            )
        if args.memory_command == "search":
            return 0, client.search(
                query=args.query,
                owner_id=args.owner_id,
                space=args.space,
                type=args.type,
                state=args.state,
                limit=args.limit,
                min_relevance=args.min_relevance,
            )
        if args.memory_command == "update":
            patch = {
                key: getattr(args, key)
                for key in ("content", "type", "space", "state", "importance", "confidence")
                if getattr(args, key) is not None
            }
            return 0, client.update(
                id=args.id,
                owner_id=args.owner_id,
                expected_version=args.expected_version,
                patch=patch,
                provenance=_provenance(),
                idempotency_key=args.idempotency_key,
            )
        return 0, client.forget(
            id=args.id,
            owner_id=args.owner_id,
            idempotency_key=args.idempotency_key,
            reason=args.reason,
        )
    if args.command == "export":
        document = client.export(args.path, owner_id=args.owner_id)
        return 0, {
            "status": "exported",
            "path": str(args.path),
            "count": len(document.memories),
            "format": document.format,
        }
    if args.command == "import":
        return 0, client.import_file(args.path, dry_run=args.dry_run)
    if args.command == "eval" and args.eval_command == "smoke":
        return _smoke(client)
    return 1, {"code": "internal_error", "message": "unsupported command"}


def _smoke(client: MemoryClient) -> tuple[int, dict[str, Any]]:
    owner = "smoke-owner"
    written = client.write(
        content=(
            "Geographic density can matter before geographic expansion in "
            "local-network marketplaces."
        ),
        type="insight",
        owner_id=owner,
        provenance=_provenance(),
        idempotency_key="smoke-write",
    )
    memory_id = written["memory"]["id"]
    found = client.search(query="GTM strategy for regional expansion", owner_id=owner, limit=5)
    empty = client.search(query="unrelated cooking recipe", owner_id=owner, limit=5)
    try:
        client.update(
            id=memory_id,
            owner_id=owner,
            expected_version=99,
            patch={"content": "x"},
            provenance=_provenance(),
            idempotency_key="smoke-conflict",
        )
    except ProtocolError as error:
        conflict = error.code
    else:
        conflict = "missing"
    updated = client.update(
        id=memory_id,
        owner_id=owner,
        expected_version=1,
        patch={"importance": 0.9},
        provenance=_provenance(),
        idempotency_key="smoke-update",
    )
    forgotten = client.forget(id=memory_id, owner_id=owner, idempotency_key="smoke-forget")
    after = client.search(query="GTM strategy for regional expansion", owner_id=owner, limit=5)
    return 0, {
        "positive_count": found["count"],
        "negative_count": empty["count"],
        "conflict": conflict,
        "updated_version": updated["memory"]["version"],
        "forget": forgotten["status"],
        "after_forget_count": after["count"],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        code, result = execute(args)
    except ProtocolError as error:
        code = EXIT_CODES.get(error.code, 1)
        result = {
            "error": {"code": error.code, "message": error.message, "retryable": error.retryable}
        }
    except (ValueError, OSError) as error:
        code = EXIT_CODES["validation_error"]
        result = {"error": {"code": "validation_error", "message": str(error)}}
    if _json_mode(args):
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    elif isinstance(result, dict):
        if "error" in result:
            print(
                f"error: {result['error']['code']}: {result['error']['message']}", file=sys.stderr
            )
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
