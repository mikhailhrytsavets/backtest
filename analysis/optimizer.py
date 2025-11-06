"""Very small grid-search optimiser."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable, Dict, Iterable, Tuple


@dataclass
class ParameterGrid:
    grid: Dict[str, Iterable]

    def __iter__(self):
        keys = list(self.grid.keys())
        for values in product(*(self.grid[key] for key in keys)):
            yield dict(zip(keys, values))


@dataclass
class Optimizer:
    parameter_grid: ParameterGrid
    evaluate: Callable[[Dict], float]

    def run(self) -> Tuple[Dict, float]:
        best_score = float("-inf")
        best_params: Dict | None = None
        for params in self.parameter_grid:
            score = self.evaluate(params)
            if score > best_score:
                best_score = score
                best_params = params
        return best_params or {}, best_score
