# AlphaStorm — AI-driven algorithmic trading framework (Public-Safe Demo)

## Project Overview

AlphaStorm is a Python-based trading framework that demonstrates how machine learning, strategy research, and execution workflows can be composed into a single quantitative system. This public repository is intentionally safety-scoped for demonstration, while preserving the core architecture for backtesting and pipeline orchestration.

This repository is a **public-safe, stripped-down showcase** of an AI trading system architecture.
It is designed for portfolio/recruiter review and intentionally removes anything that can reproduce a profitable live strategy.

## Safety Notice

- `safe_public_mode = true` is enabled by default.
- Live execution is disabled.
- Model artifacts/checkpoints are removed.
- Private datasets (MT5 exports, proprietary CSVs) are removed.
- RAG outputs are placeholders.

> **Live trading logic removed in public version.**

## Architecture (preserved)

- `training/` – model interfaces and dummy predictor implementation.
- `inference/` – model loader and signal generation.
- `backtest/` – simulation engine.
- `rag/` – strategy context query layer (placeholder in safe mode).
- `scripts/` – runnable entrypoints for data generation, backtest, and demo trading.

## Feature Coverage

- Python-based quantitative workflow.
- Machine learning model interface for strategy scoring.
- Algorithmic strategy signal generation and backtesting.
- Real-time style execution simulation (dry-run only in public-safe mode).
- Risk-aware simulation via position lifecycle and PnL accounting.
- Data engineering pipeline for synthetic sample generation.
- MLOps-style modular split between training, inference, and execution.
- Streamlit dashboard support as part of the full project scope.

## Discovery Keywords

Python, Machine Learning, Algorithmic Trading, Backtesting, Quantitative Finance, Real-time Execution, Risk Management, MLOps, Data Engineering, Trading Strategy Evaluation, MT5 Integration, Streamlit, Time Series Analysis, and Testing Workflows.

## AI + Backtest + RAG Pipeline

1. Synthetic market data is generated in `scripts/generate_sample_data.py`.
2. `inference/model_loader.py` loads a dummy predictor in safe mode.
3. `inference/signals.py` creates BUY/SELL/HOLD signals from model scores.
4. `backtest/engine.py` simulates trade lifecycle and computes PnL.
5. `rag/pipeline.py` returns placeholder strategy stats.

## Run

```bash
python scripts/run_backtest.py
python scripts/run_demo_trading.py --dry-run
```

Both commands are safe: they only simulate and log behavior.
