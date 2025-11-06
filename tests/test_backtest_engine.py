from __future__ import annotations

import asyncio
from datetime import datetime

import pytest

pytest.importorskip("pandas")
pytest.importorskip("numpy")

import pandas as pd

from backtest.engine import BacktestEngine
from backtest.risk_manager import RiskManager
from data.collectors.options_collector import OptionsCollector
from data.collectors.futures_collector import FuturesCollector
from data.collectors.volatility_collector import VolatilityCollector
from data.preprocessor import MarketDataBundle, compute_returns, merge_market_data
from strategy.components.intraday_delta import IntradayDelta
from strategy.components.intraday_short_gamma import IntradayShortGamma
from strategy.components.positional_delta import PositionalDelta
from strategy.components.positional_short_gamma import PositionalShortGamma
from strategy.portfolio_manager import PortfolioManager


async def _prepare_data():
    options_collector = OptionsCollector(seed=1)
    futures_collector = FuturesCollector(seed=1)
    volatility_collector = VolatilityCollector(seed=1)
    now = datetime.utcnow()
    start = int((now - pd.Timedelta(hours=10)).timestamp() * 1000)
    end = int(now.timestamp() * 1000)
    instruments = await options_collector.fetch_instruments_info("BTC")
    option_klines = await options_collector.fetch_option_klines(instruments.iloc[0].symbol, "1h", start, end)
    futures_klines = await futures_collector.fetch_futures_klines("BTCUSDT", "1h", start, end)
    volatility = await volatility_collector.fetch("BTC", days=option_klines["timestamp"].nunique())
    bundle = MarketDataBundle(options=option_klines, futures=futures_klines, volatility=volatility)
    merged = compute_returns(merge_market_data(bundle))
    chain = {
        pd.to_datetime(ts).to_pydatetime(): instruments.head(5).assign(delta=0.5, gamma=0.01, theta=0.02, rho=0.01)
        for ts in merged["timestamp"].unique()
    }
    return merged, chain


def test_backtest_engine_runs():
    market_data, chain = asyncio.run(_prepare_data())
    components = [
        IntradayShortGamma({}),
        IntradayDelta({"threshold": 0.0001}),
        PositionalShortGamma({}),
        PositionalDelta({"trend_lookback": 4}),
    ]
    portfolio = PortfolioManager(components=components)
    engine = BacktestEngine(portfolio=portfolio, risk_manager=RiskManager({}))
    result = engine.run(market_data, chain, initial_capital=100_000)
    assert not result.equity_curve.empty
    assert isinstance(result.performance().summary(), dict)
