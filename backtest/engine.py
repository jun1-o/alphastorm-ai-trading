"""Backtest engine for public-safe simulation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List

from execution.exit_policy import ExitPolicyConfig, decide_exit
from inference.signals import Signal


@dataclass
class BacktestResult:
    final_equity: float
    pnl: float
    trades: int


def run_backtest(
    signals: List[Signal],
    initial_capital: float,
    exit_policy_config: ExitPolicyConfig,
    exit_log_path: Path | None = None,
) -> BacktestResult:
    cash = initial_capital
    position = 0  # 1=long, -1=short, 0=flat
    entry_price = 0.0
    entry_index = -1
    ema = 0.0
    previous_ema = 0.0
    alpha = 2 / (12 + 1)
    trades = 0
    log_rows: list[dict] = []

    for index, signal in enumerate(signals):
        price = signal.price
        if index == 0:
            ema = price
            previous_ema = price
        else:
            previous_ema = ema
            ema = (alpha * price) + ((1 - alpha) * ema)
        ema_slope = ema - previous_ema

        if signal.action == "BUY" and position <= 0:
            if position == -1:
                cash -= price
                trades += 1
            position = 1
            entry_price = price
            entry_index = index
            cash -= price
            trades += 1
        elif signal.action == "SELL" and position >= 0:
            if position == 1:
                cash += price
                trades += 1
            position = -1
            entry_price = price
            entry_index = index
            cash += price
            trades += 1
        elif position != 0:
            direction = "BUY" if position == 1 else "SELL"
            profit = ((price - entry_price) if position == 1 else (entry_price - price)) * 1000
            hold_seconds = max(0, (index - entry_index) * 60)
            exit_score = abs(signal.score)
            decision = decide_exit(
                direction=direction,
                hold_seconds=hold_seconds,
                profit=profit,
                exit_score=exit_score,
                ema_slope=ema_slope,
                price=price,
                ema=ema,
                config=exit_policy_config,
            )
            print(
                f"[EXIT DEBUG] score={exit_score:.4f} profit={profit:.2f} "
                f"hold={hold_seconds} trend_alive={decision.trend_alive} "
                f"th={decision.exit_threshold_used:.2f} action={decision.action}"
            )
            log_rows.append(
                {
                    "timestamp": signal.timestamp,
                    "direction": direction,
                    "price": price,
                    "profit": round(profit, 4),
                    "hold_seconds": hold_seconds,
                    "exit_score": round(exit_score, 6),
                    "trend_alive": decision.trend_alive,
                    "initial_tolerance_active": decision.initial_tolerance_active,
                    "initial_tolerance_loss_limit": exit_policy_config.initial_tolerance_loss,
                    "hold_block_reason": decision.hold_block_reason,
                    "exit_threshold_used": decision.exit_threshold_used,
                    "action": decision.action,
                }
            )
            if decision.action == "FULL_EXIT":
                cash += price if position == 1 else -price
                position = 0
                entry_price = 0.0
                entry_index = -1
                trades += 1

    last_price = signals[-1].price if signals else 0
    if position == 1:
        final_equity = cash + last_price
    elif position == -1:
        final_equity = cash - last_price
    else:
        final_equity = cash

    if exit_log_path is not None and log_rows:
        exit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with exit_log_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(log_rows[0].keys()))
            writer.writeheader()
            writer.writerows(log_rows)

    return BacktestResult(
        final_equity=round(final_equity, 2),
        pnl=round(final_equity - initial_capital, 2),
        trades=trades,
    )
