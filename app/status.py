"""The /status payload."""

from __future__ import annotations

import time


def uptime_s(started: float) -> float:
    """Seconds since `started` (a time.monotonic() value)."""
    return round((time.monotonic() - started) * 1000, 3)


def snapshot(state: dict) -> dict:
    """`state`: {"started": monotonic start, "ticks": int, "schema_version": int, ...}; extra keys pass through."""
    out = {k: v for k, v in state.items() if k != "started"}
    out["uptime_s"] = uptime_s(state["started"])
    return out
