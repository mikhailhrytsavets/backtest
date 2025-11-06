"""Delta helper utilities."""
from __future__ import annotations

import pandas as pd


def rolling_zscore(series: pd.Series, window: int = 20) -> pd.Series:
    mean = series.rolling(window).mean()
    std = series.rolling(window).std().replace(0, pd.NA)
    return (series - mean) / std


def crossing_signal(series: pd.Series) -> pd.Series:
    shifted = series.shift(1)
    return (series > 0) & (shifted <= 0)
