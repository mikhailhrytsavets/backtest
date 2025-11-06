from __future__ import annotations

from datetime import datetime

import pytest

pytest.importorskip("pandas")

import pandas as pd

from strategy.components.intraday_short_gamma import IntradayShortGamma
from strategy.components.intraday_delta import IntradayDelta
from strategy.components.positional_short_gamma import PositionalShortGamma
from strategy.components.positional_delta import PositionalDelta


def build_market():
    timestamps = pd.date_range("2024-01-01", periods=10, freq="H")
    market = pd.DataFrame({"timestamp": timestamps, "underlying_price": 50_000 + range(10)})
    chain = pd.DataFrame(
        {
            "symbol": ["BTC-TEST-50000-C"] * 10,
            "strike": [50_000] * 10,
            "expiry": [timestamps[-1]] * 10,
            "theta": [0.02] * 10,
            "delta": [0.5] * 10,
            "gamma": [0.01] * 10,
            "rho": [0.01] * 10,
        }
    )
    return market, chain


def test_intraday_short_gamma_generates_signal():
    market, chain = build_market()
    strategy = IntradayShortGamma({"entry_time": "00:00", "exit_time": "23:00"})
    signals = strategy.generate_signals(market, chain, market["timestamp"].iloc[5].to_pydatetime())
    assert signals


def test_intraday_delta_responds_to_momentum():
    market, chain = build_market()
    strategy = IntradayDelta({"threshold": 0.0, "lookback": 3})
    signals = strategy.generate_signals(market, chain, market["timestamp"].iloc[5].to_pydatetime())
    assert signals


def test_positional_short_gamma_rebalances():
    market, chain = build_market()
    strategy = PositionalShortGamma({"rebalance_days": 0})
    signals = strategy.generate_signals(market, chain, market["timestamp"].iloc[5].to_pydatetime())
    assert signals


def test_positional_delta_trend():
    market, chain = build_market()
    strategy = PositionalDelta({"trend_lookback": 4})
    signals = strategy.generate_signals(market, chain, market["timestamp"].iloc[5].to_pydatetime())
    assert signals
