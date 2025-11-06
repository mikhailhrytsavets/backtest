"""Backtesting engine implementation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

import pandas as pd

from .execution import ExecutionModel
from .performance import PerformanceReport
from .position import Position
from .risk_manager import RiskManager
from strategy.base_strategy import TradeSignal
from strategy.portfolio_manager import PortfolioManager


@dataclass
class BacktestResult:
    trades: List[Dict]
    equity_curve: pd.Series

    def performance(self) -> PerformanceReport:
        return PerformanceReport(self.equity_curve)


@dataclass
class BacktestEngine:
    portfolio: PortfolioManager
    execution_model: ExecutionModel = field(default_factory=ExecutionModel)
    risk_manager: RiskManager | None = None

    def run(
        self,
        market_data: pd.DataFrame,
        options_chain_provider: Dict[datetime, pd.DataFrame],
        initial_capital: float = 1_000_000.0,
    ) -> BacktestResult:
        equity = initial_capital
        equity_curve = []
        trades: List[Dict] = []
        open_positions: Dict[str, List[Position]] = {component.name: [] for component in self.portfolio.components}

        market_data = market_data.sort_values("timestamp")
        for _, row in market_data.iterrows():
            timestamp: datetime = pd.to_datetime(row["timestamp"]).to_pydatetime()
            snapshot = market_data[market_data["timestamp"] <= row["timestamp"]]
            options_chain = options_chain_provider.get(timestamp, pd.DataFrame())

            generated = self.portfolio.generate_signals(snapshot, options_chain, timestamp)
            managed = self.portfolio.manage_positions(
                {name: [pos.__dict__ for pos in positions] for name, positions in open_positions.items()},
                snapshot,
                timestamp,
            )
            signals = generated + managed

            for signal in signals:
                signal_dict = signal.__dict__ if isinstance(signal, TradeSignal) else signal
                price = float(row.get("close", row.get("underlying_price", 0.0)))
                execution = self.execution_model.execute(signal_dict, price, timestamp)
                trades.append(execution)
                component_name = signal_dict.get("component", "unknown")

                if signal_dict["action"] == "open":
                    open_positions.setdefault(component_name, []).append(
                        Position(
                            symbol=signal_dict["symbol"],
                            side=signal_dict["side"],
                            quantity=signal_dict["quantity"],
                            entry_price=execution["price"],
                            entry_time=timestamp,
                            metadata=signal_dict.get("metadata", {}),
                        )
                    )
                    equity -= execution["price"] * signal_dict["quantity"]
                elif signal_dict["action"] == "close":
                    positions = open_positions.get(component_name, [])
                    if not positions:
                        continue
                    position = positions.pop(0)
                    result = position.close(execution["price"], timestamp)
                    equity += execution["price"] * signal_dict["quantity"] + result["pnl"] - execution["fee"]

            equity_curve.append((timestamp, equity))

        equity_series = pd.Series({ts: value for ts, value in equity_curve})
        return BacktestResult(trades=trades, equity_curve=equity_series)
