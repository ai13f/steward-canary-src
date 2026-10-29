"""A stand-in viewer: `python -m app.viewer URL` streams URL forever and prints one JSON line per second,
`{"t": <unix>, "bytes": <received in that second>, "gap_s": <seconds since the last byte>, "interrupted": bool}`.
A gap of GAP_S or more, or a dropped connection, is an interruption; the viewer reconnects like a player would."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request

GAP_S = float(os.environ.get("VIEWER_GAP_S", "2"))


def main(url: str) -> int:
    state = {"bytes": 0, "last": time.time(), "dropped": False}
    lock = threading.Lock()

    def reader() -> None:
        while True:
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    while True:
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        with lock:
                            state["bytes"] += len(chunk)
                            state["last"] = time.time()
            except Exception:  # noqa: BLE001 - any failure is a dropped stream; reconnect
                pass
            with lock:
                state["dropped"] = True
            time.sleep(1)

    threading.Thread(target=reader, daemon=True).start()
    while True:
        time.sleep(1)
        now = time.time()
        with lock:
            got, gap, dropped = state["bytes"], round(now - state["last"], 1), state["dropped"]
            state["bytes"], state["dropped"] = 0, False
        print(json.dumps({"t": round(now, 1), "bytes": got, "gap_s": gap, "interrupted": dropped or gap >= GAP_S}),
              flush=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
