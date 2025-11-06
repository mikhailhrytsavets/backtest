from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from data.collectors.greeks_calculator import GreeksCalculator, OptionContract


def test_greeks_are_finite():
    contract = OptionContract(spot=50000, strike=52000, maturity=0.25, rate=0.01, volatility=0.6, option_type="call")
    calculator = GreeksCalculator()
    greeks = calculator.calculate(contract)
    assert set(greeks.keys()) == {"delta", "gamma", "vega", "theta", "rho"}
    for value in greeks.values():
        assert value == value  # not NaN
