"""Run an end-to-end public-safe backtest."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest.engine import run_backtest
from config import DEFAULT_CONFIG
from execution.exit_policy import ExitPolicyConfig
from inference.model_loader import ModelLoader
from inference.signals import generate_signals
from rag.pipeline import query_strategy_context

DATA_PATH = Path("data/sample_prices.csv")
EXIT_LOG_PATH = Path("logs/exit_decision_log.csv")


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_data() -> None:
    if DATA_PATH.exists():
        return
    from scripts.generate_sample_data import main as generate_data_main

    generate_data_main()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backtest with exit-policy controls")
    parser.add_argument("--initial-tolerance-seconds", type=int, default=DEFAULT_CONFIG.initial_tolerance_seconds)
    parser.add_argument("--initial-tolerance-loss", type=float, default=DEFAULT_CONFIG.initial_tolerance_loss)
    parser.add_argument("--exit-threshold-loss", type=float, default=DEFAULT_CONFIG.exit_threshold_loss)
    parser.add_argument("--min-hold-seconds", type=int, default=DEFAULT_CONFIG.min_hold_seconds)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_data()
    rows = load_rows(DATA_PATH)
    config = replace(
        DEFAULT_CONFIG,
        initial_tolerance_seconds=args.initial_tolerance_seconds,
        initial_tolerance_loss=args.initial_tolerance_loss,
        exit_threshold_loss=args.exit_threshold_loss,
        min_hold_seconds=args.min_hold_seconds,
    )

    model = ModelLoader(config=config, model_path="models/latest.bin").load()
    signals = generate_signals(rows, model=model, threshold=config.signal_threshold)
    exit_policy_config = ExitPolicyConfig(
        initial_tolerance_seconds=config.initial_tolerance_seconds,
        initial_tolerance_loss=config.initial_tolerance_loss,
        exit_threshold_base=config.exit_threshold_base,
        exit_threshold_profit=config.exit_threshold_profit,
        exit_threshold_loss=config.exit_threshold_loss,
        min_hold_seconds=config.min_hold_seconds,
    )
    result = run_backtest(
        signals,
        initial_capital=config.initial_capital,
        exit_policy_config=exit_policy_config,
        exit_log_path=EXIT_LOG_PATH,
    )

    rag_blurb = query_strategy_context(
        "What are this strategy's recent risk metrics?", config=config
    )

    print("=== Public-Safe Backtest ===")
    print(f"Safe public mode: {config.safe_public_mode}")
    print(f"Signals generated: {len(signals)}")
    print(f"Trades simulated: {result.trades}")
    print(f"Final equity: {result.final_equity}")
    print(f"PnL: {result.pnl}")
    print(f"Exit log: {EXIT_LOG_PATH}")
    print(f"RAG: {rag_blurb}")


if __name__ == "__main__":
    main()
