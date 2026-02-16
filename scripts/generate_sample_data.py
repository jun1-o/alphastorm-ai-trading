"""Generate a synthetic OHLC-like price series for demos/backtests."""

from __future__ import annotations

import argparse
import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_rows(points: int, seed: int):
    rng = random.Random(seed)
    start = datetime(2024, 1, 1)
    for i in range(points):
        ts = start + timedelta(minutes=i)
        base = 100 + (i * 0.02) + math.sin(i / 7) * 0.8
        noise = rng.uniform(-0.35, 0.35)
        yield {"timestamp": ts.isoformat(), "price": round(base + noise, 4)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/sample_prices.csv")
    parser.add_argument("--points", type=int, default=240)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "price"])
        writer.writeheader()
        writer.writerows(generate_rows(args.points, args.seed))

    print(f"Synthetic dataset generated at {out_path}")


if __name__ == "__main__":
    main()
