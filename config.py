"""Central configuration for the public-safe demo project."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectConfig:
    """Runtime configuration for demo and backtest scripts."""

    safe_public_mode: bool = True
    random_seed: int = 42
    signal_threshold: float = 0.15
    initial_capital: float = 10_000.0
    initial_tolerance_seconds: int = 120
    initial_tolerance_loss: float = 2_000.0
    exit_threshold_base: float = 0.85
    exit_threshold_profit: float = 0.90
    exit_threshold_loss: float = 0.70
    min_hold_seconds: int = 60


DEFAULT_CONFIG = ProjectConfig()
