"""Very small in-memory cache implementation used by collectors."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


@dataclass
class Cache:
    ttl: float = 60.0
    storage: Dict[str, CacheEntry] = field(default_factory=dict)

    def get(self, key: str) -> Optional[Any]:
        entry = self.storage.get(key)
        if not entry:
            return None
        if entry.expires_at < time.time():
            self.storage.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        self.storage[key] = CacheEntry(value=value, expires_at=time.time() + self.ttl)

    def clear(self) -> None:
        self.storage.clear()
