"""The data volume's file format (separate from the SQL schema): `format` on the volume, FORMAT in the build.

A build refuses to start on a volume written in a newer format: like longhorn-manager, the way back after a format
upgrade is not a downgrade."""

from __future__ import annotations

from pathlib import Path

FORMAT = 1


class FormatTooNew(RuntimeError):
    pass


def on_disk(data: Path) -> int:
    path = data / "format"
    return int(path.read_text().strip()) if path.exists() else 1


def check(data: Path) -> int:
    found = on_disk(data)
    if found > FORMAT:
        raise FormatTooNew(f"data format {found} on disk is newer than supported {FORMAT}; downgrade not supported")
    return found
