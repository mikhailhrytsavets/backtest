"""Base classes for strategy components."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

import pandas as pd


@dataclass
class TradeSignal:
    action: str
    symbol: str
    quantity: int
    side: str
    reason: str
    component: str
    metadata: Dict[str, float] = field(default_factory=dict)


class BaseStrategy(ABC):
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.positions: List[Dict] = []
        self.signals_history: List[TradeSignal] = []

    @abstractmethod
    def generate_signals(
        self, market_data: pd.DataFrame, options_chain: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        raise NotImplementedError

    @abstractmethod
    def manage_positions(
        self, current_positions: List[Dict], market_data: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        raise NotImplementedError

    def calculate_portfolio_greeks(self, positions: List[Dict], options_chain: pd.DataFrame) -> Dict:
        if not positions or options_chain.empty:
            return {k: 0.0 for k in ("delta", "gamma", "vega", "theta", "rho")}
        aggregated = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}
        greeks_map = options_chain.set_index("symbol")
        for position in positions:
            symbol = position["symbol"]
            quantity = position.get("quantity", 0)
            side = 1 if position.get("side") == "buy" else -1
            if symbol not in greeks_map.index:
                continue
            greeks = greeks_map.loc[symbol][["delta", "gamma", "vega", "theta", "rho"]]
            for greek, value in greeks.items():
                aggregated[greek] += float(value) * quantity * side
        return aggregated
