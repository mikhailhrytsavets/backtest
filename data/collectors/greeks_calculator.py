"""Black-Scholes greeks calculator."""
from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, sqrt
from typing import Dict

import numpy as np


@dataclass(slots=True)
class OptionContract:
    spot: float
    strike: float
    maturity: float
    rate: float
    volatility: float
    option_type: str  # "call" or "put"


class GreeksCalculator:
    """Simple Black-Scholes implementation."""

    @staticmethod
    def _cdf(x: float) -> float:
        return 0.5 * (1.0 + erf(x / sqrt(2.0)))

    @staticmethod
    def _pdf(x: float) -> float:
        return (1.0 / sqrt(2 * np.pi)) * exp(-0.5 * x * x)

    def _d1_d2(self, contract: OptionContract) -> tuple[float, float]:
        d1 = (
            log(contract.spot / contract.strike)
            + (contract.rate + 0.5 * contract.volatility**2) * contract.maturity
        ) / (contract.volatility * sqrt(contract.maturity))
        d2 = d1 - contract.volatility * sqrt(contract.maturity)
        return d1, d2

    def calculate(self, contract: OptionContract) -> Dict[str, float]:
        if contract.maturity <= 0:
            return {k: 0.0 for k in ("delta", "gamma", "vega", "theta", "rho")}

        d1, d2 = self._d1_d2(contract)
        pdf = self._pdf(d1)
        cdf_d1 = self._cdf(d1)
        cdf_d2 = self._cdf(d2)
        is_call = contract.option_type.lower().startswith("c")

        if is_call:
            delta = cdf_d1
            theta = (
                -contract.spot * pdf * contract.volatility / (2 * sqrt(contract.maturity))
                - contract.rate * contract.strike * exp(-contract.rate * contract.maturity) * cdf_d2
            )
            rho = contract.strike * contract.maturity * exp(-contract.rate * contract.maturity) * cdf_d2
        else:
            delta = cdf_d1 - 1
            theta = (
                -contract.spot * pdf * contract.volatility / (2 * sqrt(contract.maturity))
                + contract.rate * contract.strike * exp(-contract.rate * contract.maturity) * self._cdf(-d2)
            )
            rho = -contract.strike * contract.maturity * exp(-contract.rate * contract.maturity) * self._cdf(-d2)

        gamma = pdf / (contract.spot * contract.volatility * sqrt(contract.maturity))
        vega = contract.spot * pdf * sqrt(contract.maturity) / 100

        return {
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta": float(theta / 365),
            "rho": float(rho / 100),
        }
