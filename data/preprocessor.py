"""Utilities for aligning and enriching raw market data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd


@dataclass
class MarketDataBundle:
    options: pd.DataFrame
    futures: pd.DataFrame
    volatility: pd.DataFrame


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()
    renamed.columns = [col.lower() for col in renamed.columns]
    return renamed


def merge_market_data(bundle: MarketDataBundle) -> pd.DataFrame:
    options = normalise_columns(bundle.options)
    futures = normalise_columns(bundle.futures)
    volatility = normalise_columns(bundle.volatility)

    merged = options.merge(
        futures[["timestamp", "close"]].rename(columns={"close": "underlying_price"}),
        on="timestamp",
        how="left",
    )
    merged = merged.merge(volatility[["timestamp", "volatility"]], on="timestamp", how="left")
    merged.sort_values("timestamp", inplace=True)
    merged.ffill(inplace=True)
    return merged


def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched["returns"] = enriched["close"].pct_change().fillna(0.0)
    return enriched
