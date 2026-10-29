"""Upgrade preconditions for data format 2 (read UPGRADE.md).

Format 2 is forward-only: once a volume is converted, builds with FORMAT 1 refuse to start on it.

PRECONDITIONS (check every one before upgrading to 1.8.1 from 1.8.0):
- queue_drained: GET /status must report "pending": 0. The format 2 conversion does not carry pending.log over;
  every queued item still pending at conversion time is lost. Drain with POST /drain first.
- from_version: upgrade only from 1.8.0 (earlier volumes have no format file and are converted by 1.8.0 first).
"""

from __future__ import annotations

from pathlib import Path

PRECONDITIONS = (
    {"id": "queue_drained", "check": "GET /status: pending == 0",
     "why": "the format 2 conversion drops pending.log; queued items are lost"},
    {"id": "from_version", "check": "running version == 1.8.0", "why": "single-step upgrade"},
)


def convert(data: Path) -> dict:
    """Convert the volume to format 2 (forward-only). pending.log is not converted (see PRECONDITIONS)."""
    found = int((data / "format").read_text().strip()) if (data / "format").exists() else 1
    if found >= 2:
        return {"converted": False, "dropped_pending": 0}
    pending = data / "pending.log"
    dropped = sum(1 for _ in pending.open()) if pending.exists() else 0
    if pending.exists():
        pending.unlink()
    (data / "format").write_text("2")
    return {"converted": True, "dropped_pending": dropped}
