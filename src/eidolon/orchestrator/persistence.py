from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters.base import TaskResult


class PlacementRecorder:
    """Persist placement + execution outcomes for auditing."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, placement: dict[str, Any], result: TaskResult) -> None:
        entry = {
            **placement,
            "final_status": result.status,
            "attempt": result.attempt,
            "outputs": result.outputs,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
