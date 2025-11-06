"""Execution simulator."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class ExecutionModel:
    maker_fee: float = 0.02
    taker_fee: float = 0.05
    slippage_bps: float = 5.0

    def execute(self, signal: Dict, price: float, timestamp: datetime) -> Dict:
        side = signal.get("side", "buy")
        quantity = signal.get("quantity", 0)
        slippage = price * (self.slippage_bps / 10_000)
        execution_price = price + slippage if side == "buy" else price - slippage
        fee_rate = self.taker_fee if side == "buy" else self.maker_fee
        fee = execution_price * quantity * (fee_rate / 100)
        return {
            "symbol": signal["symbol"],
            "side": side,
            "quantity": quantity,
            "price": execution_price,
            "timestamp": timestamp,
            "fee": fee,
        }
