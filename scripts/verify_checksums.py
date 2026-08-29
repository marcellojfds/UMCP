#!/usr/bin/env python3
"""Deterministic verification of canonical payload checksums and file SHA-256 digests."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent


def compute_canonical_checksum(payload: dict) -> str:
    """Compute the report checksum without importing the application package."""
    clean_payload = {key: value for key, value in payload.items() if key != "checksum"}
    canonical_bytes = json.dumps(clean_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"


def compute_file_sha256(file_path: Path) -> str:
    """Compute the SHA-256 digest of a report file using only the standard library."""
    return f"sha256:{hashlib.sha256(file_path.read_bytes()).hexdigest()}"


def verify_report(json_path: Path, md_path: Path) -> bool:
    print(f"[*] Verifying {json_path.name} and {md_path.name}...")
    if not json_path.exists() or not md_path.exists():
        print(f"    [!] Error: Files {json_path} or {md_path} missing.", file=sys.stderr)
        return False

    raw_json = json_path.read_text(encoding="utf-8")
    data = json.loads(raw_json)

    recorded_canonical = data.get("checksum")
    computed_canonical = compute_canonical_checksum(data)
    if recorded_canonical != computed_canonical:
        print(f"    [!] Canonical checksum mismatch:", file=sys.stderr)
        print(f"        Recorded: {recorded_canonical}", file=sys.stderr)
        print(f"        Computed: {computed_canonical}", file=sys.stderr)
        return False
    print(f"    [+] Canonical payload checksum matches: {computed_canonical}")

    actual_file_sha256 = compute_file_sha256(json_path)
    md_content = md_path.read_text(encoding="utf-8")

    expected_file_marker = f"- **Checksum do Arquivo JSON (SHA-256):** `{actual_file_sha256}`"
    if expected_file_marker not in md_content:
        print(f"    [!] Markdown file_sha256 marker mismatch against disk file:", file=sys.stderr)
        print(f"        Actual file SHA-256: {actual_file_sha256}", file=sys.stderr)
        return False
    print(f"    [+] Markdown references exact file SHA-256: {actual_file_sha256}")

    expected_canonical_marker = f"- **Checksum do Payload Canônico (SHA-256):** `{computed_canonical}`"
    if expected_canonical_marker not in md_content:
        print(f"    [!] Markdown canonical checksum marker mismatch:", file=sys.stderr)
        print(f"        Expected: {expected_canonical_marker}", file=sys.stderr)
        return False
    print(f"    [+] Markdown references exact canonical payload checksum: {computed_canonical}")

    return True


def main() -> int:
    reports = [
        (
            repo_root / "docs/handoffs/roadmap/C01-SDK-RUNNER-REPORT-20260828.json",
            repo_root / "docs/handoffs/roadmap/C01-SDK-RUNNER-REPORT-20260828.md",
        ),
        (
            repo_root / "docs/handoffs/roadmap/C02-CONTROLLED-AGENT-REPORT-20260828.json",
            repo_root / "docs/handoffs/roadmap/C02-CONTROLLED-AGENT-REPORT-20260828.md",
        ),
        (
            repo_root / "docs/handoffs/roadmap/CONTAINMENT-REPORT-20260828.json",
            repo_root / "docs/handoffs/roadmap/CONTAINMENT-REPORT-20260828.md",
        ),
    ]

    all_ok = True
    for j_path, m_path in reports:
        if not verify_report(j_path, m_path):
            all_ok = False

    if not all_ok:
        print("\n[!] VERIFICATION FAILED", file=sys.stderr)
        return 1

    print("\n[+] ALL REPORT CHECKSUMS AND DISK HASHES DETERMINISTICALLY VERIFIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
