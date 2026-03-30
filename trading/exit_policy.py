"""Exit policy module for AlphaStorm GOLD trading strategy."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExitDecision:
    """Exit decision result."""
    
    should_exit: bool
    reason: str
    trend_alive: bool
    hold_duration_sec: float
    current_profit_loss: float


class ExitPolicy:
    """
    Exit policy that balances profit-taking with trend-following.
    
    Key features:
    - Trend-based exit: Hold while trend is alive
    - Time tolerance: Allow small drawdowns during trending
    - Loss tolerance: Cut losses when trend reverses
    """
    
    def __init__(
        self,
        time_tolerance_sec: float = 300.0,  # 5分間のホールド余裕
        loss_tolerance_pct: float = 0.5,    # 0.5%までの含み損許容
        profit_target_pct: float = 1.0,     # 1.0%利確目標
        trailing_stop_pct: float = 0.3,     # 0.3%トレーリングストップ
    ):
        self.time_tolerance_sec = time_tolerance_sec
        self.loss_tolerance_pct = loss_tolerance_pct
        self.profit_target_pct = profit_target_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.peak_profit: Optional[float] = None
    
    def reset(self) -> None:
        """Reset state for new position."""
        self.peak_profit = None
    
    def should_exit(
        self,
        entry_price: float,
        current_price: float,
        position_type: str,  # "BUY" or "SELL"
        hold_duration_sec: float,
        trend_alive: bool,
        trend_direction: Optional[str] = None,  # "up", "down", or None
    ) -> ExitDecision:
        """
        Determine if position should be exited.
        
        Args:
            entry_price: Entry price of position
            current_price: Current market price
            position_type: "BUY" or "SELL"
            hold_duration_sec: How long position has been held (seconds)
            trend_alive: Whether trend is still active
            trend_direction: Current trend direction if known
        
        Returns:
            ExitDecision with should_exit flag and reasoning
        """
        # Calculate P&L
        if position_type == "BUY":
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # SELL
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Update peak profit for trailing stop
        if self.peak_profit is None or pnl_pct > self.peak_profit:
            self.peak_profit = pnl_pct
        
        # Rule 1: Profit target reached
        if pnl_pct >= self.profit_target_pct:
            logger.info(
                f"EXIT SIGNAL: Profit target reached | "
                f"pnl={pnl_pct:.2f}% target={self.profit_target_pct:.2f}%"
            )
            return ExitDecision(
                should_exit=True,
                reason="profit_target",
                trend_alive=trend_alive,
                hold_duration_sec=hold_duration_sec,
                current_profit_loss=pnl_pct,
            )
        
        # Rule 2: Trailing stop triggered (only if we've been in profit)
        if self.peak_profit and self.peak_profit > 0:
            trailing_exit = self.peak_profit - pnl_pct >= self.trailing_stop_pct
            if trailing_exit:
                logger.info(
                    f"EXIT SIGNAL: Trailing stop triggered | "
                    f"peak={self.peak_profit:.2f}% current={pnl_pct:.2f}% "
                    f"drop={self.peak_profit - pnl_pct:.2f}%"
                )
                return ExitDecision(
                    should_exit=True,
                    reason="trailing_stop",
                    trend_alive=trend_alive,
                    hold_duration_sec=hold_duration_sec,
                    current_profit_loss=pnl_pct,
                )
        
        # Rule 3: Trend is dead and we're in loss
        if not trend_alive and pnl_pct < 0:
            logger.info(
                f"EXIT SIGNAL: Trend dead + loss | "
                f"pnl={pnl_pct:.2f}% trend_alive={trend_alive}"
            )
            return ExitDecision(
                should_exit=True,
                reason="trend_dead_loss",
                trend_alive=trend_alive,
                hold_duration_sec=hold_duration_sec,
                current_profit_loss=pnl_pct,
            )
        
        # Rule 4: Loss tolerance exceeded and time tolerance exceeded
        if pnl_pct < -self.loss_tolerance_pct and hold_duration_sec > self.time_tolerance_sec:
            logger.info(
                f"EXIT SIGNAL: Loss + time tolerance exceeded | "
                f"pnl={pnl_pct:.2f}% hold={hold_duration_sec:.0f}s"
            )
            return ExitDecision(
                should_exit=True,
                reason="loss_timeout",
                trend_alive=trend_alive,
                hold_duration_sec=hold_duration_sec,
                current_profit_loss=pnl_pct,
            )
        
        # Rule 5: Trend reversal (if direction info available)
        if trend_direction and position_type == "BUY" and trend_direction == "down":
            logger.info(f"EXIT SIGNAL: Trend reversal | position=BUY trend=down")
            return ExitDecision(
                should_exit=True,
                reason="trend_reversal",
                trend_alive=trend_alive,
                hold_duration_sec=hold_duration_sec,
                current_profit_loss=pnl_pct,
            )
        elif trend_direction and position_type == "SELL" and trend_direction == "up":
            logger.info(f"EXIT SIGNAL: Trend reversal | position=SELL trend=up")
            return ExitDecision(
                should_exit=True,
                reason="trend_reversal",
                trend_alive=trend_alive,
                hold_duration_sec=hold_duration_sec,
                current_profit_loss=pnl_pct,
            )
        
        # HOLD: Trend is alive or within tolerance
        logger.debug(
            f"HOLD: trend_alive={trend_alive} pnl={pnl_pct:.2f}% "
            f"hold={hold_duration_sec:.0f}s"
        )
        return ExitDecision(
            should_exit=False,
            reason="hold_trend_alive" if trend_alive else "hold_tolerance",
            trend_alive=trend_alive,
            hold_duration_sec=hold_duration_sec,
            current_profit_loss=pnl_pct,
        )
