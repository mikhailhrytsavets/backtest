"""Historical volatility helper."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict

import numpy as np
import pandas as pd


class VolatilityCollector:
    def __init__(self, seed: int | None = None) -> None:
        self.random = np.random.default_rng(seed)

    async def fetch(self, base_coin: str, days: int, end: datetime | None = None) -> pd.DataFrame:
        end = end or datetime.utcnow()
        timestamps = [end - timedelta(days=i) for i in range(days)][::-1]
        vol = np.clip(
            0.6
            + 0.2 * np.sin(np.linspace(0, 2 * np.pi, days))
            + self.random.normal(0, 0.05, days),
            0.1,
            2.5,
        )
        df = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(timestamps),
                "volatility": vol,
                "base_coin": base_coin,
            }
        )
        await asyncio.sleep(0)
        return df
