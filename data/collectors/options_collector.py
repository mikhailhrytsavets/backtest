"""Simplified offline implementation of the options data collector."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd


class OptionsCollector:
    """Collect synthetic options data.

    The real project described in the README would connect to Bybit's API.  For
    the purposes of the kata we instead generate deterministic pseudo-random
    data that mimics the structure of the exchange responses.  This allows the
    rest of the backtesting stack to be exercised without requiring network
    connectivity or API credentials.
    """

    def __init__(self, seed: int | None = None) -> None:
        self.random = np.random.default_rng(seed)

    async def fetch_instruments_info(self, base_coin: str) -> pd.DataFrame:
        expiries = [datetime.utcnow().date() + timedelta(days=d) for d in (1, 7, 14, 30)]
        strikes = np.linspace(0.8, 1.2, num=5)
        records: List[Dict[str, object]] = []
        for expiry in expiries:
            for strike_mult in strikes:
                strike_price = round(50000 * strike_mult, 2)
                records.append(
                    {
                        "symbol": f"{base_coin}-{expiry:%d%b%y}-{int(strike_price)}-C",
                        "strike_price": strike_price,
                        "expiry_date": expiry,
                        "option_type": "Call",
                        "status": "Trading",
                        "base_coin": base_coin,
                    }
                )
                records.append(
                    {
                        "symbol": f"{base_coin}-{expiry:%d%b%y}-{int(strike_price)}-P",
                        "strike_price": strike_price,
                        "expiry_date": expiry,
                        "option_type": "Put",
                        "status": "Trading",
                        "base_coin": base_coin,
                    }
                )
        await asyncio.sleep(0)
        return pd.DataFrame.from_records(records)

    async def fetch_option_klines(
        self, symbol: str, interval: str, start_time: int, end_time: int
    ) -> pd.DataFrame:
        timestamps = _generate_timestamps(start_time, end_time, interval)
        base_price = 10 + 0.1 * np.sin(np.linspace(0, 5, len(timestamps)))
        noise = self.random.normal(0, 0.2, size=len(timestamps))

        close = np.maximum(base_price + noise, 0.1)
        high = close + self.random.random(len(timestamps)) * 0.2
        low = np.maximum(close - self.random.random(len(timestamps)) * 0.2, 0.05)
        open_ = close + self.random.normal(0, 0.1, len(timestamps))

        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": self.random.integers(1, 100, len(timestamps)),
                "turnover": close * self.random.integers(1, 100, len(timestamps)),
                "symbol": symbol,
            }
        )
        await asyncio.sleep(0)
        return df

    async def fetch_option_tickers(self, symbol: str) -> Dict:
        mark_price = float(self.random.uniform(5, 20))
        bid_price = mark_price * 0.99
        ask_price = mark_price * 1.01
        greeks = {
            "delta": float(self.random.uniform(-1, 1)),
            "gamma": float(self.random.uniform(-0.1, 0.1)),
            "vega": float(self.random.uniform(0, 0.5)),
            "theta": float(self.random.uniform(-0.1, 0.1)),
            "rho": float(self.random.uniform(-0.1, 0.1)),
        }
        await asyncio.sleep(0)
        return {
            "symbol": symbol,
            "bid1_price": bid_price,
            "ask1_price": ask_price,
            "mark_price": mark_price,
            "mark_iv": float(self.random.uniform(0.5, 1.0)),
            "underlying_price": float(self.random.uniform(40000, 60000)),
            "volume": int(self.random.integers(10, 500)),
            "greeks": greeks,
            "expiry_date": datetime.utcnow() + timedelta(days=7),
        }

    async def fetch_historical_volatility(
        self, base_coin: str, period: int, start_time: int, end_time: int
    ) -> pd.DataFrame:
        timestamps = _generate_timestamps(start_time, end_time, "1h")
        vols = np.clip(
            0.5
            + 0.1 * np.sin(np.linspace(0, 4, len(timestamps)))
            + self.random.normal(0, 0.02, len(timestamps)),
            0.1,
            2.0,
        )
        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "period": period,
                "volatility": vols,
                "base_coin": base_coin,
            }
        )
        await asyncio.sleep(0)
        return df


def _generate_timestamps(start: int, end: int, interval: str) -> Iterable[pd.Timestamp]:
    delta = _interval_to_timedelta(interval)
    start_ts = pd.to_datetime(start, unit="ms")
    end_ts = pd.to_datetime(end, unit="ms")
    current = start_ts
    timestamps = []
    while current <= end_ts:
        timestamps.append(current)
        current += delta
    return timestamps


def _interval_to_timedelta(interval: str) -> timedelta:
    mapping = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "1d": timedelta(days=1),
    }
    if interval not in mapping:
        raise ValueError(f"Unsupported interval: {interval}")
    return mapping[interval]
