"""Representation of an open position."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class Position:
    symbol: str
    side: str
    quantity: int
    entry_price: float
    entry_time: datetime
    metadata: Dict[str, float] = field(default_factory=dict)
    status: str = "open"

    def close(self, exit_price: float, exit_time: datetime) -> Dict[str, float]:
        pnl = (exit_price - self.entry_price) * self.quantity
        if self.side == "sell":
            pnl = -pnl
        self.status = "closed"
        return {"pnl": pnl, "exit_time": exit_time, "exit_price": exit_price}
