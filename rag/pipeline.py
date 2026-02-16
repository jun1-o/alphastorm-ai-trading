"""RAG facade for strategy diagnostics."""

from __future__ import annotations

from config import ProjectConfig


def query_strategy_context(question: str, config: ProjectConfig) -> str:
    if config.safe_public_mode:
        # Live trading logic removed in public version.
        return (
            "SAFE MODE PLACEHOLDER: proprietary RAG knowledge base removed. "
            "Returned metrics are synthetic and for architecture demo only."
        )

    raise RuntimeError("Private RAG context is not available in the public repository")
