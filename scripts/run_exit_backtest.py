"""Run backtest with Exit optimization strategy."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from inference.model_loader import ModelLoader
from inference.signals import generate_signals
from trading.exit_policy import ExitPolicy

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

DATA_PATH = Path("data/sample_prices.csv")


@dataclass
class Position:
    """Open position."""

    entry_price: float
    entry_time: str
    position_type: str  # "BUY" or "SELL"
    entry_idx: int


@dataclass
class Trade:
    """Completed trade."""

    entry_price: float
    exit_price: float
    entry_time: str
    exit_time: str
    position_type: str
    pnl: float
    pnl_pct: float
    hold_duration_sec: float
    exit_reason: str


@dataclass
class BacktestResult:
    """Backtest results with Exit policy."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    total_pnl_pct: float
    win_rate: float
    avg_win: float
    avg_loss: float
    avg_hold_time_sec: float
    max_drawdown: float
    final_equity: float
    trades: List[Trade]


def load_rows(path: Path):
    """Load CSV data."""
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_data() -> None:
    """Generate sample data if not exists."""
    if DATA_PATH.exists():
        return
    from scripts.generate_sample_data import main as generate_data_main

    generate_data_main()


def parse_timestamp_to_seconds(ts: str) -> float:
    """Convert timestamp to seconds (simplified for demo)."""
    # In real implementation, parse datetime properly
    # For demo, use simple hash-based approach
    return float(hash(ts) % 100000)


