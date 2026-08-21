from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_english_and_portuguese_development_protocols_are_separate(tmp_path: Path) -> None:
    for language in ("en", "pt"):
        output = tmp_path / f"{language}.json"
        completed = subprocess.run(
            [
                str(ROOT / "scripts/run-development-evals"),
                "--language",
                language,
                "--output",
                str(output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["split"] == "development"
        assert report["holdout_executed"] is False
        assert report["metrics"]["cases"] == 20
        assert report["metrics"]["passed"] == 20
