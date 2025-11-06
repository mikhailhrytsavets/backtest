"""Intraday short gamma component."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pandas as pd

from ..base_strategy import BaseStrategy, TradeSignal


class IntradayShortGamma(BaseStrategy):
    def __init__(self, config: Dict):
        super().__init__("Intraday Short Gamma", config)
        self.entry_time = config.get("entry_time", "09:00")
        self.exit_time = config.get("exit_time", "15:00")
        self.max_dte = config.get("max_dte", 3)
        self.delta_hedge_threshold = config.get("delta_hedge_threshold", 0.2)

    def generate_signals(
        self, market_data: pd.DataFrame, options_chain: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        if options_chain.empty:
            return []
        time_str = timestamp.strftime("%H:%M")
        if time_str < self.entry_time or time_str > self.exit_time:
            return []

        underlying_price = market_data["underlying_price"].iloc[-1]

        strike_column = "strike" if "strike" in options_chain.columns else None
        if strike_column is None and "strike_price" in options_chain.columns:
            strike_column = "strike_price"

        if strike_column is None:
            return []

        strikes = pd.to_numeric(options_chain[strike_column], errors="coerce")
        if strikes.isna().all():
            return []

        idx = (strikes - underlying_price).abs().idxmin()
        atm_option = options_chain.loc[idx]
        signal = TradeSignal(
            action="open",
            symbol=str(atm_option["symbol"]),
            quantity=1,
            side="sell",
            reason="intraday_short_gamma",
            component=self.name,
            metadata={"target_delta": float(atm_option.get("delta", 0))},
        )
        self.signals_history.append(signal)
        return [signal]

    def manage_positions(
        self, current_positions: List[Dict], market_data: pd.DataFrame, timestamp: datetime
    ) -> List[TradeSignal]:
        signals: List[TradeSignal] = []
        if not current_positions:
            return signals
        time_str = timestamp.strftime("%H:%M")
        if time_str >= self.exit_time:
            for position in current_positions:
                signals.append(
                    TradeSignal(
                        action="close",
                        symbol=position["symbol"],
                        quantity=position["quantity"],
                        side="buy",
                        reason="session_end",
                        component=self.name,
                    )
                )
        return signals