def run_exit_backtest(
    rows: List[dict],
    model,
    config,
    exit_policy: ExitPolicy,
    bars: int = None,
) -> BacktestResult:
    """
    Run backtest with Exit policy.
    
    Args:
        rows: Price data rows
        model: ML model for signal generation
        config: Config object
        exit_policy: Exit policy instance
        bars: Number of bars to use (None = all)
    
    Returns:
        BacktestResult with detailed metrics
    """
    if bars:
        rows = rows[:bars]
    
    signals = generate_signals(rows, model=model, threshold=config.signal_threshold)
    
    position: Position | None = None
    completed_trades: List[Trade] = []
    equity = config.initial_capital
    peak_equity = equity
    max_dd = 0.0
    
    logger.info(f"Starting backtest with {len(signals)} signals over {len(rows)} bars")
    
    for idx, row in enumerate(rows):
        current_price = float(row.get("price") or row.get("close", 0))
        current_time = row.get("timestamp", "")
        
        # Check for entry signals
        matching_signals = [s for s in signals if s.timestamp == current_time]
        
        if position is None:
            # Look for entry
            for sig in matching_signals:
                if sig.action in {"BUY", "SELL"}:
                    position = Position(
                        entry_price=current_price,
                        entry_time=current_time,
                        position_type=sig.action,
                        entry_idx=idx,
                    )
                    exit_policy.reset()
                    logger.info(
                        f"ENTRY: {position.position_type} @ {current_price:.2f} "
                        f"at {current_time}"
                    )
                    break
        else:
            # Check exit conditions
            hold_duration_sec = parse_timestamp_to_seconds(current_time) - \
                               parse_timestamp_to_seconds(position.entry_time)
            
            # Simple trend detection (using price momentum)
            trend_alive = False
            trend_direction = None
            if idx > 10:
                recent_prices = [float(rows[i].get("price") or rows[i].get("close", 0)) for i in range(idx-10, idx)]
                avg_recent = sum(recent_prices) / len(recent_prices)
                trend_alive = abs(current_price - avg_recent) / avg_recent > 0.001  # 0.1% move
                trend_direction = "up" if current_price > avg_recent else "down"
            
            decision = exit_policy.should_exit(
                entry_price=position.entry_price,
                current_price=current_price,
                position_type=position.position_type,
                hold_duration_sec=abs(hold_duration_sec),
                trend_alive=trend_alive,
                trend_direction=trend_direction,
            )
            
            if decision.should_exit:
                # Calculate trade P&L
                if position.position_type == "BUY":
                    pnl = current_price - position.entry_price
                else:  # SELL
                    pnl = position.entry_price - current_price
                
                pnl_pct = (pnl / position.entry_price) * 100
                
                trade = Trade(
                    entry_price=position.entry_price,
                    exit_price=current_price,
                    entry_time=position.entry_time,
                    exit_time=current_time,
                    position_type=position.position_type,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    hold_duration_sec=abs(hold_duration_sec),
                    exit_reason=decision.reason,
                )
                completed_trades.append(trade)
                
                # Update equity
                equity += pnl
                if equity > peak_equity:
                    peak_equity = equity
                
                dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0
                if dd > max_dd:
                    max_dd = dd
                
                logger.info(
                    f"EXIT: {position.position_type} @ {current_price:.2f} | "
                    f"P&L: {pnl:.2f} ({pnl_pct:.2f}%) | "
                    f"Reason: {decision.reason} | "
                    f"Hold: {abs(hold_duration_sec):.0f}s | "
                    f"Equity: {equity:.2f}"
                )
                
                position = None
    
    # Calculate statistics
    total_trades = len(completed_trades)
    if total_trades == 0:
        return BacktestResult(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            win_rate=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            avg_hold_time_sec=0.0,
            max_drawdown=0.0,
            final_equity=equity,
            trades=[],
        )
    
    winning_trades = [t for t in completed_trades if t.pnl > 0]
    losing_trades = [t for t in completed_trades if t.pnl <= 0]
    
    total_pnl = sum(t.pnl for t in completed_trades)
    total_pnl_pct = (total_pnl / config.initial_capital) * 100
    win_rate = len(winning_trades) / total_trades * 100
    avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
    avg_hold = sum(t.hold_duration_sec for t in completed_trades) / total_trades
    
    return BacktestResult(
        total_trades=total_trades,
        winning_trades=len(winning_trades),
        losing_trades=len(losing_trades),
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        avg_hold_time_sec=avg_hold,
        max_drawdown=max_dd,
        final_equity=equity,
        trades=completed_trades,
    )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Exit optimization backtest")
    parser.add_argument("--bars", type=int, default=None, help="Number of bars to test")
    parser.add_argument(
        "--time-tolerance",
        type=float,
        default=300.0,
        help="Time tolerance in seconds (default: 300)",
    )
    parser.add_argument(
        "--loss-tolerance",
        type=float,
        default=0.5,
        help="Loss tolerance in percent (default: 0.5)",
    )
    args = parser.parse_args()
    
    ensure_data()
    rows = load_rows(DATA_PATH)
    config = DEFAULT_CONFIG
    
    model = ModelLoader(config=config, model_path="models/latest.bin").load()
    
    exit_policy = ExitPolicy(
        time_tolerance_sec=args.time_tolerance,
        loss_tolerance_pct=args.loss_tolerance,
    )
    
    logger.info("=" * 60)
    logger.info("AlphaStorm Exit Optimization Backtest")
    logger.info("=" * 60)
    logger.info(f"Time Tolerance: {args.time_tolerance}s")
    logger.info(f"Loss Tolerance: {args.loss_tolerance}%")
    logger.info(f"Bars: {args.bars if args.bars else 'All'}")
    logger.info("=" * 60)
    
    result = run_exit_backtest(
        rows=rows,
        model=model,
        config=config,
        exit_policy=exit_policy,
        bars=args.bars,
    )
    
    # Print results
    logger.info("=" * 60)
    logger.info("BACKTEST RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total Trades: {result.total_trades}")
    logger.info(f"Winning Trades: {result.winning_trades}")
    logger.info(f"Losing Trades: {result.losing_trades}")
    logger.info(f"Win Rate: {result.win_rate:.2f}%")
    logger.info(f"Total P&L: ${result.total_pnl:.2f} ({result.total_pnl_pct:.2f}%)")
    logger.info(f"Average Win: ${result.avg_win:.2f}")
    logger.info(f"Average Loss: ${result.avg_loss:.2f}")
    logger.info(f"Average Hold Time: {result.avg_hold_time_sec:.0f}s")
    logger.info(f"Max Drawdown: {result.max_drawdown:.2f}%")
    logger.info(f"Final Equity: ${result.final_equity:.2f}")
    logger.info("=" * 60)
    
    # Exit reason breakdown
    if result.trades:
        exit_reasons = {}
        for trade in result.trades:
            reason = trade.exit_reason
            if reason not in exit_reasons:
                exit_reasons[reason] = 0
            exit_reasons[reason] += 1
        
        logger.info("Exit Reason Breakdown:")
        for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
            pct = count / result.total_trades * 100
            logger.info(f"  {reason}: {count} ({pct:.1f}%)")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
