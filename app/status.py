"""The /status payload."""

from __future__ import annotations

import time


def uptime_s(started: float) -> float:
    """Seconds since `started` (a time.monotonic() value)."""
    return round(time.monotonic() - started, 3)


def snapshot(started: float, ticks: int, schema_version: int) -> dict:
    return {"uptime_s": uptime_s(started), "ticks": ticks, "schema_version": schema_version}
