from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from app.core.models import StoreEvent


class EventStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: StoreEvent) -> StoreEvent:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(event.json() + "\n")
        return event

    def append_many(self, events: list[StoreEvent]) -> int:
        if not events:
            return 0
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                for event in events:
                    f.write(event.json() + "\n")
        return len(events)

    def all(self, limit: int | None = None) -> list[StoreEvent]:
        if not self.path.exists():
            return []
        events: list[StoreEvent] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(StoreEvent(**json.loads(line)))
        return events[-limit:] if limit else events

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
