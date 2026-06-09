from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class RunLogger:
    def __init__(self, root: Path) -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_dir = root / stamp
        self.screenshot_dir = self.run_dir / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.run_dir / "events.jsonl"

    def log(self, event: str, payload: dict[str, Any]) -> None:
        record = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            "payload": payload,
        }
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def screenshot_path(self, step: int) -> Path:
        return self.screenshot_dir / f"step-{step:03d}.png"
