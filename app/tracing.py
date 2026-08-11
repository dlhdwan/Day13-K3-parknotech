from __future__ import annotations

import os
from typing import Any

class _DummyClient:
    def update_current_trace(self, **kwargs: Any) -> None:
        return None

    def update_current_generation(self, **kwargs: Any) -> None:
        return None

    def update_current_span(self, **kwargs: Any) -> None:
        return None

    def score(self, **kwargs: Any) -> None:
        return None

    def create_score(self, **kwargs: Any) -> None:
        return None

    def flush(self) -> None:
        return None

    def get_prompt(self, name: str, **kwargs: Any) -> Any:
        return None


try:
    from langfuse import get_client, observe

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    def get_client():
        return _DummyClient()



def get_langfuse_client():
    return get_client()


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


def score_trace(name: str, value: float, comment: str | None = None) -> None:
    """Record evaluation or quality score on current trace."""
    if not tracing_enabled():
        return
    client = get_langfuse_client()
    try:
        if hasattr(client, "score") and callable(client.score):
            client.score(name=name, value=value, comment=comment)
        elif hasattr(client, "create_score") and callable(client.create_score):
            client.create_score(name=name, value=value, comment=comment)
    except Exception:
        pass


def flush_tracing() -> None:
    """Flush pending Langfuse events to ensure traces are delivered."""
    if not tracing_enabled():
        return
    client = get_langfuse_client()
    try:
        if hasattr(client, "flush") and callable(client.flush):
            client.flush()
    except Exception:
        pass

