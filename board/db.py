"""Where the board keeps its data. GIVEN — you do not need to change it.

SQLite, from the standard library. No install, one file on disk (`board.db`),
and it does two jobs:

  1. THE BOARD SURVIVES A RESTART. Kill the process, start it again, and every
     flight is still where it was. Whoever is hosting the board can close their
     laptop lid without wiping the team's afternoon.

  2. EVERY DECISION IS KEPT, FOREVER. The in-memory log holds the last 400
     events. The `decisions` table holds all of them, with an index on flight,
     so on day 3 you can ask "what actually happened to PK-304, in order, and
     which service did it" — instead of guessing from whatever is still on
     screen. That is how you work out whether a fault is yours or upstream
     (SLO 2) without reading anyone's source.

Query it directly. It's a normal database:

    sqlite3 board.db "SELECT board_min, actor, event, gate, slot
                      FROM decisions WHERE flight='PK-304' ORDER BY id"

    sqlite3 board.db "SELECT actor, COUNT(*) FROM decisions
                      WHERE event='claim_rejected' GROUP BY actor"
"""
import json
import os
import pathlib
import sqlite3
import threading

DB_PATH = pathlib.Path(os.environ.get(
    "BOARD_DB", pathlib.Path(__file__).resolve().parent.parent / "board.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS flights(
  id         TEXT PRIMARY KEY,
  kind       TEXT    NOT NULL,
  eta_min    INTEGER NOT NULL,
  gate       TEXT,
  slot       TEXT,
  status     TEXT    NOT NULL,
  delay_min  INTEGER NOT NULL DEFAULT 0,
  decided_by TEXT,
  reason     TEXT
);
CREATE TABLE IF NOT EXISTS decisions(
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  board_min INTEGER NOT NULL,
  actor     TEXT    NOT NULL,
  event     TEXT    NOT NULL,
  flight    TEXT,
  gate      TEXT,
  slot      TEXT,
  detail    TEXT
);
CREATE INDEX IF NOT EXISTS ix_decisions_flight ON decisions(flight);
CREATE INDEX IF NOT EXISTS ix_decisions_actor  ON decisions(actor);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""

_lock = threading.Lock()
_conn = None


def connect():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
        _conn.commit()
    return _conn


def reset():
    """Start the board empty. `./run fresh` does this for you."""
    global _conn
    with _lock:
        if _conn:
            _conn.close()
            _conn = None
        if DB_PATH.exists():
            DB_PATH.unlink()
    connect()


def record(entry):
    """Append one decision. Called for every event the board notes."""
    known = {"t", "actor", "event", "flight", "gate", "slot"}
    detail = {k: v for k, v in entry.items() if k not in known}
    with _lock:
        c = connect()
        c.execute(
            "INSERT INTO decisions(board_min,actor,event,flight,gate,slot,detail)"
            " VALUES(?,?,?,?,?,?,?)",
            (entry.get("t", 0), entry.get("actor", "?"), entry.get("event", "?"),
             entry.get("flight"), entry.get("gate"), entry.get("slot"),
             json.dumps(detail) if detail else None))
        c.commit()


def save_flight(f):
    with _lock:
        c = connect()
        c.execute(
            "INSERT INTO flights(id,kind,eta_min,gate,slot,status,delay_min,decided_by,reason)"
            " VALUES(?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(id) DO UPDATE SET kind=excluded.kind, eta_min=excluded.eta_min,"
            " gate=excluded.gate, slot=excluded.slot, status=excluded.status,"
            " delay_min=excluded.delay_min, decided_by=excluded.decided_by, reason=excluded.reason",
            (f.id, f.kind, f.eta_min, f.gate, f.slot, f.status, f.delay_min,
             f.decided_by, f.reason))
        c.commit()


def set_meta(key, value):
    with _lock:
        c = connect()
        c.execute("INSERT INTO meta(k,v) VALUES(?,?)"
                  " ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, json.dumps(value)))
        c.commit()


def get_meta(key, default=None):
    with _lock:
        row = connect().execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
    return json.loads(row["v"]) if row else default


def all_flights():
    with _lock:
        return [dict(r) for r in connect().execute("SELECT * FROM flights").fetchall()]


def history(flight=None, limit=200):
    """Every decision, oldest first. The day-3 debugging tool."""
    q = "SELECT board_min,actor,event,flight,gate,slot,detail FROM decisions"
    args = []
    if flight:
        q += " WHERE flight=?"
        args.append(flight)
    q += " ORDER BY id LIMIT ?"
    args.append(limit)
    with _lock:
        rows = connect().execute(q, args).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d.pop("detail", None):
            d.update(json.loads(r["detail"]))
        out.append(d)
    return out


def counts_by(column, event=None):
    """e.g. counts_by("actor", event="claim_rejected") — who is losing races."""
    q = f"SELECT {column} AS k, COUNT(*) AS n FROM decisions"
    args = []
    if event:
        q += " WHERE event=?"
        args.append(event)
    q += f" GROUP BY {column} ORDER BY n DESC"
    with _lock:
        return {r["k"]: r["n"] for r in connect().execute(q, args).fetchall() if r["k"]}
