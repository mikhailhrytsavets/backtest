"""Utility functions for volatility based signals."""
from __future__ import annotations

import pandas as pd


def implied_vs_historical(iv: pd.Series, hv: pd.Series) -> pd.Series:
    spread = iv - hv
    return spread.fillna(0.0)


def realised_volatility(returns: pd.Series, window: int = 30) -> pd.Series:
    return returns.rolling(window).std().fillna(method="bfill")
