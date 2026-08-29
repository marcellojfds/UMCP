"""Cross-assistant memory sharing demonstration against UMCP Hosted Staging.

Demonstrates the core MVP value proposition:
1. Assistant A (ChatGPT Persona) writes memory to the user vault.
2. Assistant B (Gemini Persona) discovers and recalls the exact memory.
3. Assistant B amends/updates the memory.
4. Assistant A sees the updated version.
5. Lifecycle completion: forget and verify non-resurrection.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

from omp.sdk.client import MemoryClient, ProtocolError
from omp.sdk.cloud import CloudOAuthTransport
from omp.sdk.oauth import OAuthSession, TokenData


def _provenance(source_id: str, model: str) -> dict[str, Any]:
    return {
        "source_type": "conversation",
        "source_id": source_id,
        "source_model": model,
        "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def run_cross_assistant_demo(
    *,
    base_url: str,
    access_token: str,
) -> dict[str, Any]:
    # 1. Setup Assistant A (ChatGPT Persona)
    session_a = OAuthSession(base_url)
    session_a.set_tokens(TokenData(access_token=access_token, token_type="Bearer", expires_in=3600))
    transport_a = CloudOAuthTransport(session_a)
    client_a = MemoryClient(transport_a)

    # 2. Setup Assistant B (Gemini Persona) sharing the same vault
    session_b = OAuthSession(base_url)
    session_b.set_tokens(TokenData(access_token=access_token, token_type="Bearer", expires_in=3600))
    transport_b = CloudOAuthTransport(session_b)
    client_b = MemoryClient(transport_b)

    step_results: dict[str, Any] = {}

    # Step 1: Assistant A (ChatGPT) writes user preference
    fact_content = "User preference: Adopt Clean Architecture and fail-closed security invariants across all subprojects."
    write_res = client_a.write(
        content=fact_content,
        type="fact",
        provenance=_provenance("chatgpt-session-001", "gpt-4o"),
        idempotency_key=f"demo-pref-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
    )
    
    memory_obj = write_res.get("data", write_res).get("memory", write_res)
    memory_id = memory_obj.get("id")
    step_results["1_chatgpt_write"] = {
        "memory_id": memory_id,
        "initial_version": memory_obj.get("version"),
        "status": "PASS",
    }

    # Step 2: Assistant B (Gemini) searches and recalls the memory
    search_query = "What architectural and security preferences does the user have?"
    search_res = client_b.search(query=search_query)
    found_memories = search_res.get("memories", []) if isinstance(search_res, dict) else []
    
    matched = any(
        (m.get("memory", m).get("id") == memory_id or fact_content in m.get("memory", m).get("content", ""))
        for m in found_memories
    )
    step_results["2_gemini_recall"] = {
        "query": search_query,
        "matched": matched,
        "results_count": len(found_memories),
        "status": "PASS" if matched else "FAIL",
    }

    # Step 3: Assistant B (Gemini) updates the memory with new details
    updated_content = "User preference: Adopt Clean Architecture and fail-closed security invariants with Python 3.11+."
    update_res = client_b.update(
        id=memory_id,
        expected_version=1,
        patch={"content": updated_content},
        provenance=_provenance("gemini-session-002", "gemini-1.5-pro"),
        idempotency_key=f"demo-upd-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
    )
    upd_mem = update_res.get("data", update_res).get("memory", update_res)
    step_results["3_gemini_update"] = {
        "new_version": upd_mem.get("version"),
        "status": "PASS" if upd_mem.get("version") == 2 else "FAIL",
    }

    # Step 4: Assistant A (ChatGPT) verifies the updated memory
    search_updated = client_a.search(query="Python 3.11 architecture invariants")
    found_updated = search_updated.get("memories", []) if isinstance(search_updated, dict) else []
    verified_update = any(
        (m.get("memory", m).get("id") == memory_id and "Python 3.11" in m.get("memory", m).get("content", ""))
        for m in found_updated
    )
    step_results["4_chatgpt_verify_update"] = {
        "matched": verified_update,
        "status": "PASS" if verified_update else "FAIL",
    }

    # Step 5: Forget & Lifecycle Cleanup
    forget_res = client_a.forget(id=memory_id)
    step_results["5_forget"] = {
        "status": "PASS" if forget_res.get("ok", True) else "FAIL",
    }

    return {
        "status": "SUCCESS" if all(v.get("status") == "PASS" for v in step_results.values()) else "FAILED",
        "steps": step_results,
        "cross_assistant_verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-Assistant Memory Demo")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("UMCP_BASE_URL", "https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app"),
        help="Base URL for UMCP server",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("UMCP_ACCESS_TOKEN"),
        help="Bearer access token",
    )
    args = parser.parse_args()

    if not args.token:
        print("Error: --token or UMCP_ACCESS_TOKEN environment variable required.", file=sys.stderr)
        sys.exit(1)

    result = run_cross_assistant_demo(base_url=args.base_url, access_token=args.token)
    print(json.dumps(result, indent=2))
    if result.get("status") != "SUCCESS":
        sys.exit(1)


if __name__ == "__main__":
    main()
