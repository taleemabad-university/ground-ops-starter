"""The two live feeds. GIVEN — you do not need to change it.

Arrivals and departures come in on their own schedule. They overlap: the same
flight shows up on both feeds, and sometimes twice on one. That is real, and
de-duplicating it is the board's job (board.upsert returns False for a repeat).

The feed is also where two of the day-3 failures come from, so read from it and
never assume a flight you have seen once will not turn up again.
"""
import itertools
import threading
import time

from board.state import BOARD

# deterministic on purpose: the same board every run, so a bug is reproducible
SCHEDULE = [
    # (flight,  kind,        eta minutes past the hour)
    ("PK-304", "arrival",   12),
    ("EK-621", "arrival",   14),
    ("QR-118", "arrival",   17),
    ("PK-304", "arrival",   12),        # <- duplicate, straight away
    ("PA-450", "departure", 21),
    ("TK-709", "departure", 24),
    ("SV-882", "departure", 27),
    ("EK-621", "arrival",   14),        # <- duplicate, later
    ("AI-201", "arrival",   31),
    ("BA-772", "arrival",   35),
    ("QR-118", "arrival",   17),        # <- duplicate, later still
    ("LH-760", "departure", 38),
]

TICK_SECONDS = 1.6


def events():
    """Yield (flight, kind, eta) forever, looping the schedule."""
    for row in itertools.cycle(SCHEDULE):
        yield row


def run(stop=None):
    """Push the feed into the board until told to stop."""
    seen_dupes = 0
    for flight, kind, eta in events():
        if stop is not None and stop.is_set():
            return
        fresh = BOARD.upsert(flight, kind, eta)
        if fresh:
            BOARD.note("feed", "inbound", flight=flight, kind=kind, eta=eta)
        else:
            seen_dupes += 1
            BOARD.note("feed", "duplicate_merged", flight=flight, total=seen_dupes)
        time.sleep(TICK_SECONDS)


def start():
    stop = threading.Event()
    threading.Thread(target=run, args=(stop,), daemon=True).start()
    return stop
