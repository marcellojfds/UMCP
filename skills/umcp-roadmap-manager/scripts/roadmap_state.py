#!/usr/bin/env python3
"""Parse the UMCP roadmap implementation checklist."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

START = "<!-- roadmap-manager:start -->"
END = "<!-- roadmap-manager:end -->"
LINE_RE = re.compile(
    r"^- \[(?P<mark>[ xX])\] (?P<id>[A-Z][A-Z0-9]*) \| "
    r"model=(?P<model>terra|luna|audit) \| depends=(?P<depends>[^|]+?) \| "
    r"checkpoint=(?P<checkpoint>[^|]+?) \| title=(?P<title>.+)$"
)


@dataclass(frozen=True)
class Item:
    id: str
    complete: bool
    model: str
    depends: list[str]
    checkpoint: str | None
    title: str
    line_index: int


class ChecklistError(ValueError):
    pass


def read_text(path: Path, repo: Path | None, git_ref: str | None) -> str:
    if not git_ref:
        return path.read_text(encoding="utf-8")
    if repo is None:
        raise ChecklistError("--repo is required with --git-ref")
    rel = path.relative_to(repo) if path.is_absolute() else path
    result = subprocess.run(
        ["git", "show", f"{git_ref}:{rel.as_posix()}"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ChecklistError(result.stderr.strip() or "git show failed")
    return result.stdout


def parse(text: str) -> list[Item]:
    lines = text.splitlines()
    try:
        start = lines.index(START)
        end = lines.index(END, start + 1)
    except ValueError as exc:
        raise ChecklistError("roadmap manager markers are missing") from exc

    items: list[Item] = []
    for index in range(start + 1, end):
        if not lines[index].strip():
            continue
        match = LINE_RE.fullmatch(lines[index])
        if not match:
            raise ChecklistError(f"invalid checklist line {index + 1}: {lines[index]}")
        raw_depends = match.group("depends").strip()
        checkpoint = match.group("checkpoint").strip()
        items.append(
            Item(
                id=match.group("id"),
                complete=match.group("mark").lower() == "x",
                model=match.group("model"),
                depends=[] if raw_depends == "-" else [d.strip() for d in raw_depends.split(",")],
                checkpoint=None if checkpoint == "-" else checkpoint,
                title=match.group("title").strip(),
                line_index=index,
            )
        )
    if not items:
        raise ChecklistError("checklist is empty")
    return items


def snapshot(items: list[Item]) -> dict[str, object]:
    completed = {item.id for item in items if item.complete}
    ready = [
        item
        for item in items
        if not item.complete and all(dep in completed for dep in item.depends)
    ]
    return {
        "total": len(items),
        "completed": len(completed),
        "percent_complete": round(100 * len(completed) / len(items), 1),
        "remaining": len(items) - len(completed),
        "completed_ids": [item.id for item in items if item.complete],
        "ready": [asdict(item) | {"line_index": item.line_index + 1} for item in ready],
        "ready_count": len(ready),
        "blocked_count": len(items) - len(completed) - len(ready),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--git-ref")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = snapshot(parse(read_text(args.file, args.repo, args.git_ref)))
    except (ChecklistError, OSError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"completed={result['completed']}/{result['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
