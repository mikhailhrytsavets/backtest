"""Trend following delta component."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd

from ..base_strategy import BaseStrategy, TradeSignal


class PositionalDelta(BaseStrategy):
    def __init__(self, config: Dict):
        super().__init__("Positional Delta", config)
        self.trend_lookback = config.get("trend_lookback", 50)

    def generate_signals(
        self, market_data: pd.DataFrame, options_chain: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        if len(market_data) < self.trend_lookback:
            return []
        long_ma = market_data["underlying_price"].rolling(self.trend_lookback).mean().iloc[-1]
        short_ma = market_data["underlying_price"].rolling(max(2, self.trend_lookback // 2)).mean().iloc[-1]
        if pd.isna(long_ma) or pd.isna(short_ma):
            return []
        if short_ma > long_ma:
            side = "buy"
        elif short_ma < long_ma:
            side = "sell"
        else:
            return []
        symbol = options_chain["symbol"].iloc[0] if not options_chain.empty else "FUTURES"
        signal = TradeSignal(
            action="open",
            symbol=str(symbol),
            quantity=1,
            side=side,
            reason="positional_trend_follow",
            component=self.name,
            metadata={"short_ma": float(short_ma), "long_ma": float(long_ma)},
        )
        self.signals_history.append(signal)
        return [signal]

    def manage_positions(
        self, current_positions: List[Dict], market_data: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        if len(market_data) < self.trend_lookback:
            return []
        long_ma = market_data["underlying_price"].rolling(self.trend_lookback).mean().iloc[-1]
        short_ma = market_data["underlying_price"].rolling(max(2, self.trend_lookback // 2)).mean().iloc[-1]
        if pd.isna(long_ma) or pd.isna(short_ma):
            return []
        signals: List[TradeSignal] = []
        trend_side = "buy" if short_ma > long_ma else "sell"
        for position in current_positions:
            if position["side"] != trend_side:
                signals.append(
                    TradeSignal(
                        action="close",
                        symbol=position["symbol"],
                        quantity=position["quantity"],
                        side="sell" if position["side"] == "buy" else "buy",
                        reason="trend_flip",
                        component=self.name,
                    )
                )
        return signals
