"""Performance analytics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass
class PerformanceReport:
    equity_curve: pd.Series

    def sharpe_ratio(self) -> float:
        returns = self.equity_curve.pct_change().dropna()
        if returns.empty:
            return 0.0
        return float(np.sqrt(252) * returns.mean() / returns.std())

    def max_drawdown(self) -> float:
        cumulative_max = self.equity_curve.cummax()
        drawdowns = (self.equity_curve - cumulative_max) / cumulative_max
        return float(drawdowns.min())

    def summary(self) -> Dict[str, float]:
        return {"sharpe": self.sharpe_ratio(), "max_drawdown": self.max_drawdown(), "total_return": float(self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1)}
