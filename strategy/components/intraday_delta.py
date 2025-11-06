"""Momentum driven delta component."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd

from ..base_strategy import BaseStrategy, TradeSignal


class IntradayDelta(BaseStrategy):
    def __init__(self, config: Dict):
        super().__init__("Intraday Delta", config)
        self.lookback = config.get("lookback", 20)
        self.threshold = config.get("threshold", 0.05)

    def generate_signals(
        self, market_data: pd.DataFrame, options_chain: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        if len(market_data) < self.lookback:
            return []
        recent = market_data.tail(self.lookback)
        returns = recent["underlying_price"].pct_change().dropna()
        momentum = returns.mean()
        if momentum > self.threshold:
            side = "buy"
        elif momentum < -self.threshold:
            side = "sell"
        else:
            return []

        symbol = options_chain["symbol"].iloc[0] if not options_chain.empty else "FUTURES"
        signal = TradeSignal(
            action="open",
            symbol=str(symbol),
            quantity=1,
            side=side,
            reason="intraday_delta_momentum",
            component=self.name,
            metadata={"momentum": float(momentum)},
        )
        self.signals_history.append(signal)
        return [signal]

    def manage_positions(
        self, current_positions: List[Dict], market_data: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if not current_positions:
            return signals
        latest_return = market_data["underlying_price"].pct_change().iloc[-1]
        if abs(latest_return) < self.threshold / 2:
            for position in current_positions:
                signals.append(
                    TradeSignal(
                        action="close",
                        symbol=position["symbol"],
                        quantity=position["quantity"],
                        side="sell" if position["side"] == "buy" else "buy",
                        reason="mean_reversion",
                        component=self.name,
                    )
                )
        return signals
