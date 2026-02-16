"""Backtest engine for public-safe simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from inference.signals import Signal


@dataclass
class BacktestResult:
    final_equity: float
    pnl: float
    trades: int


def run_backtest(signals: List[Signal], initial_capital: float) -> BacktestResult:
    cash = initial_capital
    position = 0
    trades = 0

    for signal in signals:
        price = signal.price
        if signal.action == "BUY" and position == 0:
            position = 1
            cash -= price
            trades += 1
        elif signal.action == "SELL" and position == 1:
            position = 0
            cash += price
            trades += 1

    last_price = signals[-1].price if signals else 0
    final_equity = cash + (last_price if position == 1 else 0)
    return BacktestResult(
        final_equity=round(final_equity, 2),
        pnl=round(final_equity - initial_capital, 2),
        trades=trades,
    )
