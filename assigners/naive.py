"""ASSIGNER — this one is YOURS to fix.

It runs. It places flights. It is also wrong in one specific way, and on day 2
that way is going to cost you a flight.

    usage:  python -m assigners.naive A 8101
            python -m assigners.naive B 8102     <- two of these run at once

WHAT IT DOES
    Polls the board for flights with no gate, picks the first gate that looked
    free, and claims it.

WHAT IS WRONG WITH IT
    1. It reads the board, then decides, then writes — and between the read and
       the write, the OTHER assigner may have taken the gate. That is a race,
       and it is not hypothetical: two of these run at the same time.
    2. It throws away the answer the board gives it. `claim()` hands back
       (ok, reason). This code ignores both, marks the flight placed in its own
       head, and moves on. The board said REJECTED; this piece never heard.

       That is the real failure. The board holds the line — it will not
       double-book. But this piece now believes it owns a gate it does not own,
       and the flight it "placed" is sitting nowhere, with nobody looking for it.
       The harness calls that a silently lost flight, and it is the difference
       between failing loudly and dying quietly.

YOUR JOB
    -> read what claim() returns and act on it                       (SLO 6)
    -> when you are refused, put the flight BACK in play, do not drop it
    -> keep your /state honest: it must match the board, always
    -> agree with the other assigner who takes what, and write it in
       contracts.md before you touch this file                       (SLO 1)
"""
import sys
import time

from board.client import Board, serve_piece

POLL_SECONDS = 0.7


def main(name, port):
    board = Board(actor=f"assigner-{name}")
    mine = {}                                   # what THIS piece thinks it placed
    log = []

    serve_piece(f"assigner-{name}", port, lambda: {"placed": mine}, log)

    while True:
        try:
            waiting = board.unassigned()
            snap = board.board()
            free = [g for g, holder in sorted(snap["gates"].items()) if holder is None]

            for flight in waiting:
                if not free:
                    break
                gate = free.pop(0)

                # ↓↓↓ THE BUG ↓↓↓  the answer is thrown away
                board.claim(flight, gate)
                mine[flight] = gate
                log.append({"t": snap["now"], "did": "placed", "flight": flight, "gate": gate})
                # ↑↑↑ we never asked whether that actually worked ↑↑↑

                # TODO(you): something like —
                #   ok, reason = board.claim(flight, gate)
                #   if ok:
                #       mine[flight] = gate
                #   else:
                #       log.append({"did": "refused", "flight": flight,
                #                   "gate": gate, "reason": reason})
                #       continue            # leave it unassigned; try again next tick

        except Exception as e:                  # noqa: BLE001 — keep going, loudly
            log.append({"did": "error", "error": repr(e)})
            print(f"[assigner-{name}] {e!r}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "A",
         int(sys.argv[2]) if len(sys.argv) > 2 else 8101)
