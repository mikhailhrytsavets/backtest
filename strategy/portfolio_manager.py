"""High level orchestrator for strategy components."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List

import pandas as pd

from .base_strategy import BaseStrategy, TradeSignal


@dataclass
class PortfolioManager:
    components: Iterable[BaseStrategy]
    capital: float = 1_000_000.0
    allocations: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.components = list(self.components)
        if not self.components:
            raise ValueError("At least one strategy component is required")
        total_allocation = sum(self.allocations.values()) if self.allocations else 1.0
        if total_allocation <= 0:
            total_allocation = 1.0
        self.normalised_allocations = {
            component.name: self.allocations.get(component.name, 1 / len(self.components)) / total_allocation
            for component in self.components
        }

    def generate_signals(
        self, market_data: pd.DataFrame, options_chain: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        for component in self.components:
            signals.extend(component.generate_signals(market_data, options_chain, timestamp))
        return signals

    def manage_positions(
        self, current_positions: Dict[str, List[Dict]], market_data: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        for component in self.components:
            component_positions = current_positions.get(component.name, [])
            signals.extend(component.manage_positions(component_positions, market_data, timestamp))
        return signals
