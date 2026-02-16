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
from inference.model_loader import ModelLoader
from inference.signals import generate_signals

logger = logging.getLogger("demo-trading")
DATA_PATH = Path("data/sample_prices.csv")


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
    executor = OrderExecutor(safe_public_mode=config.safe_public_mode)

    logger.info("SAFE MODE: %s", config.safe_public_mode)
    for sig in signals:
        logger.info(
            "SIGNAL | ts=%s action=%s score=%.4f price=%.4f",
            sig.timestamp,
            sig.action,
            sig.score,
            sig.price,
        )
        if sig.action in {"BUY", "SELL"}:
            executor.send_order(sig.action, sig.price, sig.timestamp)


if __name__ == "__main__":
    main()
