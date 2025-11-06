from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("pandas")
pytest.importorskip("numpy")

from data.collectors.options_collector import OptionsCollector
from data.collectors.futures_collector import FuturesCollector
from data.collectors.volatility_collector import VolatilityCollector


def test_collectors_produce_data():
    async def _collect():
        options = OptionsCollector(seed=0)
        futures = FuturesCollector(seed=0)
        volatility = VolatilityCollector(seed=0)
        instruments = await options.fetch_instruments_info("BTC")
        assert not instruments.empty
        now = 1_600_000_000_000
        klines = await options.fetch_option_klines(instruments.iloc[0].symbol, "1m", now, now + 3_600_000)
        assert not klines.empty
        ticker = await options.fetch_option_tickers(instruments.iloc[0].symbol)
        assert "mark_price" in ticker
        futures_df = await futures.fetch_futures_klines("BTCUSDT", "1h", now, now + 86_400_000)
        assert not futures_df.empty
        funding = await futures.fetch_funding_rate("BTCUSDT", now, now + 86_400_000)
        assert not funding.empty
        vol = await volatility.fetch("BTC", days=10)
        assert not vol.empty
    asyncio.run(_collect())
