"""Portfolio risk controls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class RiskManager:
    config: Dict

    def __post_init__(self) -> None:
        self.max_portfolio_var = self.config.get("max_portfolio_var_pct", 5) / 100
        self.max_single_position_pct = self.config.get("max_single_position_pct", 2) / 100
        self.max_component_drawdown = self.config.get("max_component_drawdown", 10) / 100

    def calculate_var(
        self, positions: List[Dict], market_data: pd.DataFrame, confidence_level: float = 0.99
    ) -> float:
        if market_data.empty:
            return 0.0
        returns = market_data["returns"].dropna()
        if returns.empty:
            return 0.0
        sorted_returns = np.sort(returns)
        index = int((1 - confidence_level) * len(sorted_returns))
        var = -sorted_returns[index]
        return float(var)

    def check_risk_limits(self, portfolio_value: float, positions: List[Dict]) -> bool:
        if not positions:
            return True
        max_position_value = max(abs(p.get("notional", 0.0)) for p in positions)
        if max_position_value > portfolio_value * self.max_single_position_pct:
            return False
        return True
