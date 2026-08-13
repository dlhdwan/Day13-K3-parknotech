from __future__ import annotations

STATE = {
    "rag_slow": False,
    "tool_fail": False,
    "cost_spike": False,
}

ALIASES = {
    "rag_fail": "tool_fail",
}


def _resolve_name(name: str) -> str:
    return ALIASES.get(name, name)


def enable(name: str) -> None:
    real_name = _resolve_name(name)
    if real_name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    STATE[real_name] = True



def disable(name: str) -> None:
    real_name = _resolve_name(name)
    if real_name not in STATE:
        raise KeyError(f"Unknown incident: {name}")
    STATE[real_name] = False



def status() -> dict[str, bool]:
    res = dict(STATE)
    # Expose alias for frontend and lab tools
    res["rag_fail"] = STATE.get("tool_fail", False)
    return res
