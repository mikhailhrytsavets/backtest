"""Gamma helper utilities."""
from __future__ import annotations

import pandas as pd


def gamma_pressure(chain: pd.DataFrame) -> float:
    if chain.empty or "gamma" not in chain.columns:
        return 0.0
    weighted = (chain["gamma"] * chain.get("volume", 1)).sum()
    volume = chain.get("volume", 1).sum()
    return float(weighted / volume) if volume else 0.0
