"""Application settings and helper utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass(slots=True)
class DataPaths:
    """Container describing all filesystem locations used by the project."""

    root: Path = field(default_factory=lambda: Path.cwd())
    data_dir: Path = field(default_factory=lambda: Path.cwd() / "data_store")
    cache_dir: Path = field(default_factory=lambda: Path.cwd() / "cache_store")

    def ensure(self) -> None:
        """Ensure that all directories exist on disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class Settings:
    """Global application settings.

    The README describes a fairly involved architecture.  The goal of this
    configuration module is to centralise runtime options that are used across
    the collectors, storage layer and the backtesting engine.  The default
    values are intentionally conservative so that the project can run in a
    completely offline environment while still resembling the layout of a
    production configuration file.
    """

    bybit_base_url: str = "https://api.bybit.com"
    http_timeout: float = 10.0
    max_concurrent_requests: int = 5
    paths: DataPaths = field(default_factory=DataPaths)
    strategy_params_path: Optional[Path] = None
    database_url: str = field(init=False)

    def __post_init__(self) -> None:
        self.paths.ensure()
        self.database_url = f"sqlite:///{self.paths.data_dir / 'backtest.db'}"


DEFAULT_SETTINGS = Settings()


def load_strategy_params(yaml_loader: Optional[callable] = None) -> Dict[str, Dict]:
    """Load strategy parameters from ``strategy_params.yaml``.

    Parameters
    ----------
    yaml_loader:
        Optional callable used for loading YAML.  This indirection keeps the
        module dependency free; the caller can supply ``yaml.safe_load`` from
        PyYAML or ``tomllib.loads`` if the file is converted to TOML in the
        future.
    """

    params_path = DEFAULT_SETTINGS.strategy_params_path or Path("config/strategy_params.yaml")
    if not params_path.exists():
        return {}

    if yaml_loader is None:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - documented behaviour
            raise RuntimeError(
                "PyYAML is required to load strategy parameters. Install it via `pip install pyyaml`."
            ) from exc
        yaml_loader = yaml.safe_load

    with params_path.open("r", encoding="utf8") as handle:
        data = yaml_loader(handle)

    return data or {}
