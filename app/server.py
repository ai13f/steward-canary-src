"""steward-canary: a tiny stateful HTTP service used to prove the image steward's judgment.

Endpoints: /healthz (process up), /readyz (ready after READY_DELAY_S and a valid schema), /status (JSON),
POST /work[?n=N] (append N items to the data volume), POST /enqueue[?n=N] and POST /drain (a pending-work queue),
GET /stream[?quiet=1] (a never-ending chunked stream: a "viewer"; quiet streams are not counted in /status.clients),
POST /slots/take?ttl=S and POST /slots/release (a shared slot another tenant can hold, like a provider line).

State lives in DATA_DIR: `schema` (applied schema version), `format` (file format), `ticks` (a counter persisted
every few seconds), `items.log` (one float timestamp per line) and `pending.log`.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import fmt, migrate, schema, status

VERSION = os.environ.get("APP_VERSION", "dev")
DATA = Path(os.environ.get("DATA_DIR", "/data"))
READY_DELAY_S = float(os.environ.get("READY_DELAY_S", "2"))
PORT = int(os.environ.get("PORT", "8080"))
CHUNK = b"x" * 4096

STARTED = time.monotonic()
STARTED_AT = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
TICKS = {"n": 0}
LIVE = {"clients": 0, "items": 0, "slot_until": 0.0}
LOCK = threading.Lock()


def _item_ts(line: str) -> float:
    line = line.strip()
    return float(json.loads(line)["t"]) if line.startswith("{") else float(line)


def load_items() -> int:
    """Count the items on the volume and store them as JSON lines (one {"t": ...} object per line), the richer form
    the item API will use."""
    path = DATA / "items.log"
    if not path.exists():
        return 0
    with path.open() as fh:
        stamps = [_item_ts(line) for line in fh if line.strip()]
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps({"t": t}) + "\n" for t in stamps))
    tmp.replace(path)
    return len(stamps)


def pending() -> int:
    path = DATA / "pending.log"
    return sum(1 for _ in path.open()) if path.exists() else 0


def status_payload() -> dict:
    with LOCK:
        ticks = TICKS["n"]
        live = dict(LIVE)
    extra = {"version": VERSION, "started_at": STARTED_AT, "items": live["items"], "clients": live["clients"],
             "slots_in_use": 1 if live["slot_until"] > time.monotonic() else 0, "pending": pending(),
             "format": fmt.on_disk(DATA)}
    return status.snapshot(STARTED, ticks, schema.SCHEMA_VERSION) | extra


def ready() -> bool:
    return time.monotonic() - STARTED >= READY_DELAY_S


def _ticker() -> None:
    while True:
        time.sleep(1)
        with LOCK:
            TICKS["n"] += 1
            n = TICKS["n"]
        if n % 5 == 0:
            (DATA / "ticks").write_text(str(n))


def _count(query: dict) -> int:
    return max(1, min(100000, int((query.get("n") or ["1"])[0])))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _stream(self, quiet: bool) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        if not quiet:
            with LOCK:
                LIVE["clients"] += 1
        try:
            while True:
                self.wfile.write(b"%x\r\n%s\r\n" % (len(CHUNK), CHUNK))
                self.wfile.flush()
                time.sleep(0.1)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            if not quiet:
                with LOCK:
                    LIVE["clients"] -= 1
            self.close_connection = True

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path == "/healthz":
            self._send(200, {"ok": True})
        elif url.path == "/readyz":
            self._send(200 if ready() else 503, {"ready": ready()})
        elif url.path == "/status":
            self._send(200, status_payload())
        elif url.path == "/stream":
            self._stream(quiet=parse_qs(url.query).get("quiet") == ["1"])
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/work":
            n = _count(query)
            with (DATA / "items.log").open("a") as fh:
                fh.write("".join(json.dumps({"t": round(time.time(), 3)}) + "\n" for _ in range(n)))
            with LOCK:
                LIVE["items"] += n
                items = LIVE["items"]
            self._send(200, {"items": items})
        elif url.path == "/enqueue":
            n = _count(query)
            with (DATA / "pending.log").open("a") as fh:
                fh.write("".join(f"{time.time():.3f}\n" for _ in range(n)))
            self._send(200, {"pending": pending()})
        elif url.path == "/drain":
            path = DATA / "pending.log"
            moved = pending()
            if moved:
                with (DATA / "items.log").open("a") as fh:
                    fh.write(path.read_text())
                path.unlink()
                with LOCK:
                    LIVE["items"] += moved
            self._send(200, {"drained": moved, "pending": 0})
        elif url.path == "/slots/take":
            ttl = float((query.get("ttl") or ["60"])[0])
            with LOCK:
                LIVE["slot_until"] = time.monotonic() + ttl
            self._send(200, {"slots_in_use": 1, "ttl": ttl})
        elif url.path == "/slots/release":
            with LOCK:
                LIVE["slot_until"] = 0.0
            self._send(200, {"slots_in_use": 0})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt_: str, *args) -> None:  # quiet access log
        pass


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        applied = migrate.upgrade(DATA, schema.SCHEMA_VERSION)
        data_format = fmt.check(DATA)
    except (migrate.SchemaTooNew, fmt.FormatTooNew) as exc:
        print(f"refusing to start: {exc}", file=sys.stderr, flush=True)
        return 3
    LIVE["items"] = load_items()
    print(f"steward-canary {VERSION} schema {applied} format {data_format} items {LIVE['items']} "
          f"listening on :{PORT}", flush=True)
    threading.Thread(target=_ticker, daemon=True).start()
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
