"""Signal generation pipeline kept for architecture demonstration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class Signal:
    timestamp: str
    price: float
    score: float
    action: str


def to_actions(scores: Iterable[float], threshold: float) -> List[str]:
    actions: List[str] = []
    for score in scores:
        if score >= threshold:
            actions.append("BUY")
        elif score <= -threshold:
            actions.append("SELL")
        else:
            actions.append("HOLD")
    return actions


def generate_signals(rows: List[dict], model, threshold: float) -> List[Signal]:
    scores = model.predict(rows)
    actions = to_actions(scores, threshold)
    return [
        Signal(
            timestamp=row["timestamp"],
            price=float(row["price"]),
            score=score,
            action=action,
        )
        for row, score, action in zip(rows, scores, actions)
    ]
