"""Entry point for running a toy backtest."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

try:
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    raise SystemExit(
        "The demo runner requires pandas. Install the optional dependencies via `pip install -r requirements.txt`."
    ) from exc

from analysis.reports import ReportBuilder
from backtest.engine import BacktestEngine
from backtest.risk_manager import RiskManager
from config.settings import load_strategy_params
from data.collectors.futures_collector import FuturesCollector
from data.collectors.options_collector import OptionsCollector
from data.collectors.volatility_collector import VolatilityCollector
from data.preprocessor import MarketDataBundle, compute_returns, merge_market_data
from strategy.components.intraday_delta import IntradayDelta
from strategy.components.intraday_short_gamma import IntradayShortGamma
from strategy.components.positional_delta import PositionalDelta
from strategy.components.positional_short_gamma import PositionalShortGamma
from strategy.portfolio_manager import PortfolioManager


async def load_synthetic_data(base_coin: str) -> tuple[pd.DataFrame, dict]:
    options_collector = OptionsCollector(seed=42)
    futures_collector = FuturesCollector(seed=42)
    volatility_collector = VolatilityCollector(seed=42)

    start = int((datetime.utcnow() - timedelta(days=2)).timestamp() * 1000)
    end = int(datetime.utcnow().timestamp() * 1000)

    instruments = await options_collector.fetch_instruments_info(base_coin)
    klines_tasks = [
        options_collector.fetch_option_klines(row.symbol, "1h", start, end)
        for row in instruments.head(2).itertuples()
    ]
    klines = await asyncio.gather(*klines_tasks)
    options_df = pd.concat(klines, ignore_index=True)
    futures_df = await futures_collector.fetch_futures_klines(f"{base_coin}USDT", "1h", start, end)
    volatility_df = await volatility_collector.fetch(base_coin, days=len(options_df["timestamp"].unique()))

    bundle = MarketDataBundle(options=options_df, futures=futures_df, volatility=volatility_df)
    merged = merge_market_data(bundle)
    merged = compute_returns(merged)

    chain_provider = {
        pd.to_datetime(ts).to_pydatetime(): instruments.assign(delta=0.5, gamma=0.01, theta=0.02, rho=0.01)
        for ts in merged["timestamp"].unique()
    }
    return merged, chain_provider


def build_portfolio() -> PortfolioManager:
    params = load_strategy_params()
    components = [
        IntradayShortGamma(params.get("intraday_short_gamma", {})),
        IntradayDelta(params.get("intraday_delta", {})),
        PositionalShortGamma(params.get("positional_short_gamma", {})),
        PositionalDelta(params.get("positional_delta", {})),
    ]
    allocations = {
        component.name: params.get(component.name.lower().replace(" ", "_"), {}).get("capital_fraction", 0.25)
        for component in components
    }
    return PortfolioManager(components=components, allocations=allocations)


async def main() -> None:
    market_data, chain_provider = await load_synthetic_data("BTC")
    portfolio = build_portfolio()
    engine = BacktestEngine(portfolio=portfolio, risk_manager=RiskManager({}))
    result = engine.run(market_data, chain_provider)
    report = ReportBuilder(result.performance()).build()
    print("Backtest summary:")
    for key, value in report.items():
        print(f"  {key}: {value:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
