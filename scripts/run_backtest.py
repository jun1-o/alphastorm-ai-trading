"""Run an end-to-end public-safe backtest."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.engine import run_backtest
from config import DEFAULT_CONFIG
from inference.model_loader import ModelLoader
from inference.signals import generate_signals
from rag.pipeline import query_strategy_context

DATA_PATH = Path("data/sample_prices.csv")


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_data() -> None:
    if DATA_PATH.exists():
        return
    from scripts.generate_sample_data import main as generate_data_main

    generate_data_main()


def main() -> None:
    ensure_data()
    rows = load_rows(DATA_PATH)
    config = DEFAULT_CONFIG

    model = ModelLoader(config=config, model_path="models/latest.bin").load()
    signals = generate_signals(rows, model=model, threshold=config.signal_threshold)
    result = run_backtest(signals, initial_capital=config.initial_capital)

    rag_blurb = query_strategy_context(
        "What are this strategy's recent risk metrics?", config=config
    )

    print("=== Public-Safe Backtest ===")
    print(f"Safe public mode: {config.safe_public_mode}")
    print(f"Signals generated: {len(signals)}")
    print(f"Trades simulated: {result.trades}")
    print(f"Final equity: {result.final_equity}")
    print(f"PnL: {result.pnl}")
    print(f"RAG: {rag_blurb}")


if __name__ == "__main__":
    main()
