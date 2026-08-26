from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import anyio

from omp.config import OMPSettings
from omp.domain import (
    EmbeddingProfileMismatchError,
    ImportConflictError,
    NotFoundError,
    OMPError,
    ValidationError,
)
from omp.sdk.export import ExportDocument

from .admin import export_record_payload, import_record
from .composition import create_runtime
from .official import run_stdio


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Memory Protocol MCP server")
    parser.add_argument(
        "--demo-backend", action="store_true", help="explicitly use the local file demo backend"
    )
    parser.add_argument("--data-file", help="demo backend persistence file")
    parser.add_argument("--admin-export", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--admin-import", help=argparse.SUPPRESS)
    parser.add_argument("--owner-id", help=argparse.SUPPRESS)
    parser.add_argument("--include-embeddings", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--m1-http", action="store_true", help="run the authenticated local M1 HTTP boundary"
    )
    parser.add_argument(
        "--cloud-http", action="store_true", help="run the fail-closed hosted HTTP boundary"
    )
    parser.add_argument("--host", default="127.0.0.1", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=8000, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.m1_http and args.cloud_http:
        parser.error("--m1-http and --cloud-http are mutually exclusive")
    if args.cloud_http:
        import uvicorn

        from .official import create_fail_closed_cloud_http_app

        uvicorn.run(create_fail_closed_cloud_http_app(), host=args.host, port=args.port, log_level="warning")
        return
    if args.m1_http:
        import uvicorn

        from .official import create_m1_http_app

        uvicorn.run(create_m1_http_app(), host=args.host, port=args.port, log_level="warning")
        return
    settings = OMPSettings(demo_data_file=args.data_file) if args.data_file else None
    runtime = create_runtime(settings, demo_backend=args.demo_backend)
    if args.admin_export or args.admin_import:
        try:
            result = anyio.run(_run_admin, runtime, args)
            print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        except AdminFailure as exc:
            print(json.dumps({"error": {"code": exc.code, "message": exc.message}}))
            raise SystemExit(exc.exit_code) from None
        return
    try:
        run_stdio(runtime)
    except RuntimeError:
        print("server unavailable: readiness check failed", file=sys.stderr)
        raise SystemExit(78) from None


class AdminFailure(RuntimeError):
    def __init__(self, code: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


async def _run_admin(runtime: Any, args: argparse.Namespace) -> dict[str, Any]:
    try:
        await runtime.startup()
        if runtime.service is None:
            raise AdminFailure("dependency_unavailable", "admin service unavailable", 7)
        if runtime.backend == "demo":
            return _run_demo_admin(runtime.service, args)
        if args.admin_export:
            if not args.owner_id:
                raise AdminFailure(
                    "validation_error", "owner_id is required for Postgres export", 2
                )
            records = await runtime.service.export_memories(
                owner_id=args.owner_id, include_embeddings=args.include_embeddings
            )
            return {
                "records": [
                    export_record_payload(item, include_embeddings=args.include_embeddings)
                    for item in records
                ]
            }
        source = (
            sys.stdin.read()
            if args.admin_import == "-"
            else Path(args.admin_import).read_text(encoding="utf-8")
        )
        document = ExportDocument.model_validate(json.loads(source))
        if not document.memories:
            return {"imported": 0, "replayed": 0}
        owner_id = args.owner_id or document.memories[0].owner_id
        if any(record.owner_id != owner_id for record in document.memories):
            raise AdminFailure("validation_error", "export contains multiple owners", 2)
        result = await runtime.service.import_memories(
            owner_id=owner_id, records=tuple(import_record(item) for item in document.memories)
        )
        return {"imported": result.imported, "replayed": result.replayed}
    except AdminFailure:
        raise
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
        raise AdminFailure("validation_error", "invalid export package", 2) from None
    except ImportConflictError:
        raise AdminFailure("version_conflict", "export conflicts with existing memory", 4) from None
    except (EmbeddingProfileMismatchError, ValidationError):
        raise AdminFailure("validation_error", "export package is not acceptable", 2) from None
    except NotFoundError:
        raise AdminFailure("not_found", "export reference was not found", 3) from None
    except RuntimeError:
        raise AdminFailure("dependency_unavailable", "Postgres is not ready", 7) from None
    except OMPError:
        raise AdminFailure("internal_error", "export/import could not be completed", 1) from None
    finally:
        await runtime.close()


def _run_demo_admin(service: Any, args: argparse.Namespace) -> dict[str, Any]:
    if args.admin_export:
        records = service.export_records(owner_id=args.owner_id, include_embeddings=False)
        return {"records": records}
    source = (
        sys.stdin.read()
        if args.admin_import == "-"
        else Path(args.admin_import).read_text(encoding="utf-8")
    )
    payload = json.loads(source)
    return {"imported": int(service.import_records(payload["memories"])), "replayed": 0}


if __name__ == "__main__":
    main()
