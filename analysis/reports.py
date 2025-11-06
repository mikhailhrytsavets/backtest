"""Textual reporting utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from backtest.performance import PerformanceReport


@dataclass
class ReportBuilder:
    performance: PerformanceReport

    def build(self) -> Dict[str, float]:
        return self.performance.summary()
