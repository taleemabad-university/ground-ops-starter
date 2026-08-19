"""What counts as surviving. GIVEN — this is what we score you against on day 2.

None of these checks look at your source code. They watch the board, and they
read the /state and /log your pieces expose. That is the whole point: we can
score any team's build without ever opening it, and you can run this yourself
as many times as you like before we do.

    python -m harness.verdict            check the board right now
"""
import json
import time
import urllib.request

BOARD_URL = "http://127.0.0.1:8080"

# your pieces. change the ports here if your team used different ones.
PIECES = {
    "assigner-A": 8101,
    "assigner-B": 8102,
    "replanner":  8103,
    "monitor":    8104,
}

RESOLVED = ("gated", "slotted", "held", "divert")
RUNAWAY_WRITES_PER_SEC = 25          # above this and the board is being hammered


def _get(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def board():
    return _get(f"{BOARD_URL}/board")


def piece(name):
    """-> dict | None (None means it did not answer, which is itself a result)."""
    try:
        return _get(f"http://127.0.0.1:{PIECES[name]}/state", timeout=2)
    except Exception:
        return None


def watch(seconds, every=0.5):
    """Sample the board for a while. Returns [(monotonic_t, snapshot), ...]."""
    out, end = [], time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            out.append((time.monotonic(), board()))
        except Exception:
            out.append((time.monotonic(), None))
        time.sleep(every)
    return [s for s in out if s[1] is not None]


# ── the checks ───────────────────────────────────────────────────────────────

def check_no_double_book(samples, **_):
    """RULE 1 and 2, plus: does each piece agree with the board about who holds what?"""
    for _, snap in samples:
        for gate, holder in snap["gates"].items():
            if holder and snap["flights"].get(holder, {}).get("gate") != gate:
                return False, f"board disagrees with itself: {gate} holds {holder}"
    for name in PIECES:
        st = piece(name)
        if not st:
            continue
        placed = (st.get("state") or {}).get("placed") or {}
        live = samples[-1][1]["gates"]
        for flight, gate in placed.items():
            if live.get(gate) != flight:
                return False, (f"{name} thinks {flight} is on {gate}, "
                               f"board says {live.get(gate) or 'nobody'} — its state has split "
                               f"from the board's")
    return True, "board and pieces agree on who holds what"


def check_no_silent_loss(samples, **_):
    """A flight that HAD a place and lost it must end up somewhere, or be decided.

    A flight still queued behind full gates has not been lost — it has never been
    placed. What we are looking for is a flight that was on the board and came off
    it with nobody saying so.
    """
    if len(samples) < 2:
        return True, "window too short to judge"
    first, final = samples[0][1]["flights"], samples[-1][1]["flights"]
    had_a_place = {f for f, v in first.items() if v["gate"] or v["slot"]}
    lost = [f for f in had_a_place
            if f in final and not final[f]["gate"] and final[f]["status"] not in RESOLVED]
    if lost:
        return False, (f"{len(lost)} flight(s) were placed and then came off the board "
                       f"with no decision: {', '.join(sorted(lost)[:4])}")
    return True, f"all {len(had_a_place)} placed flights still placed or decided"


def rate(samples, lo=0.0, hi=1.0):
    """Board writes per second over a slice of the window."""
    if len(samples) < 2:
        return 0.0
    a, b = samples[int(len(samples) * lo)], samples[min(int(len(samples) * hi), len(samples) - 1)]
    return (b[1]["writes"] - a[1]["writes"]) / max(b[0] - a[0], 0.001)


def check_converges(samples, baseline=None, **_):
    """The board must settle. A re-planner with no damping never lets it.

    Judged against how busy the board was BEFORE we touched it, because a healthy
    system's steady rate depends on how the team built it. What is never healthy
    is the rate taking off and staying up.
    """
    if len(samples) < 6:
        return True, "window too short to judge"
    end = rate(samples, 0.66, 1.0)
    ceiling = RUNAWAY_WRITES_PER_SEC if baseline is None else max(2.0, baseline * 2.5)
    if end > ceiling:
        extra = "" if baseline is None else f" (was {baseline:.1f}/s before the injection)"
        return False, (f"board still taking {end:.0f} writes/sec at the end of the window"
                       f"{extra} — it is not settling, it is spinning")
    return True, f"board settled to {end:.1f} writes/sec"


def check_pieces_alive(samples, **_):
    """Fail loudly and KEEP GOING. A piece that died is a piece that dropped out."""
    dead = [n for n in PIECES if piece(n) is None]
    if dead:
        return False, f"not answering: {', '.join(dead)} — died instead of degrading"
    return True, f"all {len(PIECES)} pieces still answering"


def check_decided(samples, flight=None, **_):
    """After 'no-gate': did anything actually make a call on the stuck flight?"""
    if not flight:
        return True, "not applicable"
    final = samples[-1][1]["flights"].get(flight)
    if not final:
        return False, f"{flight} is not on the board at all"
    if final["status"] in ("held", "divert"):
        return True, (f"{flight} -> {final['status']} "
                      f"({final.get('reason') or 'no reason given'})")
    return False, (f"{flight} is still '{final['status']}' with nowhere to go — "
                   f"nothing timed out, nothing chose a backup, it just hung")


CHECKS = {
    "no double-book":  check_no_double_book,
    "no silent loss":  check_no_silent_loss,
    "board converges": check_converges,
    "pieces alive":    check_pieces_alive,
    "decision made":   check_decided,
}


def run(samples, want=None, flight=None, baseline=None):
    want = want or [k for k in CHECKS if k != "decision made"]
    results = []
    for name in want:
        try:
            ok, why = CHECKS[name](samples, flight=flight, baseline=baseline)
        except Exception as e:                       # noqa: BLE001
            ok, why = False, f"check blew up: {e!r}"
        results.append((name, ok, why))
    return results


def report(title, results):
    print(f"\n  {title}")
    print("  " + "─" * 66)
    for name, ok, why in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<16} {why}")
    passed = sum(1 for _, ok, _ in results if ok)
    print("  " + "─" * 66)
    print(f"  {passed}/{len(results)} checks passed\n")
    return passed == len(results)


if __name__ == "__main__":
    report("board right now", run(watch(4)))
