"""Forward-only schema migrations of the data volume. There are no down migrations: a build refuses to start on
a volume written by a newer schema."""

from __future__ import annotations

from pathlib import Path

MIGRATIONS = Path(__file__).parent / "migrations"


class SchemaTooNew(RuntimeError):
    pass


def current(data: Path) -> int:
    path = data / "schema"
    return int(path.read_text().strip()) if path.exists() else 0


def upgrade(data: Path, target: int) -> int:
    on_disk = current(data)
    if on_disk > target:
        raise SchemaTooNew(f"schema {on_disk} on disk is newer than supported {target}")
    for step in range(on_disk + 1, target + 1):
        script = next(MIGRATIONS.glob(f"{step:04d}_*.sql"))
        with (data / "migrations.log").open("a") as fh:
            fh.write(f"{script.name}\n")
        (data / "schema").write_text(str(step))
    return current(data)
