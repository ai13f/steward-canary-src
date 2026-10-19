"""steward-canary: a tiny stateful HTTP service used to prove the image steward's judgment.

Endpoints: /healthz (process up), /readyz (ready after READY_DELAY_S and a valid schema), /status (JSON),
POST /work (append one item to the data volume). State lives in DATA_DIR: `schema` (applied schema version),
`ticks` (a counter persisted every few seconds) and `items.log`.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app import migrate, schema, status

VERSION = os.environ.get("APP_VERSION", "dev")
DATA = Path(os.environ.get("DATA_DIR", "/data"))
READY_DELAY_S = float(os.environ.get("READY_DELAY_S", "2"))
PORT = int(os.environ.get("PORT", "8080"))

STARTED = time.monotonic()
STARTED_AT = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
TICKS = {"n": 0}
LOCK = threading.Lock()


def status_payload() -> dict:
    with LOCK:
        ticks = TICKS["n"]
    return status.snapshot(STARTED, ticks, schema.SCHEMA_VERSION) | {"version": VERSION, "started_at": STARTED_AT}


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


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._send(200, {"ok": True})
        elif self.path == "/readyz":
            self._send(200 if ready() else 503, {"ready": ready()})
        elif self.path == "/status":
            self._send(200, status_payload())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/work":
            self._send(404, {"error": "not found"})
            return
        with (DATA / "items.log").open("a") as fh:
            fh.write(f"{time.time():.3f}\n")
        items = sum(1 for _ in (DATA / "items.log").open())
        self._send(200, {"items": items})

    def log_message(self, fmt: str, *args) -> None:  # quiet access log
        pass


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        applied = migrate.upgrade(DATA, schema.SCHEMA_VERSION)
    except migrate.SchemaTooNew as exc:
        print(f"refusing to start: {exc}", file=sys.stderr, flush=True)
        return 3
    print(f"steward-canary {VERSION} schema {applied} listening on :{PORT}", flush=True)
    print(f"ready after {READY_DELAY_S:g}s; data in {DATA}", flush=True)
    threading.Thread(target=_ticker, daemon=True).start()
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
