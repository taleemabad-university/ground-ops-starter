"""The board, over HTTP, on :8080. GIVEN — you do not need to change it.

This is the contract every piece you build codes against.

  READ
    GET  /                           the live board, as a web page — open it
    GET  /board                      everything: gates, slots, flights, clock
    GET  /now                        the board clock  -> {"now": <minutes>}
    GET  /unassigned                 flights with no gate yet
    GET  /log?n=50                   recent decisions, newest last

  WRITE  (all return 200 {"ok":true} or 409 {"ok":false,"reason":...})
    POST /claim    {"flight","gate","actor"}    take a gate
    POST /slot     {"flight","slot","actor"}    take a runway slot
    POST /release  {"gate","actor"}             give a gate back
    POST /flag     {"flight","decision","reason"}  monitor's fallback:
                                                  decision = "held" | "divert"

A 409 is NOT an error you can ignore. It means somebody beat you to it and the
board did not change. If your piece carries on as though it won, its idea of the
world and the board's have just split — and that is exactly what we look for.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .state import BOARD, Rejected
from .ui import PAGE

PORT = 8080


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass                                   # the board keeps its own log

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, page):
        body = page.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        path, _, qs = self.path.partition("?")
        q = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
        if path in ("/", "/ui"):
            return self._html(PAGE)
        if path == "/board":
            return self._send(200, BOARD.snapshot())
        if path == "/now":
            return self._send(200, {"now": BOARD.now_min()})
        if path == "/unassigned":
            return self._send(200, {"flights": BOARD.unassigned()})
        if path == "/log":
            n = int(q.get("n", 50))
            return self._send(200, {"log": BOARD.log[-n:]})
        if path == "/health":
            return self._send(200, {"ok": True, "piece": "board"})
        return self._send(404, {"ok": False, "reason": "no_such_route"})

    def do_POST(self):
        try:
            b = self._body()
        except Exception:
            return self._send(400, {"ok": False, "reason": "bad_json"})
        actor = b.get("actor", "?")
        try:
            if self.path == "/claim":
                BOARD.claim_gate(b["flight"], b["gate"], actor)
            elif self.path == "/slot":
                BOARD.claim_slot(b["flight"], b["slot"], actor)
            elif self.path == "/release":
                BOARD.release_gate(b["gate"], actor)
            elif self.path == "/flag":
                BOARD.flag(b["flight"], b["decision"], b.get("reason", ""), actor)
            # ── harness only · day 2 ──
            elif self.path == "/admin/delay":
                return self._send(200, {"ok": True, **BOARD.inject_delay(b["flight"], b["minutes"])})
            elif self.path == "/admin/close-runway":
                return self._send(200, {"ok": True, "evicted": BOARD.close_runway(b["slots"])})
            elif self.path == "/admin/skew":
                BOARD.set_skew(b["minutes"])
            elif self.path == "/admin/flight":
                BOARD.upsert(b["flight"], b.get("kind", "arrival"), b.get("eta_min", 0))
            else:
                return self._send(404, {"ok": False, "reason": "no_such_route"})
        except Rejected as r:
            return self._send(409, {"ok": False, "reason": r.reason, "holder": r.holder})
        except KeyError as e:
            return self._send(400, {"ok": False, "reason": f"missing_{e.args[0]}"})
        return self._send(200, {"ok": True})


def serve(port=PORT, block=True):
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    if block:
        srv.serve_forever()
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    print(f"board listening on :{PORT}")
    serve()
