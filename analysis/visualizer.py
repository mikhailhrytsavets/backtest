"""Visualisation helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def plot_equity_curve(equity_curve: pd.Series, path: Optional[Path] = None) -> Path:
    path = path or Path("equity_curve.png")
    plt.figure(figsize=(10, 4))
    equity_curve.sort_index().plot()
    plt.title("Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path
