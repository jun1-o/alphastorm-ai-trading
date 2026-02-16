"""Dummy model artifacts used for public-safe release."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class DummyModel:
    """Public-safe predictor that emulates model output shape.

    Live trading logic removed in public version.
    """

    random_seed: int = 42

    def __post_init__(self) -> None:
        self._rng = random.Random(self.random_seed)

    def predict(self, rows: Iterable[dict]) -> List[float]:
        """Return deterministic pseudo-random scores for each row."""
        return [self._rng.uniform(-1.0, 1.0) for _ in rows]
