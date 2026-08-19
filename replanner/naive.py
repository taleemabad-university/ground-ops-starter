"""RE-PLANNER — this one is YOURS to fix.

When a flight slips, the flights behind it have to be redone. This does that.
It also cannot stop doing it, which is the problem.

    usage:  python -m replanner.naive 8103

WHAT IT DOES
    Every tick it looks at the whole board and re-issues a runway slot for every
    single flight it can see.

WHAT IS WRONG WITH IT
    1. NO DAMPING. There is nothing between "something changed" and "redo it".
       On day 2 we hand it a clock that runs 47 minutes fast, so every flight
       looks late, so it re-plans everything, which changes the board, which
       looks like another change, which makes it re-plan again. It is the piece
       whose whole job is to fix the board, and left like this it is the piece
       most likely to melt it.
    2. NO BLAST RADIUS. One flight slipped. It redoes all twelve. Even when it
       is not spinning, it is churning gates that nobody asked it to touch, and
       every one of those writes is a chance to fight the assigners.
    3. It reads its own clock in one place (see the marked line) instead of the
       board's. With a skewed board clock the two disagree, and it will not even
       be able to tell you why it is behaving like this.

YOUR JOB
    -> work out WHICH flights a delay actually touches, and move only those
    -> rate-limit yourself: at most one re-plan per flight per N board-minutes,
       and back off when the board keeps changing under you   self-healing (SLO 6)
    -> read time from board.now(), never from your own clock
    -> say out loud in the log what you changed and why    observability (SLO 6)
"""
import sys
import time

from board.client import Board, serve_piece

TICK_SECONDS = 0.4
SLOTS = ["R1", "R2", "R3", "R4"]


def main(port):
    board = Board(actor="replanner")
    log = []
    replans = {"count": 0, "last_tick": 0}

    serve_piece("replanner", port, lambda: dict(replans), log)

    while True:
        try:
            snap = board.board()
            now = snap["now"]

            # ↓↓↓ THE BUG ↓↓↓  every flight, every tick, no matter what changed
            for fid, f in snap["flights"].items():
                if f["status"] in ("held", "divert"):
                    continue
                late = f["eta_min"] < now                # <- and "late" is measured
                if not late:                            #    against a clock we do
                    continue                            #    not control
                for s in SLOTS:
                    if s in snap["closed_slots"]:
                        continue
                    holder = snap["slots"].get(s)
                    if holder in (None, fid):
                        board.slot(fid, s)
                        replans["count"] += 1
                        log.append({"t": now, "did": "replan", "flight": fid, "slot": s})
                        break
            # ↑↑↑ nothing here limits how often any of that can happen ↑↑↑

            # TODO(you): something like —
            #   affected = flights whose gate or slot actually moved since last tick
            #   for f in affected:
            #       if now - last_replan[f] < COOLDOWN: continue
            #       ... replan just f ...
            #       last_replan[f] = now

            replans["last_tick"] = now
        except Exception as e:                          # noqa: BLE001
            log.append({"did": "error", "error": repr(e)})
            print(f"[replanner] {e!r}", flush=True)
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8103)
