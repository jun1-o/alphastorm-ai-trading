"""Demo trading loop with logging-only execution."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from execution.exit_policy import ExitPolicyConfig, decide_exit
from inference.model_loader import ModelLoader
from inference.signals import generate_signals

logger = logging.getLogger("demo-trading")
DATA_PATH = Path("data/sample_prices.csv")
EXIT_LOG_PATH = Path("logs/demo_exit_decision_log.csv")


class OrderExecutor:
    def __init__(self, safe_public_mode: bool) -> None:
        self.safe_public_mode = safe_public_mode

    def send_order(self, action: str, price: float, timestamp: str) -> None:
        # Live trading logic removed in public version.
        logger.info(
            "SIMULATED ORDER | ts=%s action=%s price=%.4f reason=safe_public_mode",
            timestamp,
            action,
            price,
        )


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_data() -> None:
    if DATA_PATH.exists():
        return
    from scripts.generate_sample_data import main as generate_data_main

    generate_data_main()


def write_exit_log(rows: list[dict]) -> None:
    if not rows:
        return
    EXIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EXIT_LOG_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run logging-only simulation")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = DEFAULT_CONFIG

    if not config.safe_public_mode and not args.dry_run:
        raise RuntimeError("Public repository enforces safe mode or --dry-run")

    ensure_data()
    rows = load_rows(DATA_PATH)

    model = ModelLoader(config=config, model_path="models/latest.bin").load()
    signals = generate_signals(rows[:50], model=model, threshold=config.signal_threshold)
    exit_policy_config = ExitPolicyConfig(
        initial_tolerance_seconds=config.initial_tolerance_seconds,
        initial_tolerance_loss=config.initial_tolerance_loss,
        exit_threshold_base=config.exit_threshold_base,
        exit_threshold_profit=config.exit_threshold_profit,
        exit_threshold_loss=config.exit_threshold_loss,
        min_hold_seconds=config.min_hold_seconds,
    )

    executor = OrderExecutor(safe_public_mode=config.safe_public_mode)
    position = 0
    entry_price = 0.0
    entry_index = -1
    ema = 0.0
    prev_ema = 0.0
    alpha = 2 / (12 + 1)
    exit_log_rows: list[dict] = []

    logger.info("SAFE MODE: %s", config.safe_public_mode)
    for index, sig in enumerate(signals):
        if index == 0:
            ema = sig.price
            prev_ema = sig.price
        else:
            prev_ema = ema
            ema = (alpha * sig.price) + ((1 - alpha) * ema)
        ema_slope = ema - prev_ema

        logger.info(
            "SIGNAL | ts=%s action=%s score=%.4f price=%.4f",
            sig.timestamp,
            sig.action,
            sig.score,
            sig.price,
        )

        if sig.action == "BUY" and position <= 0:
            if position == -1:
                executor.send_order("BUY", sig.price, sig.timestamp)
            position = 1
            entry_price = sig.price
            entry_index = index
            executor.send_order("BUY", sig.price, sig.timestamp)
            continue

        if sig.action == "SELL" and position >= 0:
            if position == 1:
                executor.send_order("SELL", sig.price, sig.timestamp)
            position = -1
            entry_price = sig.price
            entry_index = index
            executor.send_order("SELL", sig.price, sig.timestamp)
            continue

        if position == 0:
            continue

        direction = "BUY" if position == 1 else "SELL"
        profit = ((sig.price - entry_price) if position == 1 else (entry_price - sig.price)) * 1000
        hold_seconds = max(0, (index - entry_index) * 60)
        decision = decide_exit(
            direction=direction,
            hold_seconds=hold_seconds,
            profit=profit,
            exit_score=abs(sig.score),
            ema_slope=ema_slope,
            price=sig.price,
            ema=ema,
            config=exit_policy_config,
        )
        logger.info(
            "[EXIT DEBUG] score=%.4f profit=%.2f hold=%d trend_alive=%s th=%.2f action=%s",
            abs(sig.score),
            profit,
            hold_seconds,
            decision.trend_alive,
            decision.exit_threshold_used,
            decision.action,
        )
        exit_log_rows.append(
            {
                "timestamp": sig.timestamp,
                "direction": direction,
                "price": sig.price,
                "profit": round(profit, 4),
                "hold_seconds": hold_seconds,
                "exit_score": round(abs(sig.score), 6),
                "trend_alive": decision.trend_alive,
                "initial_tolerance_active": decision.initial_tolerance_active,
                "initial_tolerance_loss_limit": exit_policy_config.initial_tolerance_loss,
                "hold_block_reason": decision.hold_block_reason,
                "exit_threshold_used": decision.exit_threshold_used,
                "action": decision.action,
            }
        )

        if decision.action == "FULL_EXIT":
            exit_action = "SELL" if position == 1 else "BUY"
            executor.send_order(exit_action, sig.price, sig.timestamp)
            position = 0
            entry_price = 0.0
            entry_index = -1

    write_exit_log(exit_log_rows)


if __name__ == "__main__":
    main()
