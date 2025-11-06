"""Longer term short gamma component."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd

from ..base_strategy import BaseStrategy, TradeSignal


class PositionalShortGamma(BaseStrategy):
    def __init__(self, config: Dict):
        super().__init__("Positional Short Gamma", config)
        self.max_dte = config.get("max_dte", 30)
        self.rebalance_days = config.get("rebalance_days", 5)
        self._last_rebalance: datetime | None = None

    def generate_signals(
        self, market_data: pd.DataFrame, options_chain: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        if options_chain.empty:
            return []
        if self._last_rebalance and (timestamp - self._last_rebalance).days < self.rebalance_days:
            return []
        eligible = options_chain[options_chain["expiry"] - timestamp <= pd.Timedelta(days=self.max_dte)]
        if eligible.empty:
            return []
        target = eligible.sort_values("theta", ascending=False).head(1).iloc[0]
        signal = TradeSignal(
            action="open",
            symbol=str(target["symbol"]),
            quantity=1,
            side="sell",
            reason="positional_theta_harvest",
            component=self.name,
            metadata={"theta": float(target.get("theta", 0.0))},
        )
        self._last_rebalance = timestamp
        self.signals_history.append(signal)
        return [signal]

    def manage_positions(
        self, current_positions: List[Dict], market_data: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        for position in current_positions:
            opened = position.get("entry_time")
            if opened and (timestamp - opened).days >= self.rebalance_days:
                signals.append(
                    TradeSignal(
                        action="close",
                        symbol=position["symbol"],
                        quantity=position["quantity"],
                        side="buy",
                        reason="rebalance",
                        component=self.name,
                    )
                )
        return signals
