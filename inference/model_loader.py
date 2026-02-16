"""Model loading facade preserving private-project structure."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from config import ProjectConfig
from training.dummy_model import DummyModel


class ModelLoader:
    """Load production model in private mode, dummy model in public mode."""

    def __init__(self, config: ProjectConfig, model_path: Optional[str] = None) -> None:
        self.config = config
        self.model_path = Path(model_path) if model_path else None

    def load(self):
        if self.config.safe_public_mode:
            # Live trading logic removed in public version.
            return DummyModel(random_seed=self.config.random_seed)

        if not self.model_path:
            raise ValueError("model_path is required when safe_public_mode is disabled")
        raise RuntimeError(
            "Private trained models/checkpoints are intentionally excluded from the public repository"
        )
