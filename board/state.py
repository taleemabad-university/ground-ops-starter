"""The shared state. This file is GIVEN — you do not need to change it.

Two hard rules are enforced here, in one place, under one lock:

    one gate holds one flight, ever
    one slot holds one flight, ever

Everything you build talks to this through board/api.py over HTTP. That is on
purpose: it is the only thing all four pieces agree on, and it is where we
inject failures on day 2 without touching your code.
"""
import threading
import time
from dataclasses import dataclass, field, asdict

from . import db

GATES = ["G1", "G2", "G3", "G4", "G5", "G6"]
SLOTS = ["R1", "R2", "R3", "R4"]

PENDING = "pending"      # known to the board, nowhere yet
GATED = "gated"          # holds a gate
SLOTTED = "slotted"      # holds a gate and a runway slot
HELD = "held"            # monitor's fallback: waiting on the tarmac
DIVERT = "divert"        # monitor's fallback: flagged to divert


@dataclass
class Flight:
    id: str
    kind: str                      # "arrival" | "departure"
    eta_min: int                   # minutes past the hour, board time
    gate: str | None = None
    slot: str | None = None
    status: str = PENDING
    delay_min: int = 0
    decided_by: str | None = None  # which piece made the last call on it
    reason: str | None = None


class Rejected(Exception):
    """A claim that would have broken a hard rule. Your piece MUST handle this."""

    def __init__(self, reason, holder=None):
        super().__init__(reason)
        self.reason = reason
        self.holder = holder


