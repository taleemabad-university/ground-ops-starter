"""Talking to the board, and being reachable yourself. GIVEN.

Two things live here so you do not have to write them three times:

  Board(...)      a thin client for the board's HTTP contract
  serve_piece(..) stands your piece up on its own port with /health /state /log

That second one matters more than it looks. SLO 4 says your piece has to run
somewhere a teammate can reach — not just on your laptop. Everything you build
answers on a port from minute one, and on day 2 the harness reads /state and
/log to work out whether your piece survived. A piece nobody can see is a piece
we score as absent.
"""
import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import BOARD_URL          # set in team.env — NOT hardcoded to your laptop


class Board:
    """The board, as your piece sees it."""

    def __init__(self, actor, url=BOARD_URL):
        self.actor = actor
        self.url = url

    def _get(self, path):
        with urllib.request.urlopen(f"{self.url}{path}", timeout=4) as r:
            return json.loads(r.read())

    def _post(self, path, payload):
        payload = {**payload, "actor": self.actor}
        req = urllib.request.Request(
            f"{self.url}{path}", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=4) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    # reads
    def board(self):       return self._get("/board")
    def now(self):         return self._get("/now")["now"]
    def unassigned(self):  return self._get("/unassigned")["flights"]
    def log(self, n=50):   return self._get("/log?n=%d" % n)["log"]

    # writes — every one of these can be REFUSED. 409 means the board did not move.
    def claim(self, flight, gate):
        """-> (ok: bool, reason: str|None). ok=False means SOMEONE ELSE HAS IT."""
        code, body = self._post("/claim", {"flight": flight, "gate": gate})
        return code == 200, body.get("reason")

    def slot(self, flight, slot):
        code, body = self._post("/slot", {"flight": flight, "slot": slot})
        return code == 200, body.get("reason")

    def release(self, gate):
        code, _ = self._post("/release", {"gate": gate})
        return code == 200

    def flag(self, flight, decision, reason):
        """decision: "held" | "divert" — the monitor's safe backup."""
        code, body = self._post("/flag", {"flight": flight,
                                          "decision": decision, "reason": reason})
        return code == 200, body.get("reason")


def serve_piece(name, port, state_fn, log):
    """Stand this piece up on `port` so teammates — and the harness — can see it."""

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/health":
                payload = {"ok": True, "piece": name}
            elif self.path == "/state":
                payload = {"piece": name, "state": state_fn()}
            elif self.path.startswith("/log"):
                payload = {"piece": name, "log": list(log)[-80:]}
            else:
                payload = {"ok": False, "reason": "no_such_route"}
            body = json.dumps(payload).encode()
            self.send_response(200 if payload.get("ok", True) else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"{name} reachable on :{port}  (/health /state /log)", flush=True)
    return srv
