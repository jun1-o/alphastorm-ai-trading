"""Central configuration for the public-safe demo project."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectConfig:
    """Runtime configuration for demo and backtest scripts."""

    safe_public_mode: bool = True
    random_seed: int = 42
    signal_threshold: float = 0.15
    initial_capital: float = 10_000.0


DEFAULT_CONFIG = ProjectConfig()