class Board:
    def __init__(self):
        self._lock = threading.RLock()
        self.gates = {g: None for g in GATES}
        self.slots = {s: None for s in SLOTS}
        self.closed_slots = set()
        self.flights: dict[str, Flight] = {}
        self.log: list[dict] = []
        self.skew_min = 0            # harness: bad-clock injection
        self.writes = 0              # monotonic; the verdict uses it to spot a runaway
        self.started = time.time()

    # ── the board's clock ────────────────────────────────────────────────
    # Read time from HERE, not from your own datetime.now(). On day 2 we skew
    # this, and a piece that kept its own clock will not even notice.
    def now_min(self):
        with self._lock:
            return int((time.time() - self.started) / 6) + self.skew_min

    def note(self, actor, event, **kw):
        with self._lock:
            entry = {"t": self.now_min(), "actor": actor, "event": event, **kw}
            self.log.append(entry)
            del self.log[:-400]        # memory keeps the last 400 …
            db.record(entry)           # … the database keeps all of them
            return entry

    def _persist(self, flight_id):
        f = self.flights.get(flight_id)
        if f is not None:
            db.save_flight(f)

    def restore(self):
        """Rebuild from disk. The board survives whoever is hosting it rebooting."""
        with self._lock:
            for row in db.all_flights():
                f = Flight(id=row["id"], kind=row["kind"], eta_min=row["eta_min"],
                           gate=row["gate"], slot=row["slot"], status=row["status"],
                           delay_min=row["delay_min"], decided_by=row["decided_by"],
                           reason=row["reason"])
                self.flights[f.id] = f
                if f.gate:
                    self.gates[f.gate] = f.id
                if f.slot:
                    self.slots[f.slot] = f.id
            self.closed_slots = set(db.get_meta("closed_slots", []))
            self.skew_min = db.get_meta("skew_min", 0)
            return len(self.flights)

    # ── flights ──────────────────────────────────────────────────────────
    def upsert(self, flight_id, kind, eta_min):
        """Feeds call this. Duplicates collapse onto the same record."""
        with self._lock:
            f = self.flights.get(flight_id)
            if f:
                return False                       # already known — a duplicate
            self.flights[flight_id] = Flight(id=flight_id, kind=kind, eta_min=eta_min)
            self._persist(flight_id)
            return True

    def unassigned(self):
        with self._lock:
            return [f.id for f in self.flights.values()
                    if f.gate is None and f.status in (PENDING,)]

    # ── the two hard rules ───────────────────────────────────────────────
    def claim_gate(self, flight_id, gate, actor="?"):
        with self._lock:
            f = self.flights.get(flight_id)
            if f is None:
                raise Rejected("unknown_flight")
            if gate not in self.gates:
                raise Rejected("unknown_gate")
            holder = self.gates[gate]
            if holder is not None and holder != flight_id:
                # RULE 1. Somebody got here first.
                self.note(actor, "claim_rejected", flight=flight_id, gate=gate, holder=holder)
                raise Rejected("gate_occupied", holder=holder)
            if f.gate and f.gate != gate:
                self.gates[f.gate] = None          # a flight holds at most one gate
            self.gates[gate] = flight_id
            f.gate = gate
            f.status = SLOTTED if f.slot else GATED
            f.decided_by = actor
            self.writes += 1
            self.note(actor, "claim_ok", flight=flight_id, gate=gate)
            self._persist(flight_id)
            return True

    def claim_slot(self, flight_id, slot, actor="?"):
        with self._lock:
            f = self.flights.get(flight_id)
            if f is None:
                raise Rejected("unknown_flight")
            if slot not in self.slots:
                raise Rejected("unknown_slot")
            if slot in self.closed_slots:
                raise Rejected("slot_closed")
            holder = self.slots[slot]
            if holder is not None and holder != flight_id:
                # RULE 2.
                self.note(actor, "slot_rejected", flight=flight_id, slot=slot, holder=holder)
                raise Rejected("slot_occupied", holder=holder)
            if f.slot and f.slot != slot:
                self.slots[f.slot] = None
            self.slots[slot] = flight_id
            f.slot = slot
            f.status = SLOTTED if f.gate else PENDING
            f.decided_by = actor
            self.writes += 1
            self.note(actor, "slot_ok", flight=flight_id, slot=slot)
            self._persist(flight_id)
            return True

    def release_gate(self, gate, actor="?"):
        with self._lock:
            fid = self.gates.get(gate)
            if fid:
                f = self.flights[fid]
                f.gate = None
                f.status = PENDING if f.slot is None else f.status
            self.gates[gate] = None
            self.writes += 1
            self.note(actor, "release_gate", gate=gate, flight=fid)
            if fid: self._persist(fid)
            return fid

    def flag(self, flight_id, decision, reason, actor="monitor"):
        """The monitor's safe backup. HELD or DIVERT — a decision, not a hang."""
        with self._lock:
            f = self.flights.get(flight_id)
            if f is None:
                raise Rejected("unknown_flight")
            if decision not in (HELD, DIVERT):
                raise Rejected("bad_decision")
            f.status = decision
            f.reason = reason
            f.decided_by = actor
            self.writes += 1
            self.note(actor, "fallback", flight=flight_id, decision=decision, reason=reason)
            self._persist(flight_id)
            return True

    # ── harness surface · day 2 only ─────────────────────────────────────
    def inject_delay(self, flight_id, minutes):
        with self._lock:
            f = self.flights[flight_id]
            f.delay_min += minutes
            f.eta_min += minutes
            missed = None
            if minutes >= 60 and f.slot:
                # it is far too late to make its own runway slot. the slot opens up,
                # the gate does not — which is what starts the whole cascade.
                missed, self.slots[f.slot] = f.slot, None
                f.slot = None
                f.status = GATED if f.gate else PENDING
            self.note("HARNESS", "delay", flight=flight_id, minutes=minutes,
                      gate=f.gate, missed_slot=missed)
            self._persist(flight_id)
            return {"gate": f.gate, "missed_slot": missed}

    def close_runway(self, slots):
        with self._lock:
            evicted = []
            for s in slots:
                self.closed_slots.add(s)
                fid = self.slots.get(s)
                if fid:
                    self.flights[fid].slot = None
                    self.flights[fid].status = GATED if self.flights[fid].gate else PENDING
                    evicted.append(fid)
                self.slots[s] = None
            db.set_meta("closed_slots", sorted(self.closed_slots))
            for fid in evicted:
                self._persist(fid)
            self.note("HARNESS", "close_runway", slots=list(slots), evicted=evicted)
            return evicted

    def set_skew(self, minutes):
        with self._lock:
            self.skew_min = minutes
            db.set_meta("skew_min", minutes)
            self.note("HARNESS", "clock_skew", minutes=minutes)

    def snapshot(self):
        with self._lock:
            return {
                "now": self.now_min(),
                "writes": self.writes,
                "gates": dict(self.gates),
                "slots": dict(self.slots),
                "closed_slots": sorted(self.closed_slots),
                "flights": {k: asdict(v) for k, v in self.flights.items()},
            }


BOARD = Board()
