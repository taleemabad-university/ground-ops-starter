"""MONITOR — this one is YOURS to fix.

It is supposed to be the piece that notices when something is stuck and makes a
call about it. Right now it notices, and then does nothing about it, forever.

    usage:  python -m monitor.naive 8104

WHAT IT DOES
    Counts how many flights have no gate, and prints the number.

WHAT IS WRONG WITH IT
    1. NO TIMER. A flight with nowhere to go stays a flight with nowhere to go.
       Nothing is counting how long it has been waiting, so nothing can ever
       decide that it has waited too long.
    2. NO FALLBACK. board.flag(flight, "held" | "divert", reason) is sitting
       right there and never gets called. On day 2 we hand it a flight and open
       no gates at all. This will watch that flight sit there until the demo
       ends. A system that hangs quietly has failed just as hard as one that
       crashes — it has just made it harder to notice.
    3. NO LOG WORTH READING. `print(count)` tells you nothing after the fact. If
       your piece cannot tell us afterwards WHAT it decided and WHY, we cannot
       tell the difference between "handled it" and "got lucky".
    4. NO TESTS. tests/ has one example. This piece is supposed to own the rest.

YOUR JOB
    -> start a clock on every flight the moment it has nowhere to go
    -> when it runs out, PICK SOMETHING: hold on the tarmac, or flag a divert.
       A safe backup beats hanging every single time                    (SLO 6)
    -> write down every decision and the reason for it                  (SLO 6)
    -> turn each day-2 failure you hit into a test in tests/            (SLO 7)
"""
import sys
import time

from board.client import Board, serve_piece

TICK_SECONDS = 1.0
PATIENCE_MIN = 2           # board-minutes a flight may wait before you MUST decide


def main(port):
    board = Board(actor="monitor")
    log = []
    waiting_since = {}                          # tracked, and then ignored

    serve_piece("monitor", port, lambda: {"waiting": waiting_since}, log)

    while True:
        try:
            snap = board.board()
            now = snap["now"]
            stuck = [fid for fid, f in snap["flights"].items()
                     if f["gate"] is None and f["status"] == "pending"]

            for fid in stuck:
                waiting_since.setdefault(fid, now)
            for fid in list(waiting_since):
                if fid not in stuck:
                    waiting_since.pop(fid, None)

            # ↓↓↓ THE BUG ↓↓↓  it can see the problem and does nothing about it
            print(f"[monitor] {len(stuck)} flights with nowhere to go", flush=True)
            # ↑↑↑ no timer runs out, no decision is ever made, nobody is told ↑↑↑

            # TODO(you): something like —
            #   for fid, since in waiting_since.items():
            #       if now - since < PATIENCE_MIN:
            #           continue
            #       ok, reason = board.flag(fid, "held",
            #                               f"no gate for {now - since} min")
            #       log.append({"t": now, "did": "fallback", "flight": fid,
            #                   "decision": "held", "waited": now - since})

        except Exception as e:                  # noqa: BLE001
            log.append({"did": "error", "error": repr(e)})
            print(f"[monitor] {e!r}", flush=True)
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8104)
