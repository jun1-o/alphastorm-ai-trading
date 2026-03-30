"""Demo trading with Exit optimization strategy."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

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


class Position:
    """Track open position."""

    def __init__(self, entry_price: float, entry_time: str, position_type: str):
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.position_type = position_type
        self.entry_timestamp_sec = time.time()


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


def main() -> None:
    """Main entry point for Exit demo."""
    parser = argparse.ArgumentParser(description="Run Exit optimization demo")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--bars", type=int, default=50, help="Number of bars to simulate")
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

    config = DEFAULT_CONFIG

    if not config.safe_public_mode and not args.dry_run:
        raise RuntimeError("Public repository enforces safe mode or --dry-run")

    ensure_data()
    rows = load_rows(DATA_PATH)

    model = ModelLoader(config=config, model_path="models/latest.bin").load()
    signals = generate_signals(
        rows[: args.bars], model=model, threshold=config.signal_threshold
    )

    exit_policy = ExitPolicy(
        time_tolerance_sec=args.time_tolerance,
        loss_tolerance_pct=args.loss_tolerance,
    )

    logger.info("=" * 60)
    logger.info("AlphaStorm Exit Optimization DEMO")
    logger.info("=" * 60)
    logger.info(f"Safe Mode: {config.safe_public_mode}")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info(f"Time Tolerance: {args.time_tolerance}s")
    logger.info(f"Loss Tolerance: {args.loss_tolerance}%")
    logger.info(f"Bars to simulate: {args.bars}")
    logger.info("=" * 60)

    position: Position | None = None
    signal_map = {s.timestamp: s for s in signals}

    for idx, row in enumerate(rows[: args.bars]):
        current_price = float(row.get("price") or row.get("close", 0))
        current_time = row.get("timestamp", "")

        logger.info(f"Bar {idx}: {current_time} | Price: {current_price:.2f}")

        # Check for signals
        if current_time in signal_map:
            sig = signal_map[current_time]
            logger.info(
                f"  SIGNAL: {sig.action} | Score: {sig.score:.4f} | Price: {sig.price:.2f}"
            )

            if position is None and sig.action in {"BUY", "SELL"}:
                # Entry
                position = Position(
                    entry_price=current_price,
                    entry_time=current_time,
                    position_type=sig.action,
                )
                exit_policy.reset()
                logger.info(
                    f"  ✅ ENTRY EXECUTED: {position.position_type} @ {current_price:.2f}"
                )

        # Check exit if in position
        if position:
            hold_duration_sec = time.time() - position.entry_timestamp_sec

            # Simple trend detection
            trend_alive = False
            trend_direction = None
            if idx > 10:
                recent_prices = [
                    float(rows[i].get("price") or rows[i].get("close", 0)) for i in range(idx - 10, idx)
                ]
                avg_recent = sum(recent_prices) / len(recent_prices)
                trend_alive = (
                    abs(current_price - avg_recent) / avg_recent > 0.001
                )  # 0.1% move
                trend_direction = "up" if current_price > avg_recent else "down"

            decision = exit_policy.should_exit(
                entry_price=position.entry_price,
                current_price=current_price,
                position_type=position.position_type,
                hold_duration_sec=hold_duration_sec,
                trend_alive=trend_alive,
                trend_direction=trend_direction,
            )

            # Calculate current P&L
            if position.position_type == "BUY":
                pnl = current_price - position.entry_price
            else:  # SELL
                pnl = position.entry_price - current_price

            pnl_pct = (pnl / position.entry_price) * 100

            logger.info(
                f"  Position: {position.position_type} | "
                f"Entry: {position.entry_price:.2f} | "
                f"Current P&L: {pnl:.2f} ({pnl_pct:.2f}%) | "
                f"Hold: {hold_duration_sec:.0f}s | "
                f"Trend: {'🔥' if trend_alive else '💀'}"
            )

            if decision.should_exit:
                logger.info(
                    f"  ❌ EXIT EXECUTED: {position.position_type} @ {current_price:.2f} | "
                    f"Reason: {decision.reason} | "
                    f"Final P&L: {pnl:.2f} ({pnl_pct:.2f}%)"
                )
                position = None
            else:
                logger.info(f"  🔒 HOLD: {decision.reason}")

        logger.info("")  # Blank line for readability

    logger.info("=" * 60)
    logger.info("Demo simulation completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
