"""Shared exit decision policy for demo-trading and backtest paths."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExitPolicyConfig:
    initial_tolerance_seconds: int
    initial_tolerance_loss: float
    exit_threshold_base: float
    exit_threshold_profit: float
    exit_threshold_loss: float
    min_hold_seconds: int


@dataclass(frozen=True)
class ExitDecision:
    action: str
    trend_alive: bool
    initial_tolerance_active: bool
    hold_block_reason: str
    exit_threshold_used: float


def is_trend_alive(direction: str, ema_slope: float, price: float, ema: float) -> bool:
    if direction == "BUY":
        return ema_slope > 0 and price > ema
    if direction == "SELL":
        return ema_slope < 0 and price < ema
    return False


def select_exit_threshold(profit: float, config: ExitPolicyConfig) -> float:
    if profit > 0:
        return config.exit_threshold_profit
    if profit < 0:
        return config.exit_threshold_loss
    return config.exit_threshold_base


def decide_exit(
    *,
    direction: str,
    hold_seconds: int,
    profit: float,
    exit_score: float,
    ema_slope: float,
    price: float,
    ema: float,
    config: ExitPolicyConfig,
) -> ExitDecision:
    trend_alive = is_trend_alive(direction, ema_slope, price, ema)
    threshold = select_exit_threshold(profit, config)
    initial_tolerance_active = (
        hold_seconds < config.initial_tolerance_seconds
        and trend_alive
        and profit > -config.initial_tolerance_loss
    )

    if not trend_alive:
        return ExitDecision(
            action="FULL_EXIT",
            trend_alive=trend_alive,
            initial_tolerance_active=False,
            hold_block_reason="trend_break",
            exit_threshold_used=threshold,
        )

    if initial_tolerance_active:
        return ExitDecision(
            action="HOLD",
            trend_alive=trend_alive,
            initial_tolerance_active=True,
            hold_block_reason="initial_tolerance",
            exit_threshold_used=threshold,
        )

    if profit > 0 and trend_alive:
        return ExitDecision(
            action="HOLD",
            trend_alive=trend_alive,
            initial_tolerance_active=False,
            hold_block_reason="profit_with_trend",
            exit_threshold_used=threshold,
        )

    if hold_seconds < config.min_hold_seconds:
        return ExitDecision(
            action="HOLD",
            trend_alive=trend_alive,
            initial_tolerance_active=False,
            hold_block_reason="min_hold_guard",
            exit_threshold_used=threshold,
        )

    if exit_score >= threshold:
        return ExitDecision(
            action="FULL_EXIT",
            trend_alive=trend_alive,
            initial_tolerance_active=False,
            hold_block_reason="score_exit",
            exit_threshold_used=threshold,
        )

    return ExitDecision(
        action="HOLD",
        trend_alive=trend_alive,
        initial_tolerance_active=False,
        hold_block_reason="score_below_threshold",
        exit_threshold_used=threshold,
    )
