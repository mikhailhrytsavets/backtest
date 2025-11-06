"""Synthetic futures data collector."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Dict

import numpy as np
import pandas as pd

from .options_collector import _generate_timestamps


class FuturesCollector:
    def __init__(self, seed: int | None = None) -> None:
        self.random = np.random.default_rng(seed)

    async def fetch_futures_klines(
        self, symbol: str, interval: str, start_time: int, end_time: int
    ) -> pd.DataFrame:
        timestamps = _generate_timestamps(start_time, end_time, interval)
        base_price = 50000 + 500 * np.sin(np.linspace(0, 2, len(timestamps)))
        noise = self.random.normal(0, 100, size=len(timestamps))
        close = base_price + noise
        high = close + np.abs(self.random.normal(0, 50, len(timestamps)))
        low = close - np.abs(self.random.normal(0, 50, len(timestamps)))
        open_ = close + self.random.normal(0, 30, len(timestamps))
        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": self.random.integers(100, 1000, len(timestamps)),
                "symbol": symbol,
            }
        )
        await asyncio.sleep(0)
        return df

    async def fetch_funding_rate(self, symbol: str, start_time: int, end_time: int) -> pd.DataFrame:
        timestamps = _generate_timestamps(start_time, end_time, "1h")
        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "funding_rate": self.random.normal(0, 0.0005, len(timestamps)),
                "symbol": symbol,
            }
        )
        await asyncio.sleep(0)
        return df
